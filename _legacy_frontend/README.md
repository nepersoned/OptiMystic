# Legacy Frontend (React/Vite)

This directory contains the original React + Vite web UI for OptiMystic.

## Why archived

Superseded by a **Google Sheets Add-on** (`gsheets_addon/`) which offers:
- Zero upload friction — data is already in the spreadsheet
- Familiar UX for operations users
- Google Workspace Marketplace distribution
- Simpler deployment (no frontend hosting needed)

## Stack

- React 18 + TypeScript + Vite
- AG Grid (data grid editor)
- Tailwind CSS + shadcn/ui
- Zustand (state management)
- i18n: EN / KR

## Key pages

| Page | Path | Description |
|---|---|---|
| Upload | `/` | Drag & drop xlsx/csv, domain inference |
| Dataset | `/datasets/:id` | AG Grid editor + AI chat sidebar |
| Results | `/datasets/:id/results` | Charts, KPIs, bottleneck analysis |

## Running locally (if needed)

```bash
cd _legacy_frontend
npm install
npm run dev        # http://localhost:5173
```

Requires the FastAPI backend running on `http://localhost:8000`.
