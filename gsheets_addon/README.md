# OptiMystic — Google Sheets Add-on

AI operations consultant embedded directly in your spreadsheet.

## Files

| File | Description |
|---|---|
| `appsscript.json` | Manifest — OAuth scopes, runtime |
| `Code.gs` | Server-side: menu, sidebar, API calls, sheet read/write |
| `Sidebar.html` | Chat UI rendered in the sidebar |

## Setup

### 1. Deploy the backend
Make sure `python_solvers` is running (Cloud Run, Railway, etc.) and note the URL.

### 2. Create Apps Script project
1. Open any Google Sheet
2. **Extensions → Apps Script**
3. Copy `Code.gs` content into the editor (replace default `myFunction`)
4. Create a new HTML file named `Sidebar` and paste `Sidebar.html`
5. Replace `appsscript.json` content in Project Settings → `appsscript.json`

### 3. Set backend URL
Run `onOpen()` once manually, then use **OptiMystic → Settings** to enter your backend URL.

Or set it via Script Properties (Project Settings → Script Properties):
```
Key: BACKEND_URL
Value: https://your-backend.run.app
```

Current default in `Code.gs`:
```
https://optimystic-826180130763.asia-northeast3.run.app
```

### 4. Run
Reload the sheet → **OptiMystic → Open Chat** appears in the menu.

## How it works

```
Sheets sidebar
  → google.script.run.getSheetData()
  → Sidebar `fetch(backend/sheets/chat)` with message + sheet snapshot
  → Gemini 2.5 Flash replies
  → Sidebar shows response + optional "Apply changes" button
```

Notes:
- Sheet rows sent from add-on are capped to 200 rows (`values.slice(1, 201)`).
- Backend context currently uses up to 30 rows for prompt construction.
- Add-on network calls use a 30-second Apps Script deadline when server-side fetch is used.

## Suggested changes

If the AI suggests cell edits, a green box appears with a preview.
Click **✓ 적용** to write changes directly to the sheet.

## Local dev (clasp)

```bash
npm install -g @google/clasp
clasp login
clasp create --type sheets --title "OptiMystic"
clasp push
```

If this repo already has `gsheets_addon/.clasp.json`, you can skip `clasp create` and run:

```bash
cd gsheets_addon
clasp push
```
