Todo list
Phase 0 — Project decisions
Freeze V1 target as 3-class next-5-day volatility regime classification.

Freeze V1 universe as either 20–30 ETFs or 50 liquid U.S. equities; my recommendation is ETFs first for faster alignment and cleaner first experiments.

Freeze primary evaluation split philosophy as strict time-based train / validation / test only, with no random cross-validation.

Freeze V1 models as Logistic Regression, XGBoost, LightGBM, and LSTM.

Freeze V1 stress families as noise, missingness, distribution shift, adversarial perturbation, and label-noise contamination.

Freeze V1 tracking stack as MLflow + local file-backed runs.

Freeze V1 app stack as Python package + CLI scripts + FastAPI skeleton; dashboard can come later after the audit pipeline works.

Acceptance criteria

One short design note exists in the repo describing task, target, split policy, metrics, and out-of-scope items.

No unresolved debate remains about target variable, asset universe, or model list before coding begins.

Phase 1 — Repo and environment
Create repo root structure:

data/

configs/

src/aegis/ingestion/

src/aegis/features/

src/aegis/models/

src/aegis/evaluation/

src/aegis/attacks/

src/aegis/shifts/

src/aegis/explainability/

src/aegis/api/

experiments/

reports/

tests/

Add pyproject.toml.

Add .gitignore.

Add README.md.

Add Makefile or simple task runner commands.

Create .venv and install initial dependencies.

Add ruff, black, pytest, and pre-commit config.

Add .env.example for optional API keys and config toggles.

Add first configs/base.yaml.

Acceptance criteria

pytest runs successfully even if there are only placeholder tests.

ruff check . and black --check . succeed.

python -m aegis or a simple CLI entrypoint runs without import errors.

Phase 2 — Data ingestion
Decide exact symbols list.

Implement OHLCV downloader module.

Implement FRED downloader module.

Define canonical date index and trading-day alignment behavior.

Standardize ticker naming and column naming.

Create raw data save format in data/raw/.

Create processed aligned panel save format in data/processed/.

Add validation checks:

Duplicate dates.

Unexpected null bursts.

Empty symbol series.

Macro forward-fill policy explicitly documented.

Add ingestion config fields for start date, end date, symbols, macro series, and refresh flags.

Write at least two tests for ingestion helpers.

Acceptance criteria

One command builds a merged panel dataset from raw downloads.

Output table is date-indexed, reproducible, and saved to disk.

Data dictionary markdown file exists with every raw field explained.

Phase 3 — Targets and features
Implement log returns.

Implement rolling return means.

Implement rolling standard deviation / realized volatility.

Implement momentum windows.

Implement moving-average spreads.

Implement RSI.

Implement drawdown features.

Implement volume shock features.

Implement SPY / market context features.

Implement macro delta and trend features.

Implement target generation for next-5-day realized volatility regime.

Define label thresholds, ideally from rolling or training-only quantiles.

Add leakage-safe shifting and windowing checks.

Save processed feature matrix and metadata.

Acceptance criteria

Every feature documents whether it uses only information available at prediction time.

Target labels are generated with no lookahead leakage.

Final training table contains no unexplained NaNs.

One unit test catches a deliberate leakage bug.

Phase 4 — Splits and benchmark protocol
Define train / validation / test date ranges in config.

Add optional backtest-style rolling evaluation config for later.

Implement split module that slices strictly by date.

Save split manifests with row counts and class balance.

Create evaluation schema for metrics and artifacts.

Decide primary clean benchmark metrics:

Accuracy.

Macro F1.

ROC-AUC if supported for multiclass.

PR-AUC if feasible.

Calibration error.

Confusion matrix.

Add baseline “dummy classifier” for sanity comparison.

Acceptance criteria

A split report exists before any model training starts.

Class proportions for each split are saved and reviewed.

No overlapping dates appear across train, validation, and test.

Phase 5 — Baseline models
Implement common model interface:

fit

predict

predict_proba

save

load

Implement Logistic Regression pipeline.

Implement XGBoost pipeline.

Implement LightGBM pipeline.

Add feature scaling only where appropriate.

Add class-weight handling if imbalance requires it.

Add hyperparameter config blocks.

Log every run to MLflow with params, metrics, and artifacts.

Save predictions and probability outputs for every run.

Acceptance criteria

One command trains all classical models on the same split.

MLflow logs parameters, metrics, code version context, and artifacts for each run.

A benchmark table compares all clean runs in one place.

Phase 6 — Advanced model
Build sequence dataset formatter for LSTM.

Define sequence length and feature tensor layout.

Implement training loop with validation monitoring.

Add early stopping.

Save model checkpoints and training curves.

Add probability calibration check if outputs are poorly calibrated.

Log run artifacts to MLflow.

Acceptance criteria

LSTM trains end-to-end on the same split protocol.

Output probabilities are saved in the same format as tabular models.

Results can be compared directly against classical models.

Phase 7 — Robustness engine I
Create perturbation interface:

fit_context

apply

name

severity

Implement Gaussian noise perturbation.

Implement variance-scaled noise perturbation.

Implement burst-window noise.

Implement MCAR missingness.

Implement feature-group dropout.

Implement stale macro simulation.

Implement time-based shift protocols, such as pre-period vs post-period and calm vs volatile windows.

Add clean-vs-stressed metric comparison report.

Acceptance criteria

A single audit command can run clean and stressed evaluation for one model.

Results are saved as machine-readable JSON/CSV and human-readable markdown.

You can rank models by worst-case and average degradation.

Phase 8 — Robustness engine II
Implement adversarial perturbation wrapper for differentiable models.

Implement heuristic threshold-crossing or importance-guided perturbation for tree models.

Implement label-noise contamination experiments for training data.

Implement outlier-row contamination experiments.

Add severity sweep support.

Add confidence degradation analysis under attack.

Acceptance criteria

At least one adversarial-style attack works on LSTM or another differentiable model.

At least one tree-model perturbation heuristic is implemented and documented clearly as heuristic rather than exact gradient attack.

Worst-case robustness summary exists for all core models.

Phase 9 — Explainability and drift
Add SHAP for XGBoost and LightGBM first.

Add global importance plots on clean data.

Add local explanations for representative rows.

Compute SHAP or explanation summaries on stressed data.

Implement feature ranking change comparison.

Implement explanation drift score.

Write model-card style failure notes per model.

Acceptance criteria

At least one report shows the model lost performance and its feature logic changed under stress.

Feature ranking changes are saved numerically, not just plotted visually.

One markdown report narrates clean vs stressed explanation behavior.

Phase 10 — Reporting and artifacts
Define standard report bundle:

metrics summary

confusion matrix

calibration plot

robustness table

worst-case scenario summary

explanation drift summary

deployment recommendation

Implement report generator that writes markdown and JSON.

Save all plots to reports/figures/.

Save benchmark tables to reports/tables/.

Add one combined “audit report” artifact per run.

Acceptance criteria

A finished run generates a reusable artifact bundle without manual notebook cleanup.

Reports are understandable without opening the training code.

Phase 11 — API layer
Create FastAPI app package structure:

main.py

routers/

schemas/

services/

core/config.py

Implement /health.

Implement /train.

Implement /audit/run.

Implement /audit/results/{id}.

Implement /model/compare.

Add Pydantic request/response schemas.

Keep route handlers thin and push logic into services.

Acceptance criteria

API can trigger at least one train job and one audit job locally.

Responses are schema-validated and documented in OpenAPI.

The API layer contains orchestration, not core ML logic.

Phase 12 — Dashboard or UI
Decide V1 UI as Streamlit for speed or React later for stronger SWE polish.

Build benchmark overview page.

Build stress-test comparison page.

Build explanation drift page.

Build run-detail page.

Add filters by model, stress type, and severity.

Add export/download buttons for reports.

Acceptance criteria

A reviewer can understand the project by clicking through the UI without reading code first.

Charts and tables match saved artifact outputs exactly.

Phase 13 — Testing and quality
Add unit tests for feature generation.

Add unit tests for split logic.

Add unit tests for perturbation modules.

Add integration test for one end-to-end mini pipeline.

Add API tests for core endpoints.

Add CI workflow for lint + test.

Add regression fixture for one tiny sample dataset.

Acceptance criteria

CI passes on every push.

A mini end-to-end test proves the project is reproducible on a toy dataset.

Phase 14 — Portfolio packaging
Write polished README sections:

motivation

dataset

task

models

robustness methods

results

architecture

how to run

roadmap

Create architecture diagram.

Create one technical writeup.

Draft résumé bullets.

Record short demo video.

Add screenshots and example reports.

Acceptance criteria

GitHub landing page explains the project in under 60 seconds of reading.

A recruiter can see both ML depth and engineering maturity immediately.

Week 1 focus
For this week, the only things we should touch are the items that unlock the whole pipeline:

Freeze target and universe.

Create repo structure.

Set up environment and tooling.

Build data ingestion.

Build aligned panel output.

Write the first config file.

Add one smoke test.

Add one benchmark notebook or script only for sanity checking, not as the final architecture.

Your Week 1 success condition is simple: one command should produce a clean, date-aligned dataset ready for feature engineering. That is more important than having a dashboard, a deep model, or fancy attacks early.

Immediate next tasks
Here is the exact sequence I’d follow tomorrow:

Create the repo skeleton and config files.

Add dependency and tooling setup.

Implement ingestion/market_data.py and ingestion/macro_data.py.

Implement ingestion/build_panel.py.

Save one reproducible processed dataset.

Add a short project decision memo in the repo.