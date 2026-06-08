# BastionQuant

BastionQuant is a financial ML robustness auditing platform for training market models, stress-testing them under perturbations and distribution shifts, and generating deployment-oriented diagnostics.

## V1 scope

- Task: next-5-day volatility regime classification
- Data: OHLCV + macroeconomic context
- Models: logistic regression, XGBoost, LightGBM, LSTM
- Robustness tests: noise, missingness, shift, adversarial perturbation, contamination
- Explainability: SHAP-based drift diagnostics

## Initial goals

1. Build a clean, leakage-safe panel dataset.
2. Train baseline benchmark models.
3. Add stress-testing and reporting.
4. Package the workflow into reproducible CLI and API entry points.

## Quick start

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -U pip
pip install -e .[dev]
copy .env.example .env
python -m bastionquant ingest --config configs/base.yaml
```

## Notes

- Set `FRED_API_KEY` in your environment or `.env`.
- Output data will be written under `data/raw/` and `data/processed/`.