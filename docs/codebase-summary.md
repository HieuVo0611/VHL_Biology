# VHL Biology - Codebase Summary

**Last Updated**: 2026-03-22
**Version**: 1.2.0
**Status**: Production-Ready (Full Pipeline Verified 2026-03-11)

## Project Overview

VHL Biology is a comprehensive ML system for analyzing dissolved oxygen (DO) degradation patterns in biological samples. The project implements classification (GGA vs GGA-metal), adaptive peak extraction for BOD calculation, and time-series forecasting. Full end-to-end pipeline verified on 2026-03-11.

## Directory Structure

```
VHL_Biology/
├── code/                              # Core analysis scripts
│   ├── gga_classification_model.py    # RF & XGBoost classification (70+ features)
│   ├── extract_DO_in.py               # DO extremum extraction (Savitzky-Golay filter)
│   ├── extract_special_points.py      # Fixed-interval special point extraction
│   ├── ema_model.py                   # EMA forecasting with RF regressor
│   ├── process_txt_data.py            # UTF-16 TXT → CSV metadata conversion
│   ├── check_matching_name.py         # Fuzzy name matching (TXT/Excel samples)
│   └── train extract special points/  # ML-based extraction pipeline
│       ├── create_dataset.py          # Dataset creation for XGBoost
│       ├── train_xgboost.py           # XGBoost model training
│       └── predict_and_extract.py     # Prediction and extraction
├── src/                               # Utility modules
│   ├── peak_extractor.py              # Production adaptive peak extraction (448 lines)
│   │                                  #  - Two-pass HH detection
│   │                                  #  - Bias correction (+0.05mV non-HH, +0.04mV HH)
│   │                                  #  - Tuned 485+ configurations, 93.0% @ 0.3mV test
│   ├── phase_detector.py              # Phase boundary detection (135 lines)
│   │                                  #  - Hybrid 3-track: RandomForest Metal/HH, constrained change-point GGA
│   │                                  #  - Output: phase1 / transition / phase2 tags
│   │                                  #  - Accuracy: Metal 98%, HH 98.6% (±1 boundary), GGA 84% (algorithm)
│   ├── phase_features.py              # Phase feature extraction (85 lines)
│   │                                  #  - 16 peak-derived features for Metal/HH RF models
│   ├── utils.py                       # Core utilities (549 lines):
│   │                                  #  - extract_peaks_from_txt() wrapper
│   │                                  #  - Feature engineering (81 features: 68 original + 13 robust)
│   │                                  #  - CatBoost inference
│   │                                  #  - LSTM prediction
│   │                                  #  - calculate_toxicity() [filters transition, prefers phase1/phase2]
│   ├── export_excel.py                # Excel report generator (Summary Dashboard v2.0)
│   │                                  #  - 2-sheet formatted workbook (Summary + Peaks)
│   │                                  #  - openpyxl-based with styled headers/cells
│   └── visualize_data.py              # Data visualization with peak marking
├── tools/                             # Data processing utilities
│   ├── derive_metadata_from_txt.py    # Peak detection via signal processing
│   │                                  #  (median filter + scipy find_peaks)
│   ├── validate_metadata.py           # Tolerance-based validation
│   ├── extract-phase-gt-from-excel.py # Extract phase GT from Excel color marking
│   │                                  #  (yellow=phase1, white=transition/phase2)
│   ├── train-phase-detector.py        # Train Metal + HH RandomForest models
│   ├── validate-phase-detector.py     # Validate phase detector on GT
│   ├── analyze_metal_errors.py        # Per-peak error analysis (4 datasets)
│   ├── test_metal_targeted.py         # 47 bias/param config sweep
│   ├── test_bias_finetune.py          # Bias fine-tuning (19 configs)
│   ├── test_ml_correction.py          # ML correction experiment (GBR/RF vs uniform bias)
│   ├── validate-classifier-accuracy.py # 518-file classification validation
│   ├── experiment-a-robust-features.py # Feature engineering experiments
│   ├── experiment-b-augmentation.py   # Noise injection + oversampling
│   ├── experiment-c-ensemble.py       # Multi-model ensemble
│   ├── experiment-d-aligned-training.py # Aligned training on algo-extracted peaks
│   ├── experiment-e-aligned-noise.py  # Combined best approach
│   ├── experiment-final-combine.py    # Final model training
│   ├── generate_comprehensive_report.py # Word report generation
│   └── generate-progress-report-260311.py # Vietnamese progress report (.docx)
├── model/                             # Trained models
│   ├── LSTM Model/                   # LSTM encoder-decoder models
│   │   └── 2024-2025 variants        # Multiple versions with hyperparameter tuning
│   ├── RF Model/                     # Random Forest classifiers
│   │   └── 03012025/                 # Latest random_forest.pkl
│   ├── catboost_model.cbm            # CatBoost classifier
│   ├── catboost_training_metadata.json # Training metadata (features, params, accuracy)
│   ├── phase_detector_metal.pkl      # RandomForest Metal phase detector (CV 93.2%)
│   ├── phase_detector_hh.pkl         # RandomForest HH phase detector (CV 94.1%)
│   └── label_encoder_classes.npy     # Class labels for encoding
├── notebooks/                        # Jupyter analysis notebooks
│   ├── ARIMA_1_0_Bio_VHL.ipynb       # ARIMA(1,1,5) time series forecasting
│   ├── LSTM_Bio_VHL.ipynb            # LSTM with lookback=7, Huber loss
│   ├── LR_BIO_VHL.ipynb              # Linear Regression (8-12 lag features)
│   └── SMA_EWMA_method.ipynb         # SMA/EWMA baselines (span=12)
├── data/                              # Sample and training data
│   ├── GGA/                          # GGA sample measurements (UTF-16 TXT)
│   ├── GGA-metal/                    # GGA-metal sample measurements
│   ├── BOD-Hieu/                     # BOD reference measurements
│   ├── phase-gt-gga.csv              # GGA ground truth (25 samples, 446 peaks)
│   ├── phase-gt-metal.csv            # Metal ground truth (100 samples, 1477 peaks)
│   ├── phase-gt-hh.csv               # HH ground truth (432 samples, 6055 peaks)
│   ├── metadata-gga-txt.csv          # Extracted metadata from TXT files
│   ├── metadata-gga-*.csv            # Various metadata versions
│   └── SPECIAL_POINTS_EXTRACTED.xlsx # Extracted special points results
├── docs/                              # Documentation
│   ├── project-overview-pdr.md       # Project requirements & overview
│   ├── code-standards.md             # Coding standards & conventions
│   ├── system-architecture.md        # System design & data flow
│   ├── codebase-summary.md           # This file
│   └── project-roadmap.md            # Development roadmap
├── app.py                            # Streamlit Summary Dashboard v2.0 (349 lines)
├── app_legacy.py                     # Legacy 5-step sequential dashboard (backup)
├── test.py                           # Standalone peak detection with BOD classification
├── peak_finder.py                    # OriginLab Pro integration (Quick Peaks gadget)
└── requirements.txt                  # Python dependencies
```

## Core Components

### 1. DO Peak Extraction (Production) (`/src/peak_extractor.py`)

**Purpose**: Extract DO extremum values (DOin, DOmin, DDO) from raw time-series signals

**Features**:
- Two-pass adaptive algorithm: non-HH extraction → DDO computation → conditional HH re-extraction
- Bias correction: +0.05mV non-HH, +0.04mV HH (fixes systematic 78% DOin under-estimation)
- Parameters: safety=5, hh_smooth=21, non_hh_smooth=19, hh_lookback=0.50, stab_mult=0.012
- Tuned over 485+ configurations

**Accuracy (at 0.3mV tolerance)**:
- Test: 93.0% (681 peaks)
- GGA: 85.3% (1793 peaks)
- Metal: 80.1% (5254 peaks)
- HH: 84.1% (1252 peaks)

**Output**:
```
DataFrame columns: [No.peak, Tag, Doin (mV), DOmin (mV), DDO (mV), Sample Name]
```

**Integration**: `src/utils.py` provides `extract_peaks_from_txt()` wrapper for TXT file input

### 2. Classification Pipeline (`/code/gga_classification_model.py`)

**Purpose**: Classify samples as GGA or GGA-metal based on extracted peak features

**Features**:
- CatBoost classifier (production primary — trained on algo-extracted peaks with noise augmentation + GGA oversampling)
- Random Forest classifier (81 features)
- XGBoost classifier (81 features)
- Ensemble voting mechanism
- Feature importance analysis
- Cross-validation (60/40 or 60/20/20 split)

**Input**: Extracted peaks DataFrame or engineered features (81)

**Key Metrics**:
- Training data: 518-file validation dataset
- Features: 81 engineered metrics (68 original + 13 robust)
- Output: Class labels with confidence scores
- Accuracy: 84.4% on 518-file validation (GGA=88.1%, Metal=82.7%)

**Usage**:
```bash
python code/gga_classification_model.py
# Outputs: Classification reports, feature importance plots
```

### 3. Legacy DO Extraction Methods

**Algorithm-Based** (`/code/extract_DO_in.py`):
- Savitzky-Golay filter (window 21-51, polyorder 2-9)
- Scipy `find_peaks` for extremum detection
- Fast: < 1 second/sample
- Reference: Superseded by production adaptive algorithm in peak_extractor.py

**ML-Based** (`/code/train extract special points/`):
- XGBoost trained on labeled extraction examples
- `create_dataset.py`: Generates training dataset
- `train_xgboost.py`: Trains model with hyperparameter tuning
- `predict_and_extract.py`: Production inference

### 4. Special Points Extraction (`/code/extract_special_points.py`)

**Purpose**: Extract DO values at specific time intervals for BOD calculation

**Strategies**:
- Fixed-interval extraction (0, 1, 3, 5, 7 days, etc.)
- ML-based prediction (XGBoost trained on patterns)
- Plateau mean calculation for stability analysis

**Output**: `special_points_perfect.csv`, `special_points_plateau_mean.csv`

### 5. Time-Series Forecasting

**LSTM Encoder-Decoder** (`/notebooks/LSTM_Bio_VHL.ipynb`, `app_legacy.py`):
- Lookback window: 7 timesteps
- Huber loss function
- Bidirectional encoding
- Multiple model versions (2024-2025)
- Inference via `utils.py` LSTM functions
- File: `model/LSTM Model/28_07_2025/enc-dec_lstm_model.h5`

**EMA with RF** (`/code/ema_model.py`):
- Exponential Moving Average (span=12)
- Random Forest regressor for trend
- Combines smoothing with trend detection

**ARIMA Baseline** (`/notebooks/ARIMA_1_0_Bio_VHL.ipynb`):
- ARIMA(1,1,5) configuration
- Comparative analysis
- Time-series decomposition

**Linear Regression Baseline** (`/notebooks/LR_BIO_VHL.ipynb`):
- 8-12 lag features
- Lag-based feature engineering
- Quick baseline for comparison

### 6. Feature Engineering (`/src/utils.py`)

**81 Engineered Features (68 original + 13 robust)**:
- Statistical: mean, std, min, max, median, quantiles
- Time-series: autocorrelation, entropy, detrending
- Domain-specific: DO degradation rate, half-life, plateau metrics
- Aggregate: slope, acceleration, variability measures
- Robust (13): outlier-resistant variants of key features

**Additional Utilities**:
- CatBoost model inference
- LSTM prediction interface
- Toxicity calculation (domain-specific metrics)
- Metadata extraction and normalization

### 7. Data Input Processing

**Text File Processing** (`/code/process_txt_data.py`):
- UTF-16 encoding detection & conversion
- Timestamp parsing (various formats)
- DO value extraction
- Metadata normalization
- Error handling for malformed data

**Tools**:
- `tools/derive_metadata_from_txt.py`: Signal processing-based peak detection
- `tools/validate_metadata.py`: Tolerance-based validation
- `tools/generate_comprehensive_report.py`: Word report generation
- `tools/analyze_metal_errors.py`: Per-peak DOin error analysis across 4 datasets
- `tools/test_metal_targeted.py`: 47 bias/param config sweep
- `tools/test_bias_finetune.py`: Bias fine-tuning (19 configs)
- `tools/test_ml_correction.py`: ML correction experiment (GBR/RF vs uniform bias)
- `tools/validate-classifier-accuracy.py`: 518-file classification validation
- `tools/experiment-a-robust-features.py`: Feature engineering experiments
- `tools/experiment-b-augmentation.py`: Noise injection + oversampling
- `tools/experiment-c-ensemble.py`: Multi-model ensemble
- `tools/experiment-d-aligned-training.py`: Aligned training on algo-extracted peaks
- `tools/experiment-e-aligned-noise.py`: Combined best approach
- `tools/experiment-final-combine.py`: Final model training
- `tools/generate-progress-report-260311.py`: Vietnamese progress report (.docx)

**Sample Matching** (`/code/check_matching_name.py`):
- Fuzzy string matching (fuzzywuzzy)
- Legacy: Cross-references TXT filenames with Excel sample names
- Note: Excel dependency removed from main pipeline

### 8. Streamlit Dashboard (`app.py`) — Summary Dashboard v2.0

**Overview**: 1-click auto-run pipeline replacing the former 5-step sequential workflow. Upload a TXT file, click Run, and all results are displayed on one page.

**Features**:
- Auto-run pipeline: upload → button → extract peaks → classify → toxicity (no manual steps)
- Summary cards: peak count, classification result + confidence, toxicity score, signal info (DO range, data points)
- Plotly interactive DO signal chart with overlaid peak markers
- Color-coded peaks table: BOD10 = yellow, BOD5 = blue
- Toxicity panel with Stage 1/2 breakdown + formula display
- Excel export via `src/export_excel.py`: 2 formatted sheets (Summary + Peaks, openpyxl)

**Key Components (Summary Dashboard v2.0)**:
```python
1. Upload .txt File (UTF-16)
2. Click "Run Analysis" → auto-execute full pipeline:
   a. extract_peaks_from_txt() [src/peak_extractor.py]
   b. catboost_inference_from_csv() [src/utils.py]
   c. calculate_toxicity() [src/utils.py]
3. Display: Summary cards, Plotly signal chart, color-coded peaks table, toxicity panel
4. Export: Excel report (src/export_excel.py) — 2 sheets: Summary + Peaks
```

**New Module: `src/export_excel.py`**:
- Generates formatted Excel workbook with openpyxl
- Sheet 1 (Summary): sample name, classification, toxicity, signal stats
- Sheet 2 (Peaks): full peaks table with BOD10/BOD5 color coding

**Legacy Backup**:
- `app_legacy.py`: original 5-step sequential dashboard preserved for reference

**Size**: `app.py` is 349 lines (was 152 lines in v1.0)

**Model Paths Configuration**:
- LSTM model: `model/LSTM Model/28_07_2025/enc-dec_lstm_model.h5`
- RF model: `model/RF Model/03012025/random_forest.pkl`
- CatBoost model: `model/catboost_model.cbm`
- Label encoder: `model/label_encoder_classes.npy`

### 9. Additional Tools

**Peak Analysis** (`test.py`):
- Standalone peak detection script
- BOD5 and BOD0 classification
- Direct peak finding without full pipeline

**OriginLab Integration** (`peak_finder.py`):
- Automation for OriginLab Pro Quick Peaks gadget
- Desktop application integration
- Large file (13KB) indicates complex automation logic

## Technology Stack

### Runtime
- Python 3.8+ (conda env `vhl` recommended)
- Streamlit (web framework)
- Jupyter (notebooks)

### Python Environment (conda `vhl`)
| Package | Version | Purpose |
|---------|---------|---------|
| catboost | 1.2.8 | Production classifier |
| tensorflow | 2.19.0 | LSTM models |
| keras | 3.10.0 | Deep learning API |
| scipy | Latest | Signal processing |
| scikit-learn | Latest | RF, preprocessing |
| XGBoost | Latest | XGBoost classifier |
| streamlit | Latest | Dashboard |
| plotly | Latest | Interactive plots |
| pandas | 1.x+ | Data manipulation |
| numpy | Latest | Numerical computing |
| openpyxl | Latest | Excel I/O |

### ML & Data Processing
| Library | Version | Purpose |
|---------|---------|---------|
| scikit-learn | Latest | RF, SVM, preprocessing |
| XGBoost | Latest | XGBoost classifier |
| CatBoost | 1.2.8 | CatBoost classifier (production) |
| TensorFlow | 2.19.0 | LSTM models |
| Keras | 3.10.0 | Deep learning API |
| statsmodels | Latest | ARIMA, time-series |
| pandas | 1.x+ | Data manipulation |
| numpy | Latest | Numerical computing |
| scipy | Latest | Signal processing (find_peaks) |
| fuzzywuzzy | Latest | Name matching |

### Visualization & I/O
- matplotlib, plotly (visualization)
- openpyxl (Excel reading/writing)
- chardet (encoding detection)

### Development Tools
- Git (version control)
- Python venv (.venv)

## Data Models

### Metadata Structure (CSV)
```
Fields: Timestamp, DO_value, Temperature, Conductivity, pH, ...
        [81 derived features (68 original + 13 robust)]
        [Sample_Name, Classification_Label]
```

### Special Points Output
```
Fields: Sample_ID, DO_0_days, DO_1_day, DO_3_days, DO_5_days, DO_7_days,
        Plateau_Mean, BOD_0, BOD_5, Classification, Toxicity_Score
```

### Classification Output
```
Fields: Sample_ID, GGA_Probability, GGA_Metal_Probability, Predicted_Class,
        Confidence_Score, Top_10_Features
```

## Key Algorithms & Methods

### Savitzky-Golay Filter Configuration
- Window size: 21-51 (depending on data resolution)
- Polyorder: 2-9 (balance between smoothing and peak preservation)
- Purpose: Remove noise while preserving extrema

### Train/Test Splits
- Primary: 60/40 (training/testing)
- Alternative: 60/20/20 (training/validation/testing)
- Cross-validation: 5-fold for model evaluation

### Feature Engineering Process
1. Time-series extraction (raw values)
2. Statistical aggregation (mean, std, quantiles)
3. Domain transformations (degradation rate, half-life)
4. Scaling/normalization (StandardScaler)
5. Feature selection (importance-based)

## Performance Characteristics

### Classification
- Accuracy: 84.4% on 518-file validation (GGA=88.1%, Metal=82.7%)
- Training time: < 1 hour (full dataset)
- Inference time: < 500ms/sample

### DO Extraction
- Algorithm method: < 1 second/sample
- ML method: < 200ms/sample
- Production adaptive: 80.1-93.0% at 0.3mV tolerance (depending on dataset)

### Full Pipeline Test (2026-03-11)
End-to-end pipeline verified with real data:
```
Input:  N4-10-5-01042024-Q=49.81mL_phút-3.txt (9,415 data points)
Step 1: Parse TXT → DO range 277.24 – 284.75 mV
Step 2: Extract Peaks → 20 peaks (1 BOD10, 19 BOD5), DDO 4.49 – 5.84 mV
Step 3: CatBoost Classification → GGA (probability 78.4%)
Step 4: Toxicity → 5.31% (Stage 1: BOD10, Stage 2: BOD5)
Result: ALL STEPS PASSED ✓
```
Environment: conda `vhl` (Python 3.x, CatBoost 1.2.8, TensorFlow 2.19.0)

### Forecasting
- LSTM: Best accuracy for non-linear patterns
- EMA: Fast but limited to linear trends
- ARIMA: Good for stationary series
- LR: Fast baseline

### Dashboard
- Response time: < 2 seconds (typical)
- Memory usage: < 2GB for full pipeline
- Batch processing: 100 samples in < 5 minutes

## Dependencies

**See**: `requirements.txt` for complete list

Key dependencies:
- scikit-learn, XGBoost, CatBoost
- TensorFlow (for LSTM)
- Streamlit (dashboard)
- pandas, numpy, scipy
- plotly, matplotlib (visualization)

## File Organization Notes

**Large Files**:
- `PeakAnalysis.opju` (30KB): OriginLab project file
- `temp.xlsx` (300KB): Temporary Excel data
- `peak_finder.py` (13KB): Complex automation script

**Data Directories**:
- `data/GGA/` & `data/GGA-metal/`: Raw UTF-16 TXT files (thousands)
- `data/BOD-Hieu/`: Reference measurements
- `model/`: Serialized trained models

**Generated Files**:
- `special_points_perfect.csv`: Extracted special points
- `special_points_plateau_mean.csv`: Plateau analysis
- `metadata-gga-txt.csv`: Extracted metadata

## Development Workflow

### Typical Development Cycle
1. Add new feature to `code/` directory
2. Test with sample data in `data/`
3. Update `app.py` / `src/export_excel.py` dashboard if needed
4. Run full validation pipeline
5. Update model if needed (retrain notebooks)
6. Commit changes to git

### Testing
- Manual testing via Streamlit dashboard
- Unit tests in test.py
- Cross-validation during model training
- Validation tool: `tools/validate_metadata.py`

### Model Management
- Store models in versioned directories: `model/[Type]/[Date]/`
- Keep label encoders for reproducibility
- Document hyperparameters used for training

## Integration Points

- **Input**: UTF-16 TXT files from laboratory instruments
- **Output**: CSV/Excel results, plots, classifications
- **Optional**: OriginLab Pro integration for automation
- **Optional**: Dashboard web interface (Streamlit)

## Known Limitations

1. **UTF-16 Dependency**: Requires specific TXT format from instruments
2. **Single-Machine**: No distributed training/inference
3. **Manual Retraining**: Models require periodic updates
4. **Python-Only**: No C++ backend for real-time performance
5. **Labeled Data**: Classification requires labeled training samples

## Maintenance Notes

- Monitor model performance metrics regularly
- Retrain models quarterly or when performance degrades
- Update feature engineering if new patterns emerge
- Validate data pipeline integrity
- Archive old experiments in reference directory

## Related Documentation

- [Project Overview & PDR](./project-overview-pdr.md)
- [Code Standards](./code-standards.md)
- [System Architecture](./system-architecture.md)
- [Project Roadmap](./project-roadmap.md)

## Glossary

- **DO**: Dissolved Oxygen concentration (mg/L)
- **BOD**: Biochemical Oxygen Demand (5-day standard)
- **GGA**: Reference control sample type
- **GGA-metal**: Sample type with metal compounds
- **LSTM**: Long Short-Term Memory neural network
- **EMA**: Exponential Moving Average
- **RF**: Random Forest
