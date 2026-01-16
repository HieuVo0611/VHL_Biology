# VHL Biology Project

Dissolved oxygen (DO) analysis system using ML models to classify biological samples (GGA vs GGA-metal) and extract special points for BOD (Biochemical Oxygen Demand) calculation.

## Quick Start

1. **Install dependencies:**
```bash
pip install -r requirements.txt
```

2. **Run the Streamlit dashboard:**
```bash
streamlit run app.py
```

3. **Run classification model:**
```bash
python code/gga_classification_model.py
```

## Project Overview

**Core Purpose**: Analyze dissolved oxygen degradation patterns to classify samples and calculate BOD metrics
**Key Components**: Classification (RF/XGBoost), DO extraction (algorithm & ML), Time-series forecasting (LSTM/EMA)
**Data Pipeline**: UTF-16 TXT → CSV metadata → Classification → Special point extraction → BOD calculation

## Directory Structure

```
VHL_Biology/
├── code/                          # Core Python scripts
│   ├── gga_classification_model.py # RF/XGBoost classifier (70+ features)
│   ├── extract_DO_in.py           # Algorithm-based DO extremum extraction
│   ├── extract_special_points.py  # Fixed-interval point extraction
│   ├── ema_model.py               # EMA forecasting with RF regressor
│   ├── process_txt_data.py        # UTF-16 TXT → CSV conversion
│   ├── check_matching_name.py     # Fuzzy name matching (TXT/Excel)
│   └── train extract special points/  # ML-based extraction
│       ├── create_dataset.py
│       ├── train_xgboost.py
│       └── predict_and_extract.py
├── src/
│   ├── utils.py                   # Utilities (feature engineering, CatBoost, LSTM)
│   └── visualize_data.py          # Time-series visualization
├── tools/
│   ├── derive_metadata_from_txt.py # Signal processing peak detection
│   └── validate_metadata.py       # Tolerance-based validation
├── model/                          # Trained models
│   ├── LSTM Model/               # LSTM encoder-decoder variants
│   ├── RF Model/                 # Random Forest models
│   ├── catboost_model.cbm        # CatBoost classifier
│   └── label_encoder_classes.npy
├── notebooks/                      # Jupyter notebooks
│   ├── ARIMA_1_0_Bio_VHL.ipynb   # ARIMA(1,1,5) forecasting
│   ├── LSTM_Bio_VHL.ipynb        # LSTM lookback=7
│   ├── LR_BIO_VHL.ipynb          # Linear Regression 8-12 lags
│   └── SMA_EWMA_method.ipynb     # Moving average baselines
├── data/
│   ├── GGA/                      # GGA sample data
│   ├── GGA-metal/                # GGA-metal sample data
│   ├── BOD-Hieu/                 # BOD reference data
│   └── metadata-gga-*.csv        # Extracted metadata
├── docs/                          # Documentation
└── app.py                         # Streamlit interactive dashboard
```

## Key Features

- **Classification**: RF & XGBoost with 70-85 engineered features
- **DO Extraction**: Savitzky-Golay filter (window 21-51, polyorder 2-9)
- **Time-Series**: LSTM lookback 7 steps, EMA span 12
- **Dashboard**: Real-time prediction, classification, toxicity calculation
- **Validation**: Fuzzy name matching, tolerance-based metadata validation

## Data Processing Pipeline

```
TXT files (UTF-16) → process_txt_data.py → metadata-gga-txt.csv
                                                ↓
    Algorithm path: extract_DO_in.py / extract_special_points.py
    ML path: create_dataset.py → train_xgboost.py → predict_and_extract.py
                                                ↓
                        gga_classification_model.py (classification)
                                                ↓
                        app.py (Streamlit dashboard)
```

## Documentation

- [Project Overview & Requirements](./docs/project-overview-pdr.md)
- [Code Standards & Structure](./docs/code-standards.md)
- [System Architecture](./docs/system-architecture.md)
- [Codebase Summary](./docs/codebase-summary.md)
- [Project Roadmap](./docs/project-roadmap.md)
