Phase F1 – Scaffold
Status: [ ]

Goal: establish a clean frontend app with shared infrastructure.

Deliverables:

Create frontend/ with Vite + React + TypeScript.

Add Tailwind, TanStack Query, React Router, and a small API client layer.

Add app shell layout: sidebar, top bar, main workspace.

Add environment config for backend base URL.

Add basic theme tokens, loading states, and normalized error display.

Suggested structure:

text
frontend/
├── src/
│   ├── app/
│   ├── components/
│   ├── features/
│   │   ├── catalog/
│   │   ├── query/
│   │   ├── copilot/
│   │   └── settings/
│   ├── lib/
│   │   ├── api/
│   │   ├── query-client/
│   │   └── utils/
│   ├── routes/
│   └── types/
├── public/
└── package.json
Exit criteria:

Frontend boots locally.

Can reach backend base URL.

Query client/provider wired once at app root, which is the recommended TanStack Query pattern.

Phase F2 – Query Workbench MVP
Status: [ ]

Goal: ship the first real user-facing InferSQL surface.

Deliverables:

“Query Workbench” page.

Monaco SQL editor with starter SQL and run buttons.

Tabs or panels for:

Validate

Plan

Execute

Results table for rows/columns.

Debug panel for stage, engine, features, timings.

Error panel that renders normalized backend errors consistently.

Query history in memory for current session.

Core UX:

Left: dataset browser.

Center: SQL editor.

Right/bottom: results, plan, debug, errors.

Exit criteria:

User can type SQL and call /query/validate, /query/plan, /query/execute.

Results, plans, and errors render clearly.

End-to-end demo works against your current backend API.

Phase F3 – Catalog and Dataset Explorer
Status: [ ]

Goal: make schema discovery easy so users do not need to guess tables and columns.

Deliverables:

Dataset list from GET /catalog/datasets.

Dataset detail drawer/page from GET /catalog/datasets/{name}.

Display:

dataset description,

row count,

source path / loaded time when available,

columns and types,

optional column descriptions,

sample values if returned.

“Insert sample query” actions:

SELECT * FROM dataset LIMIT 10

basic aggregate examples

join example when paired datasets exist

Exit criteria:

User can browse datasets without leaving the app.

Dataset metadata helps author SQL faster.

Phase F4 – Ingestion UI
Status: [ ]

Goal: make dataset registration usable from the frontend.

Deliverables:

Local path ingestion form for /catalog/ingest.

File upload form for /catalog/upload.

Overwrite toggle.

Success/failure toasts or inline notices.

Automatic catalog refresh after successful ingest.

Nice-to-have:

ingest preview summary,

recent ingests list,

validation hints for unsupported formats.

Exit criteria:

A new dataset can be registered from the UI and then queried immediately.

Phase F5 – Copilot UI
Status: [ ]

Goal: expose the backend’s NL→SQL flow in a controlled, inspectable way.

Deliverables:

Natural-language prompt input.

“Generate SQL” action.

Show:

candidate SQL,

assumptions,

selected tables if returned,

validation result,

optional execution result.

“Send to editor” button.

Repair/retry history panel if backend returns it.

Design principle:

Copilot should feel like an assistant, not a black box.

Always show generated SQL and validation outcome before encouraging trust.

Exit criteria:

A user can ask a natural-language question and inspect the generated SQL path end to end.

Phase F6 – Query History and Saved Sessions
Status: [ ]

Goal: make the workbench feel like a real tool rather than a one-shot demo.

Deliverables:

Query history list.

Re-run previous SQL.

Save named query snippets.

Pin favorite queries.

Compare validate/plan/execute outputs for a query.

Important note:

Start with in-memory or local frontend persistence only if you want speed.

If you want to stay aligned with your backend rigor, you can defer durable persistence until you define a backend contract for it.

Exit criteria:

Users can return to prior work without retyping.

Phase F7 – Visualization and Result UX
Status: [ ]

Goal: improve usability for larger result sets and make benchmark/demo flows more compelling.

Deliverables:

Better result table:

sticky header,

column resizing,

copy cell/row,

CSV export.

Lightweight charts for obvious aggregate result sets.

Plan tree viewer for logical/physical plan output.

Better JSON viewers for debug payloads.

Exit criteria:

Query results are easy to inspect beyond the raw JSON stage.

Phase F8 – Observability UI
Status: [ ]

Goal: expose the backend’s debug and performance signals in a useful way.

Deliverables:

Request timeline card using debug.total_ms.

Engine/stage badges.

Feature flags display (join, set_op, window, derived_from).

Benchmark artifact viewer:

upload/open JSON/CSV summaries,

display baseline results,

maybe simple charts later.

Exit criteria:

Developers can use the UI as a lightweight internal console for backend behavior.

Phase F9 – Polishing and Demo Readiness
Status: [ ]

Goal: make the frontend presentable for demos, portfolio use, and faster iteration.

Deliverables:

Empty/loading/error states across the app.

Keyboard shortcuts:

run query,

format SQL,

focus editor,

open catalog.

Responsive layout for laptop and tablet widths.

Cleaner branding/copy.

README for frontend local setup.

Screenshots or demo GIFs.

Exit criteria:

The app feels coherent enough to show other people without caveats every minute.

Recommended order
I’d do the frontend in this order:

F1 – Scaffold

F2 – Query Workbench MVP

F3 – Catalog Explorer

F4 – Ingestion UI

F5 – Copilot UI

F6 – Query History

F7 – Visualization

F8 – Observability UI

F9 – Polish

That order mirrors the backend’s real strengths: query core first, schema second, ingestion third, copilot after the core experience is solid.

Suggested frontend MVP definition
Your first true frontend milestone should probably stop at:

F1 complete

F2 complete

F3 complete

That is enough to call it an InferSQL frontend MVP:

browse datasets,

write SQL,

validate/plan/execute,

inspect results and debug data.

Proposed todo.md section
You could add this as a new top-level frontend roadmap:

text
## Frontend roadmap

### Phase F1 – Frontend scaffold
Status: [x]

- [x] Create `frontend/` with Vite + React + TypeScript.
- [x] Add Tailwind, TanStack Query, routing, and shared API client setup.
- [x] Add app shell layout and backend base URL configuration.
- [x] Add shared loading and normalized error components.

### Phase F2 – Query workbench MVP
Status: [x]

- [x] Add editable SQL input.
- [x] Wire `validate`, `plan`, and `execute` actions to backend endpoints.
- [x] Show raw JSON responses for validate/plan/execute.
- [x] Show normalized backend errors.
- [x] Add in-memory query history.

### Phase F3 – Catalog Explorer
Status: [x]

- [x] Build dataset list and dataset detail views from catalog endpoints.
- [x] Show schema, types, descriptions, row counts, and samples where available.
- [x] Add quick actions to insert example SQL into the editor.

### Phase F4 – Ingestion UI
Status: [ ]

- [ ] Add local-path ingest form for `/catalog/ingest`.
- [ ] Add upload form for `/catalog/upload`.
- [ ] Add overwrite toggle and refresh catalog on success.

### Phase F5 – Copilot UI
Status: [ ]

- [ ] Add NL→SQL prompt input and generated SQL display.
- [ ] Show assumptions, validation output, and optional execution result.
- [ ] Add “send to editor” and repair-history display.

### Phase F6 – Query History
Status: [ ]

- [ ] Add saved queries, favorites, and rerun support.
- [ ] Improve session continuity for repeated experimentation.

### Phase F7 – Result UX and Visualization
Status: [ ]

- [ ] Improve result table usability.
- [ ] Add CSV export and lightweight charts for aggregate outputs.
- [ ] Add a better plan/debug viewer.

### Phase F8 – Observability UI
Status: [ ]

- [ ] Surface engine, stage, timing, and feature debug metadata clearly.
- [ ] Add benchmark artifact viewing for Phase 12 outputs.

### Phase F9 – Polish
Status: [ ]

- [ ] Add keyboard shortcuts, responsive cleanup, and refined empty/error states.
- [ ] Add frontend README and demo-ready screenshots.

