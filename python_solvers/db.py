from __future__ import annotations

import json
import os
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Dict, Generator, Optional

from sqlalchemy import DateTime, Float, Integer, String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker


def _normalize_database_url(raw_url: str) -> str:
    if raw_url.startswith("postgres://"):
        return raw_url.replace("postgres://", "postgresql+psycopg://", 1)
    if raw_url.startswith("postgresql://"):
        return raw_url.replace("postgresql://", "postgresql+psycopg://", 1)
    return raw_url


DATABASE_URL = _normalize_database_url(os.getenv("DATABASE_URL", "").strip())


class Base(DeclarativeBase):
    pass


class OptimizationRunRecord(Base):
    __tablename__ = "optimization_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), default=datetime.utcnow, nullable=False)
    domain: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    solver: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    objective: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    solve_time: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    request_json: Mapped[str] = mapped_column(Text, nullable=False)
    result_json: Mapped[str] = mapped_column(Text, nullable=False)
    error_msg: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


engine = None
SessionLocal = None


def _ensure_database_config() -> None:
    global DATABASE_URL, engine, SessionLocal

    resolved_url = _normalize_database_url(os.getenv("DATABASE_URL", "").strip())
    if resolved_url == DATABASE_URL and engine is not None and SessionLocal is not None:
        return

    DATABASE_URL = resolved_url
    if not DATABASE_URL:
        engine = None
        SessionLocal = None
        return

    engine = create_engine(DATABASE_URL, future=True, pool_pre_ping=True)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def is_database_enabled() -> bool:
    _ensure_database_config()
    return engine is not None and SessionLocal is not None


def init_db() -> None:
    _ensure_database_config()
    if engine is None:
        return
    Base.metadata.create_all(bind=engine)


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    if SessionLocal is None:
        raise RuntimeError("Database is not configured. Set DATABASE_URL to enable persistence.")

    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def create_optimization_run(request_payload: Dict[str, Any], result_payload: Dict[str, Any]) -> Optional[int]:
    if SessionLocal is None:
        return None

    domain = str(request_payload.get("domain") or "unknown")
    solver = str(request_payload.get("solver") or "unknown")
    status = str(result_payload.get("status") or "unknown")
    objective = result_payload.get("objective")
    solve_time = float(result_payload.get("solve_time") or 0.0)
    error_msg = result_payload.get("error_msg")

    with get_db_session() as session:
        record = OptimizationRunRecord(
            domain=domain,
            solver=solver,
            status=status,
            objective=float(objective) if isinstance(objective, (int, float)) else None,
            solve_time=solve_time,
            request_json=json.dumps(request_payload, ensure_ascii=True),
            result_json=json.dumps(result_payload, ensure_ascii=True),
            error_msg=str(error_msg) if error_msg is not None else None,
        )
        session.add(record)
        session.flush()
        return int(record.id)


def serialize_optimization_run(record: OptimizationRunRecord) -> Dict[str, Any]:
    return {
        "id": record.id,
        "created_at": record.created_at.isoformat() + "Z",
        "domain": record.domain,
        "solver": record.solver,
        "status": record.status,
        "objective": record.objective,
        "solve_time": record.solve_time,
        "error_msg": record.error_msg,
        "request": json.loads(record.request_json),
        "result": json.loads(record.result_json),
    }


def list_optimization_runs(limit: int = 20) -> list[Dict[str, Any]]:
    if SessionLocal is None:
        return []

    capped_limit = max(1, min(int(limit or 20), 100))
    with get_db_session() as session:
        rows = (
            session.query(OptimizationRunRecord)
            .order_by(OptimizationRunRecord.created_at.desc(), OptimizationRunRecord.id.desc())
            .limit(capped_limit)
            .all()
        )
        return [serialize_optimization_run(row) for row in rows]