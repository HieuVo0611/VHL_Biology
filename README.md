# VHL Biology Project

**Version**: 1.1.0 | **Last Updated**: 2026-03-11 | **Status**: Production Ready

Production ML system for dissolved oxygen (DO) analysis. Classifies biological samples (GGA vs GGA-metal), extracts DO peaks using adaptive two-pass algorithm, and predicts BOD metrics—entirely from TXT file uploads with no Excel dependency.

**Full pipeline verified**: TXT → Peaks → Classification → Toxicity (tested 2026-03-11).

## Quick Start

1. **Environment** (conda `vhl` recommended):
```bash
conda activate vhl
# or: pip install -r requirements.txt
```

2. **Run the Streamlit dashboard:**
```bash
streamlit run app.py
```
Dashboard walks you through: Upload TXT → Extract Peaks → LSTM → Classification → Toxicity.

## Project Overview

**Core Purpose**: Analyze DO degradation patterns from TXT files using production-tuned peak extraction, classify samples, and forecast time-series.
**Key Components**: Adaptive peak extraction (2-pass HH detection, +0.05mV non-HH bias), Classification (CatBoost primary, RF/XGBoost), Time-series forecasting (LSTM encoder-decoder)
**Production Pipeline**: UTF-16 TXT → extract_peaks_from_txt() → peaks DataFrame → Classification → Toxicity
**Python Environment**: conda env `vhl` (CatBoost 1.2.8, TensorFlow 2.19.0, SciPy, Keras 3.10.0)

## Directory Structure

```
VHL_Biology/
├── code/                          # Analysis scripts (legacy + training)
│   ├── gga_classification_model.py # RF/XGBoost classifier (70+ features)
│   ├── extract_DO_in.py           # Legacy Savitzky-Golay extraction
│   ├── extract_special_points.py  # Fixed-interval extraction
│   ├── ema_model.py               # EMA forecasting with RF
│   ├── process_txt_data.py        # UTF-16 TXT → CSV conversion
│   ├── check_matching_name.py     # Fuzzy name matching
│   └── train extract special points/  # ML-based extraction training
├── src/                           # Production modules
│   ├── peak_extractor.py          # Production adaptive peak extraction (448 lines)
│   ├── utils.py                   # Feature engineering, CatBoost, LSTM, toxicity (549 lines)
│   └── visualize_data.py          # Visualization with peak marking
├── tools/                         # Optimization & reporting utilities
│   ├── derive_metadata_from_txt.py # Signal processing peak detection
│   ├── validate_metadata.py       # Tolerance-based validation
│   ├── analyze_metal_errors.py    # Per-peak error analysis (4 datasets)
│   ├── test_metal_targeted.py     # 47 bias/param configurations
│   ├── test_bias_finetune.py      # Bias fine-tuning (19 configs)
│   ├── test_ml_correction.py      # ML correction experiment (GBR/RF)
│   ├── generate_comprehensive_report.py  # Word report generation
│   └── generate-progress-report-260311.py # Vietnamese progress report
├── model/                          # Trained models (versioned)
│   ├── LSTM Model/28_07_2025/    # LSTM encoder-decoder (lookback=7, Huber loss)
│   ├── RF Model/03012025/         # Random Forest classifier
│   ├── catboost_model.cbm         # CatBoost classifier (production)
│   └── label_encoder_classes.npy
├── notebooks/                      # Jupyter notebooks (baselines)
│   ├── ARIMA_1_0_Bio_VHL.ipynb
│   ├── LSTM_Bio_VHL.ipynb
│   ├── LR_BIO_VHL.ipynb
│   └── SMA_EWMA_method.ipynb
├── data/
│   ├── GGA/, GGA-metal/, BOD-Hieu/  # Sample data (UTF-16 TXT)
│   ├── metadata-gga-*.csv         # Extracted metadata
│   └── ext_v16_*.csv              # Algorithm-extracted peaks
├── docs/                          # Documentation
├── plans/reports/                 # Optimization reports & Vietnamese progress reports
└── app.py                         # Streamlit 5-step TXT-only dashboard (152 lines)
```

## Key Features

- **Peak Extraction**: Production adaptive algorithm (two-pass HH detection, +0.05mV bias correction, 485+ configs tuned)
- **Classification**: CatBoost primary (0.81 accuracy), RF/XGBoost available
- **Time-Series**: LSTM encoder-decoder (lookback=7, Huber loss)
- **Toxicity**: DDO-based stage1 vs stage2 calculation
- **Dashboard**: 5-step TXT-only pipeline (Upload → Peaks → LSTM → Classify → Toxicity)
- **Validation**: Tolerance-based peak matching, fuzzy name matching

## Production Pipeline

```
Upload TXT (UTF-16)
    ↓
extract_peaks_from_txt() [src/utils.py → src/peak_extractor.py]
    ├─ Two-pass HH detection
    ├─ Bias correction (+0.05mV non-HH, +0.04mV HH)
    └─ Output: DataFrame [No.peak, Tag, Doin, DOmin, DDO, Sample Name]
    ↓
Split processing:
├─ process_and_predict_lstm() [LSTM prediction on raw time-series]
├─ catboost_inference_from_csv() [CatBoost classification on peaks]
└─ calculate_toxicity() [DDO stage1 vs stage2 → toxicity %]
    ↓
Results: Classification, Toxicity %, Forecasts
```

### Pipeline Test Result (2026-03-11)

```
Sample: N4-10-5-01042024-Q=49.81mL_phút-3
Signal: 9,415 points | DO range: 277.24 – 284.75 mV
Peaks:  20 extracted (1 BOD10, 19 BOD5) | DDO: 4.49 – 5.84 mV
Classification: GGA (probability 78.4%)
Toxicity: 5.31%
Status: ALL 4 STEPS PASSED ✓
```

## Extraction Accuracy (2-pass adaptive, tuned 485+ configs)

| Dataset | Samples | Peaks | 0.2mV  | 0.3mV  |
|---------|---------|-------|--------|--------|
| Test    | 14      | 681   | 88.1%  | **93.0%** |
| GGA     | 134     | 1793  | 79.9%  | **85.3%** |
| Metal   | 348     | 5254  | 73.6%  | **80.1%** |
| HH      | 89      | 1252  | 73.7%  | **84.1%** |

## Environment Setup

```bash
# Recommended: conda vhl environment (has all dependencies)
conda activate vhl

# Key packages in vhl env:
# catboost==1.2.8, tensorflow==2.19.0, keras==3.10.0
# scipy, pandas, numpy, scikit-learn, plotly, streamlit, openpyxl
```

## Documentation

- [Project Overview & Requirements](./docs/project-overview-pdr.md)
- [Code Standards & Structure](./docs/code-standards.md)
- [System Architecture](./docs/system-architecture.md)
- [Codebase Summary](./docs/codebase-summary.md)
- [Project Roadmap](./docs/project-roadmap.md)

## Reports

- Vietnamese progress report: `plans/reports/BÁO CÁO SINH HỌC (11-03-2026).docx`
- DOin bias correction & ML analysis: `plans/reports/optimization-260224-0921-doin-bias-correction-ml-analysis.md`
- DOin accuracy ceiling audit: `plans/reports/evaluation-audit-260222-0956-doin-accuracy-ceiling.md`
