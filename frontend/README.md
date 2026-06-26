# InferSQL Frontend

InferSQL Frontend is the demo-ready UI for exploring datasets, writing SQL, inspecting plans and debug metadata, and generating SQL with the copilot.

## Views

- Query Workbench
  - SQL editor
  - Validate / Plan / Execute flow
  - Response, logical plan, physical plan, and debug tabs
  - Query history, result chart, result table, benchmark viewer
- Catalog Explorer
  - Dataset list
  - Dataset detail
  - Local path and upload ingest flows
- Copilot
  - Natural-language prompt to SQL
  - Validation, assumptions, repair history, and optional execution output

## Run locally

```bash
npm install
npm run dev
```

Use the frontend dev server URL shown by Vite.

## Keyboard shortcuts

### Global navigation

- `g q` → Open Query Workbench
- `g c` → Open Catalog Explorer
- `g p` → Open Copilot

### Query editor

- `Ctrl/Cmd + Enter` → Execute
- `Ctrl/Cmd + Shift + Enter` → Plan
- `Ctrl/Cmd + Alt + Enter` → Validate

### Copilot prompt

- `Ctrl/Cmd + Enter` → Generate SQL

## Demo flow

1. Open Query Workbench.
2. Execute the starter SQL.
3. Switch to debug or plan views in the response panel.
4. Open Catalog Explorer and inspect a dataset.
5. Insert SQL from catalog back into the editor.
6. Open Copilot and generate SQL from a natural-language prompt.
7. Send generated SQL back to the editor and execute it.
8. Open the benchmark viewer if a Phase 12 artifact is available.

## Demo screenshots

Capture and store screenshots in `docs/screenshots/` or `frontend/docs/screenshots/`.

Recommended screenshots:

1. `query-workbench-overview.png`
   - SQL editor visible
   - response panel visible
   - history visible

2. `query-debug-panel.png`
   - debug metadata cards visible
   - debug tab selected

3. `catalog-explorer.png`
   - dataset list and dataset detail visible

4. `copilot-generated-sql.png`
   - prompt, generated SQL, validation, assumptions visible

5. `benchmark-viewer.png`
   - benchmark artifact table visible

## Screenshot checklist

Before capturing screenshots:

- use seeded or stable demo data
- keep browser zoom at 100%
- use a consistent window width
- prefer dark mode consistently across all shots
- clear distracting devtool panes
- make sure empty states are intentional if shown
- avoid showing localhost errors or transient loading flashes

## Notes

- Query history is session-backed in the current frontend.
- Benchmark viewing expects a static JSON artifact path when Phase 12 outputs are present.
- This frontend is optimized for demo clarity first, then iteration speed.