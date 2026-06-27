# InferSQL Frontend

InferSQL Frontend is the demo-ready UI for exploring datasets, writing SQL, inspecting plans and debug metadata, saving reusable snippets, and generating SQL with the copilot.

## Views

- Query Workbench
  - SQL editor
  - Validate / Plan / Execute flow
  - Response, logical plan, physical plan, and debug tabs
  - Saved snippets with local persistence, rename, pin, delete, and compare snapshots
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

## Query workbench notes

- Query history is session-backed and stored in `sessionStorage`.
- Saved snippets are durable and stored in `localStorage`.
- History and snippets are intentionally separate:
  - history tracks recent validate / plan / execute / copilot activity
  - snippets store reusable named SQL across reloads
- Snippet comparison is lightweight and local-first:
  - save a snippet first
  - run validate, plan, or execute for matching SQL
  - inspect the latest saved snapshots in the compare panel

## Demo flow

1. Open Query Workbench.
2. Execute the starter SQL.
3. Switch to debug or plan views in the response panel.
4. Save the current SQL as a snippet.
5. Re-run validate, plan, or execute and inspect the snippet compare panel.
6. Open Catalog Explorer and inspect a dataset.
7. Insert SQL from catalog back into the editor.
8. Open Copilot and generate SQL from a natural-language prompt.
9. Send generated SQL back to the editor and execute it.
10. Open the benchmark viewer if a Phase 12 artifact is available.

## Demo screenshots

Capture and store screenshots in `docs/screenshots/` or `frontend/docs/screenshots/`.

Recommended screenshots:

1. `query-workbench-overview.png`
   - SQL editor visible
   - response panel visible
   - snippets or history visible

2. `query-debug-panel.png`
   - debug metadata cards visible
   - debug tab selected

3. `query-snippets-compare.png`
   - saved snippets visible
   - snippet compare panel visible
   - one compare tab selected

4. `catalog-explorer.png`
   - dataset list and dataset detail visible

5. `copilot-generated-sql.png`
   - prompt, generated SQL, validation, assumptions visible

6. `benchmark-viewer.png`
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

- Query history is session-backed and optimized for repeated experimentation in the current tab.
- Saved snippets persist across reloads in the current browser.
- Snippet compare snapshots are frontend-only and derived from the latest validate, plan, execute, or error response captured for a saved snippet.
- Benchmark viewing expects a static JSON artifact path when Phase 12 outputs are present.
- This frontend is optimized for demo clarity first, then iteration speed.