## Frontend roadmap

### Phase F1 – Frontend scaffold
Status: [x]

- [x] Create `frontend/` with Vite + React + TypeScript.
- [x] Add Tailwind, TanStack Query, routing, and shared API client setup.
- [x] Add app shell layout and backend base URL configuration.
- [x] Add shared loading and normalized error components.

### Phase F2 – Query workbench MVP
Status: [ ]

- [x] Add editable SQL input.
- [x] Wire `validate`, `plan`, and `execute` actions to backend endpoints.
- [x] Show raw JSON responses for validate/plan/execute.
- [x] Show normalized backend errors.
- [x] Add in-memory or session-backed query history.
- [ ] Replace textarea editor with Monaco SQL editor.

### Phase F3 – Catalog Explorer
Status: [x]

- [x] Build dataset list and dataset detail views from catalog endpoints.
- [x] Show schema, types, descriptions, row counts, and samples where available.
- [x] Add quick actions to insert example SQL into the editor.

### Phase F4 – Ingestion UI
Status: [x]

- [x] Add local-path ingest form for `/catalog/ingest`.
- [x] Add upload form for `/catalog/upload`.
- [x] Add overwrite toggle and refresh catalog on success.

### Phase F5 – Copilot UI
Status: [x]

- [x] Add NL→SQL prompt input and generated SQL display.
- [x] Show assumptions, validation output, and optional execution result.
- [x] Add “send to editor” and repair-history display.

### Phase F6 – Query History & Saved Snippets
Status: [x]

- [x] Add query history list.
- [x] Add rerun/load-into-editor support.
- [x] Add favorites.
- [x] Improve session continuity for repeated experimentation.
- [x] Add saved named query snippets.
- [x] Add validate/plan/execute output comparison for a selected query.

### Phase F7 – Result UX and Visualization
Status: [x]

- [x] Improve result table usability.
- [x] Add CSV export and lightweight charts for aggregate outputs.
- [x] Add a better plan/debug viewer.

### Phase F8 – Observability UI
Status: [x]

- [x] Surface engine, stage, timing, and feature debug metadata clearly.
- [x] Add benchmark artifact viewing for Phase 12 outputs.

### Phase F9 – Polish
Status: [x]

- [x] Add keyboard shortcuts, responsive cleanup, and refined empty/error states.
- [x] Add frontend README and demo-ready screenshots.