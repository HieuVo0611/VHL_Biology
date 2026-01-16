<!-- Auto-generated: concise instructions for AI coding agents working on this repo -->
# Copilot instructions — VHL_Biology

Purpose: quick reference for an AI coding agent to become productive in this repository.

- **Big picture**: This repo implements data processing, feature extraction, classification (CatBoost) and LSTM time-series inference for dissolved-oxygen (DO) experiments. The UI is a Streamlit dashboard (`app.py`) that ties together preprocessing (`src/utils.py`), model inference (`model/`), and file uploads (`temp.txt`, `temp.xlsx`). There is also an OriginPro automation helper (`peak_finder.py`) used for peak extraction on Windows.

- **Major components / flow**:
  - Raw data: `data/` (text and Excel exports from instruments).
  - Preprocessing & feature engineering: `src/utils.py` (key functions: `extract_metadata_single_sample`, `aggregate_features`, `process_and_predict_lstm`, `catboost_inference_from_csv`, `calculate_toxicity`).
  - Models: stored under `model/` (examples: `catboost_model.cbm`, `label_encoder_classes.npy`, LSTM under `model/LSTM Model/*`).
  - App: `app.py` — Streamlit front-end that writes uploaded files to `temp.txt`/`temp.xlsx` and calls functions from `src/utils.py`.
  - Analysis scripts and training experiments: `code/` and `notebooks/` contain training code and notebooks.

- **Why things are structured this way**: models live in `model/` and are loaded at runtime; `src/utils.py` centralizes domain logic so `app.py` remains lightweight. `temp.txt`/`temp.xlsx` are used as transient upload targets by Streamlit.

- **Run / debug quickly (Windows)**:
  - Install deps:
    ```bash
    pip install -r requirements.txt
    ```
  - Run the Streamlit UI locally:
    ```bash
    streamlit run app.py
    ```
  - Run example utils script (quick smoke):
    ```bash
    python -c "from src.utils import process_and_predict_lstm; import plotly; process_and_predict_lstm('data/GGA/File txt/.../sample.txt','model/LSTM Model/28_07_2025/enc-dec_lstm_model.h5')"
    ```
  - Run classification script:
    ```bash
    python code/gga_classification_model.py
    ```

- **File/format conventions agents should follow**:
  - Excel sample parsing: `extract_metadata_single_sample` expects the sample name to contain `Q=` in the first header row; it uses relative column offsets to find `Tag`, `Doin (mV)`, `No.peak`, `DOmin (mV)`, `DDO (mV)`.
  - Streamlit writes uploaded files to `temp.txt` / `temp.xlsx`; edits to the UI should preserve that pattern or update both `app.py` and downstream callers in `src/utils.py`.
  - Model inference functions expect aggregated features (use `aggregate_features`) and return zipped tuples: `(sample_name, prediction_label, probability_array)` for CatBoost.

- **Platform and integration notes**:
  - `peak_finder.py` uses `originpro` and LabTalk scripting — Windows-only and requires OriginPro installed and accessible to Python. Avoid trying to run that on CI or Linux containers.
  - TensorFlow / Keras LSTM models are loaded with `keras.models.load_model` in `src/utils.py` — keep TensorFlow versions compatible with `requirements.txt`.

- **Patterns & small examples**:
  - Use `src/utils.process_and_predict_lstm(txt_path, model_path, lookback=7)` to get a Plotly `fig` for a single `.txt` file.
  - Use `src/utils.extract_metadata_single_sample(xlsx_path)` to obtain a DataFrame, then cast numeric columns before calling `catboost_inference_from_csv`.
    Example snippet:
    ```py
    from src.utils import extract_metadata_single_sample, catboost_inference_from_csv
    df = extract_metadata_single_sample('temp.xlsx')
    for c in ['Doin (mV)','No.peak','DOmin (mV)','DDO (mV)']:
        df[c] = pd.to_numeric(df[c], errors='coerce')
    results = catboost_inference_from_csv(df,'model/catboost_model.cbm','model/label_encoder_classes.npy')
    ```

- **What an AI agent should avoid changing without CI or human sign-off**:
  - `requirements.txt` TensorFlow/CatBoost pinning — changes can break runtime on developer machines.
  - Windows-specific `originpro` automation in `peak_finder.py`.
  - Paths under `model/` used by `app.py` (update both `app.py` and `src/utils.py` if relocating models).

- **Missing/undeclared conventions**:
  - No tests or CI detected; add tests under `tests/` if adding logic and include a `requirements-dev.txt`.
  - No `.github` actions defined — avoid assuming CI runs.

If anything is unclear or you want added examples (e.g., unit test template, CI workflow, or contributor guidelines), tell me which section to expand.
