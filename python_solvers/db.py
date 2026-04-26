from __future__ import annotations

import json
import os
import hashlib
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


class Dataset(Base):
    __tablename__ = "datasets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), default=datetime.utcnow, nullable=False)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(256), nullable=False)
    tenant_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, index=True)
    current_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)


class DatasetVersion(Base):
    __tablename__ = "dataset_versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    dataset_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), default=datetime.utcnow, nullable=False)
    data_json: Mapped[str] = mapped_column(Text, nullable=False)
    columns_json: Mapped[str] = mapped_column(Text, nullable=False)
    note: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)


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


class OptimizationIdempotencyRecord(Base):
    __tablename__ = "optimization_idempotency"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), default=datetime.utcnow, nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    run_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    response_json: Mapped[str] = mapped_column(Text, nullable=False)


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


def _stable_json(payload: Dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _request_hash(payload: Dict[str, Any]) -> str:
    return hashlib.sha256(_stable_json(payload).encode("utf-8")).hexdigest()


def get_idempotent_response(idempotency_key: str, request_payload: Dict[str, Any]) -> Dict[str, Any]:
    if SessionLocal is None:
        return {"state": "disabled"}

    key = (idempotency_key or "").strip()
    if not key:
        return {"state": "disabled"}

    req_hash = _request_hash(request_payload)

    with get_db_session() as session:
        record = (
            session.query(OptimizationIdempotencyRecord)
            .filter(OptimizationIdempotencyRecord.idempotency_key == key)
            .one_or_none()
        )
        if record is None:
            return {"state": "miss", "request_hash": req_hash}

        if record.request_hash != req_hash:
            return {"state": "conflict"}

        try:
            payload = json.loads(record.response_json)
        except Exception:
            payload = {}

        return {
            "state": "hit",
            "response_payload": payload if isinstance(payload, dict) else {},
            "run_id": record.run_id,
        }


def save_idempotent_response(
    idempotency_key: str,
    request_payload: Dict[str, Any],
    response_payload: Dict[str, Any],
    run_id: Optional[int] = None,
) -> None:
    if SessionLocal is None:
        return

    key = (idempotency_key or "").strip()
    if not key:
        return

    req_hash = _request_hash(request_payload)

    with get_db_session() as session:
        record = (
            session.query(OptimizationIdempotencyRecord)
            .filter(OptimizationIdempotencyRecord.idempotency_key == key)
            .one_or_none()
        )

        if record is None:
            record = OptimizationIdempotencyRecord(
                idempotency_key=key,
                request_hash=req_hash,
                run_id=run_id,
                response_json=json.dumps(response_payload, ensure_ascii=True),
            )
            session.add(record)
            return

        if record.request_hash != req_hash:
            raise ValueError("idempotency_key_conflict")

        record.run_id = run_id if run_id is not None else record.run_id
        record.response_json = json.dumps(response_payload, ensure_ascii=True)


def serialize_optimization_run(record: OptimizationRunRecord) -> Dict[str, Any]:
    request_payload = json.loads(record.request_json)
    tenant_id = None
    if isinstance(request_payload, dict):
        raw_tenant_id = request_payload.get("tenant_id")
        if raw_tenant_id is not None:
            tenant_id = str(raw_tenant_id)

    return {
        "id": record.id,
        "created_at": record.created_at.isoformat() + "Z",
        "domain": record.domain,
        "solver": record.solver,
        "status": record.status,
        "objective": record.objective,
        "solve_time": record.solve_time,
        "error_msg": record.error_msg,
        "tenant_id": tenant_id,
        "request": request_payload if isinstance(request_payload, dict) else {},
        "result": json.loads(record.result_json),
    }


def create_dataset(
    name: str, filename: str, tenant_id: Optional[str], rows: list, columns: list
) -> int:
    with get_db_session() as session:
        ds = Dataset(name=name, original_filename=filename, tenant_id=tenant_id, current_version=1)
        session.add(ds)
        session.flush()
        ver = DatasetVersion(
            dataset_id=ds.id,
            version=1,
            data_json=json.dumps(rows, ensure_ascii=True),
            columns_json=json.dumps(columns, ensure_ascii=True),
            note="initial upload",
        )
        session.add(ver)
        return int(ds.id)


def list_datasets(tenant_id: Optional[str] = None) -> list[Dict[str, Any]]:
    with get_db_session() as session:
        q = session.query(Dataset)
        if tenant_id:
            q = q.filter(Dataset.tenant_id == tenant_id)
        rows = q.order_by(Dataset.created_at.desc()).limit(100).all()
        return [
            {
                "id": ds.id,
                "name": ds.name,
                "original_filename": ds.original_filename,
                "current_version": ds.current_version,
                "tenant_id": ds.tenant_id,
                "created_at": ds.created_at.isoformat() + "Z",
            }
            for ds in rows
        ]


def _load_dataset_version(session: Any, dataset_id: int, version: int) -> Optional[Dict[str, Any]]:
    ds = session.query(Dataset).filter(Dataset.id == dataset_id).one_or_none()
    if ds is None:
        return None
    ver = (
        session.query(DatasetVersion)
        .filter(DatasetVersion.dataset_id == dataset_id, DatasetVersion.version == version)
        .one_or_none()
    )
    if ver is None:
        return None
    return {
        "dataset_id": ds.id,
        "name": ds.name,
        "original_filename": ds.original_filename,
        "tenant_id": ds.tenant_id,
        "current_version": ds.current_version,
        "version": ver.version,
        "rows": json.loads(ver.data_json),
        "columns": json.loads(ver.columns_json),
        "note": ver.note,
        "created_at": ver.created_at.isoformat() + "Z",
    }


def get_dataset_latest_version(dataset_id: int) -> Optional[Dict[str, Any]]:
    with get_db_session() as session:
        ds = session.query(Dataset).filter(Dataset.id == dataset_id).one_or_none()
        if ds is None:
            return None
        return _load_dataset_version(session, dataset_id, ds.current_version)


def get_dataset_version(dataset_id: int, version: int) -> Optional[Dict[str, Any]]:
    with get_db_session() as session:
        return _load_dataset_version(session, dataset_id, version)


def add_dataset_version(
    dataset_id: int, rows: list, columns: list, note: Optional[str] = None
) -> int:
    with get_db_session() as session:
        ds = session.query(Dataset).filter(Dataset.id == dataset_id).one_or_none()
        if ds is None:
            raise ValueError(f"Dataset {dataset_id} not found")
        new_version = ds.current_version + 1
        ds.current_version = new_version
        ver = DatasetVersion(
            dataset_id=dataset_id,
            version=new_version,
            data_json=json.dumps(rows, ensure_ascii=True),
            columns_json=json.dumps(columns, ensure_ascii=True),
            note=note,
        )
        session.add(ver)
        return new_version


def list_dataset_versions(dataset_id: int) -> list[Dict[str, Any]]:
    with get_db_session() as session:
        vers = (
            session.query(DatasetVersion)
            .filter(DatasetVersion.dataset_id == dataset_id)
            .order_by(DatasetVersion.version.asc())
            .all()
        )
        return [
            {
                "version": v.version,
                "note": v.note,
                "created_at": v.created_at.isoformat() + "Z",
            }
            for v in vers
        ]


def list_optimization_runs(limit: int = 20, tenant_id: str | None = None) -> list[Dict[str, Any]]:
    if SessionLocal is None:
        return []

    capped_limit = max(1, min(int(limit or 20), 100))
    tenant_filter = (tenant_id or "").strip()
    fetch_limit = capped_limit if not tenant_filter else min(500, capped_limit * 10)

    with get_db_session() as session:
        rows = (
            session.query(OptimizationRunRecord)
            .order_by(OptimizationRunRecord.created_at.desc(), OptimizationRunRecord.id.desc())
            .limit(fetch_limit)
            .all()
        )

        serialized = [serialize_optimization_run(row) for row in rows]
        if not tenant_filter:
            return serialized[:capped_limit]

        filtered = [row for row in serialized if str(row.get("tenant_id") or "") == tenant_filter]
        return filtered[:capped_limit]