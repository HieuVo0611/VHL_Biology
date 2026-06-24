# VHL Biology - System Architecture

**Last Updated**: 2026-03-22
**Version**: 1.2.0
**Project**: VHL Biology - DO Analysis & BOD Classification

## Architecture Overview

VHL Biology implements a modular ML pipeline for analyzing dissolved oxygen (DO) degradation patterns. The system uses CatBoost (primary) with RF/XGBoost for classification and LSTM encoder-decoder for forecasting. Full end-to-end pipeline verified 2026-03-11.

### Design Pattern: Layered Pipeline Architecture

```
Data Input Layer
       ↓
Feature Engineering Layer
       ↓
├─ Classification Layer
├─ DO Extraction Layer
├─ Special Points Layer
└─ Forecasting Layer
       ↓
Results & Dashboard Layer
```

## System Components

### 1. Data Input Layer (TXT-Only)

**Purpose**: Read raw instrument data from TXT files

**Components**:
- **TXT File Parser** (`/src/peak_extractor.py` + `/code/process_txt_data.py`)
  - Reads UTF-16 encoded files
  - Extracts timestamps and DO values
  - Handles encoding errors gracefully
  - Passes to peak extraction immediately

- **No Excel Dependency**
  - Removed Excel classification shortcut (was using expert ground truth)
  - All classification now from algorithmically extracted peaks
  - Legacy: check_matching_name.py still available but not in main pipeline

**Data Format**:
```
Input: UTF-16 TXT files with timestamp, DO_value columns
Output to Peak Extractor: Raw DO array + Time array
```

### 2. Feature Engineering Layer

**Purpose**: Extract 81 features for ML models

**Location**: `/src/utils.py`

**Feature Categories**:
1. **Statistical Features** (15-20 features)
   - mean, std, min, max, median
   - Quantiles: 25%, 75%
   - Range, IQR, skewness, kurtosis

2. **Time-Series Features** (20-25 features)
   - Autocorrelation at lags 1-5
   - Entropy, trend slope
   - Seasonality detection
   - Detrending components

3. **Domain-Specific Features** (20-30 features)
   - DO degradation rate
   - Half-life calculation
   - Plateau detection and mean
   - Rising/falling periods
   - Peak analysis

4. **Aggregate Features** (10-15 features)
   - Slope, acceleration
   - Variability measures
   - Normalized ranges

**Feature Pipeline**:
```
Raw Data
   ↓
Statistical Aggregation
   ↓
Time-Series Transformation
   ↓
Domain Calculations
   ↓
Scaling/Normalization (StandardScaler)
   ↓
81 Features Ready for ML
```

### 3. Classification Layer

**Purpose**: Classify samples as GGA or GGA-metal

**Location**: `/code/gga_classification_model.py`

**Architecture**:
```
81 Features (68 original + 13 robust features added 2026-03-22)
   ↓
CatBoost Classifier (Primary)
├─ iter=300, lr=0.05, depth=8
├─ Balanced class weights
├─ Trained on algo-extracted peaks (518 TXT files)
├─ + Gaussian noise augmentation (s=0.08, 3x)
└─ + GGA oversampling (45%)
   ↓
Final Classification: GGA or GGA-metal
   ↓
Confidence Score (probability)
```

**Key Parameters**:
- Production model: CatBoost (iter=300, lr=0.05, depth=8, balanced weights)
- Training data: 518 TXT files (algo-extracted peaks, not GT peaks)
- Augmentation: Gaussian noise s=0.08 (3x) + GGA oversampling 45%
- Accuracy: 84.4% on 518-file validation (GGA=88.1%, Metal=82.7%)
- Key architectural improvement: aligned to algo-extracted peaks (was trained on GT peaks)

**Output Schema**:
```json
{
  "sample_id": "GGA_001",
  "predicted_class": "GGA",
  "gga_probability": 0.92,
  "gga_metal_probability": 0.08,
  "confidence_score": 0.92,
  "top_features": [feature_1, feature_2, ...]
}
```

### 4. DO Extraction Layer (Production Adaptive)

**Purpose**: Extract DO extremum values (DOin, DOmin, DDO)

**Primary Method** (`/src/peak_extractor.py`):
```
Raw Time-Series Data
   ↓
Adaptive Two-Pass Algorithm:
Pass 1: Non-HH extraction
   ├─ Smoothing: non_hh_smooth=19
   ├─ Lookback: 0.75 * cycle_length
   └─ Extract peaks with non-HH thresholds
   ↓
Pass 2: DDO Computation & HH Detection
   ├─ Compute DDO = DOmin - DOin
   ├─ Check if HH sample (high noise floor)
   └─ If HH detected, proceed to Pass 3
   ↓
Pass 3: Conditional HH Re-extraction
   └─ If HH: Re-extract with HH params (hh_smooth=21, hh_lookback=0.50)
   ↓
Bias Correction
   ├─ Non-HH: +0.05mV to DOin, +0.04mV to DOmin
   └─ HH: +0.04mV to DOin, +0.04mV to DOmin
   ↓
Output: DataFrame [No.peak, Tag, Doin (mV), DOmin (mV), DDO (mV), Sample Name]
```

**Performance**:
- Accuracy @ 0.3mV: Test 93.0%, GGA 85.3%, Metal 80.1%, HH 84.1%
- Speed: < 1 second/sample
- Tuned over 485+ configurations
- Addresses 78% systematic DOin under-estimation

**Legacy Methods**:

**A. Algorithm-Based** (`/code/extract_DO_in.py`):
- Savitzky-Golay filter (window 21-51, polyorder 2-9)
- scipy.signal.find_peaks()
- Fast but less accurate

**B. ML-Based** (`/code/train extract special points/`):
- XGBoost trained on labeled examples
- Higher accuracy but requires training data

### 5. Phase Boundary Detection Layer

**Purpose**: Classify peaks as phase1 (stable), transition (rising/falling), or phase2 (new stable)

**Location**: `/src/phase_detector.py` + `/src/phase_features.py`

**Architecture**:
```
Extracted Peaks DataFrame
   ↓
Compute Peak Features (16 derived features)
   ├─ Amplitude ratio, duration, position metrics
   └─ Output: feature vector per peak
   ↓
Hybrid 3-Track Detection:
   ├─ Track 1: HH Detection (DDO P90 > 12mV)
   │  └─ RandomForest HH classifier (CV 94.1%, 6055 training peaks)
   │     └─ If HH: phase1/phase2 output (98.6% ±1 accuracy)
   │
   ├─ Track 2: Metal Classification (sample class)
   │  └─ RandomForest Metal classifier (CV 93.2%, 1477 training peaks)
   │     └─ If Metal: phase1/phase2 output (98% ±1 accuracy)
   │
   └─ Track 3: GGA (Constrained Change-Point)
      └─ Algorithm: find best boundary in [5,8] range
         └─ Output: phase1/phase2 (84% ±1 accuracy)
   ↓
Output: phase1 / transition / phase2 tags per peak
```

**Ground Truth Data**:
- GGA: 25 samples, 446 peaks (extracted from Excel yellow/white marking)
- Metal: 100 samples, 1477 peaks (Excel color GT)
- HH: 432 samples, 6055 peaks (Excel color GT)

**Key Features** (16 total):
- Amplitude metrics (DOin, DOmin, DDO, relative position)
- Duration and spacing ratios
- BOD10/BOD5 indicators
- Cumulative DDO ratios

### 6. Special Points Extraction Layer

**Purpose**: Extract DO values at specific time intervals for BOD calculation

**Location**: `/code/extract_special_points.py`

**Extraction Strategy**:
```
Time-Series Data
   ↓
Identify Target Time Points: 0, 1, 3, 5, 7 days (configurable)
   ↓
┌─ Algorithm-Based: Interpolation/nearest timestamp
├─ ML-Based: XGBoost prediction at time points
└─ Plateau-Based: Extract plateau mean for each interval
   ↓
Output: DO values at each interval
```

**Output Files**:
- `special_points_perfect.csv`: Exact interval extractions
- `special_points_plateau_mean.csv`: Plateau mean values

### 7. Forecasting Layer

**Purpose**: Predict future DO values using time-series models

**Location**: `/notebooks/`, `/code/ema_model.py`, `/src/utils.py`

**Models**:

**A. LSTM Encoder-Decoder** (Best for Non-Linear Patterns)
```
Historical Time-Series (7 timesteps)
   ↓
LSTM Encoder
   ↓
Context Vector
   ↓
LSTM Decoder
   ↓
Predicted Future Values
```
- Lookback: 7 timesteps
- Loss: Huber (robust to outliers)
- Architecture: Bidirectional encoder
- File: `model/LSTM Model/28_07_2025/enc-dec_lstm_model.h5`

**B. EMA with RF** (Balanced Speed & Accuracy)
```
Time-Series Data
   ↓
Exponential Moving Average (span=12)
   ↓
RF Regressor (learns trend correction)
   ↓
Combined Prediction
```
- Fast inference
- Handles trends well
- File: `/code/ema_model.py`

**C. ARIMA(1,1,5)** (Stationary Series Baseline)
```
Time-Series Decomposition
   ↓
ARIMA(1,1,5) Fitting
   ↓
Forecast
```
- Notebook: `ARIMA_1_0_Bio_VHL.ipynb`

**D. Linear Regression** (Quick Baseline)
```
Lag Features (8-12 lags)
   ↓
Linear Regression
   ↓
Prediction
```
- Notebook: `LR_BIO_VHL.ipynb`

### 8. Results & Dashboard Layer (Wizard Dashboard v2.2.0)

**Purpose**: 6-step guided wizard — one step per screen, back/forward navigation, per-step elapsed time, cached renders.

**Location**: `/app.py` (Streamlit, 725 lines) | `/src/export_excel.py` (Excel generator)

**Architecture**:
```
Step 0 — Upload
   └─ _parse_signal(bytes) [@st.cache_data] → DO array + signal stats
      Back-nav: shows existing file (no re-upload); new upload resets pipeline
   ↓
Step 1 — Peak Extraction
   └─ extract_peaks_from_txt() [src/peak_extractor.py]
      _build_chart_fig() [@st.cache_data] → Plotly figure with red ✕ markers
   ↓
Step 2 — Classification
   └─ catboost_inference_from_csv() [src/utils.py]
      → GGA/GGA-metal + confidence %
   ↓
Step 3 — Phase Detection
   └─ update_phase_tags() [src/phase_detector.py]
      → phase1 / transition / phase2 per peak
   ↓
Step 4 — Toxicity
   └─ calculate_toxicity() [src/utils.py]
      → Toxicity % (phase1 vs phase2, transition skipped)
   ↓
Step 5 — Summary
   ├─ 4 metric cards + processing time table
   └─ Excel Export [src/export_excel.py]: Sheet 1 Summary + Sheet 2 Peaks
```

**Key Implementation Details**:
- `@st.cache_data` on `_parse_signal` and `_build_chart_fig` — avoids re-work on every Streamlit rerun
- Unique button keys `btn_nxt_{back}_{nxt}` / `btn_back_{back}_{nxt}` — prevents Streamlit confusing same-label buttons
- `_flow(nodes)` renders colored HTML flowchart diagrams (blue input → green process → yellow decision → purple output)
- Session state guards (`if session_state.X is None`) ensure each step's computation runs exactly once per file

## Data Flow Diagrams

### End-to-End Processing Flow (TXT-Only, Wizard Dashboard v2.2.0)

```
User Input: TXT File (UTF-16)
   ↓
Step 1: Data Input Layer
└─ Parse UTF-16 TXT → Extract timestamps, DO values
   ↓
Step 2: DO Extraction Layer (Production Adaptive)
└─ peak_extractor.py
   ├─ Two-pass HH detection
   ├─ Bias correction (+0.05mV non-HH)
   └─ Output: peaks DataFrame [No.peak, Tag, Doin, DOmin, DDO, Sample Name]
   ↓
Step 3: LSTM Prediction (Independent)
├─ Raw time-series → process_and_predict_lstm()
└─ Output: DO forecast
   ↓
Step 4: Classification Pipeline (From Peaks)
├─ peaks DataFrame → Feature engineering (81 features)
├─ CatBoost inference (primary)
└─ Output: GGA/GGA-metal classification + confidence
   ↓
Step 5: Phase Boundary Detection
├─ peaks DataFrame → compute_peak_features() (16 features)
├─ Hybrid 3-track: RandomForest Metal/HH, constrained change-point GGA
└─ Output: phase1 / transition / phase2 tags per peak
   ↓
Step 6: Toxicity Calculation
├─ Filtered peaks (transition excluded)
└─ Output: Toxicity score (Phase 1 vs Phase 2)
   ↓
Results Display (Wizard Dashboard v2.2.0)
├─ Summary cards (peak count, classification, toxicity, signal info)
├─ Plotly DO signal chart with peak markers
├─ Color-coded peaks table (phase1=yellow, transition=white, phase2=blue)
├─ Toxicity panel (Phase 1/2 detail + formula)
└─ Excel export (src/export_excel.py — 2 sheets: Summary + Peaks with phase tags)
```

### Classification Pipeline Detail (From Extracted Peaks)

```
Extracted Peaks DataFrame
   ├─ [No.peak, Tag, Doin (mV), DOmin (mV), DDO (mV), Sample Name]
   ↓
Feature Engineering (81 features from peaks)
   ├─ 68 original features: mean, std, min, max of Doin, DOmin, DDO, degradation rate, half-life, plateau metrics
   └─ 13 robust features added 2026-03-22
   ↓
CatBoost Classifier (Primary)
├─ iter=300, lr=0.05, depth=8
├─ Balanced class weights
├─ Trained on algo-extracted peaks (not GT peaks) — key architectural improvement
├─ Gaussian noise augmentation (s=0.08, 3x) + GGA oversampling (45%)
└─ Accuracy: 84.4% on 518-file validation (GGA=88.1%, Metal=82.7%)
   ↓
Final Prediction
(GGA or GGA-metal)
   ↓
Confidence Score
```

**Key Change**: Classification now derives from algorithmically extracted peaks (not Excel metadata)

### DO Extraction Pipeline Detail

```
Time-Series Data
   │
   ├─ Algorithm Path:
   │  ├─ Savitzky-Golay Filter (window 21-51, polyorder 2-9)
   │  ├─ Smooth Signal
   │  ├─ scipy.signal.find_peaks()
   │  └─ Extract Extrema → DO_in, DO_out
   │
   └─ ML Path:
      ├─ Train: create_dataset.py
      ├─ Model: train_xgboost.py
      ├─ Predict: predict_and_extract.py
      └─ Output: DO_in, DO_out predictions
```

## Technology Stack

### Core Runtime
| Component | Technology | Version |
|-----------|-----------|---------|
| Language | Python | 3.8+ (conda env `vhl`) |
| Web Framework | Streamlit | Latest |
| Notebooks | Jupyter | Latest |

### ML & Data Processing Libraries
| Library | Purpose | Version |
|---------|---------|---------|
| scikit-learn | RF, preprocessing | Latest |
| XGBoost | XGBoost classifier | Latest |
| CatBoost | CatBoost model | 1.2.8 |
| TensorFlow/Keras | LSTM models | 2.19.0 / 3.10.0 |
| statsmodels | ARIMA | Latest |
| pandas | Data manipulation | 1.x+ |
| numpy | Numerical computing | Latest |
| scipy | Signal processing | Latest |
| fuzzywuzzy | Name matching | Latest |

### Visualization & I/O
| Library | Purpose |
|---------|---------|
| matplotlib | Static plots |
| plotly | Interactive plots |
| openpyxl | Excel I/O |
| chardet | Encoding detection |

## Model Storage & Versioning

### Directory Structure
```
model/
├── LSTM Model/
│   └── 28_07_2025/
│       └── enc-dec_lstm_model.h5
├── RF Model/
│   └── 03012025/
│       ├── random_forest.pkl
│       ├── hyperparameters.json
│       └── training_log.txt
├── catboost_model.cbm
└── label_encoder_classes.npy
```

### Model Metadata
Each model stored with:
- **Hyperparameters**: JSON file with all parameters
- **Training Log**: Date, accuracy, F1-score, cross-val scores
- **Feature Schema**: List of 81 features used
- **Scaler Parameters**: Mean, std for StandardScaler

### Loading Models
```python
# Example: Load RF model
import joblib
import json

model = joblib.load('model/RF Model/03012025/random_forest.pkl')
with open('model/RF Model/03012025/hyperparameters.json') as f:
    params = json.load(f)
```

## Configuration Management

### Environment Variables
```python
MODEL_PATH = os.getenv('MODEL_PATH', 'model/')
DATA_PATH = os.getenv('DATA_PATH', 'data/')
SAVITZKY_GOLAY_WINDOW = int(os.getenv('SG_WINDOW', '31'))
SAVITZKY_GOLAY_POLYORDER = int(os.getenv('SG_POLYORDER', '3'))
```

### Hardcoded Paths (Root Level)
- LSTM model: `model/LSTM Model/28_07_2025/enc-dec_lstm_model.h5`
- RF model: `model/RF Model/03012025/random_forest.pkl`
- CatBoost: `model/catboost_model.cbm`

## Error Handling & Recovery

### Data Validation
```
Input Data
   ↓
Validate UTF-16 Encoding
   ↓ (fail) → Fallback to UTF-8 → Retry
   ↓ (success)
Validate Column Presence
   ↓ (fail) → Log warning → Skip sample
   ↓ (success)
Validate Value Ranges
   ├─ DO_value: 0-15 mg/L
   ├─ Temperature: 0-50°C
   └─ Timestamp: valid format
   ↓ (fail) → Handle gracefully
   ↓ (success)
Process Sample
```

### Error Recovery Strategies
1. **Missing Data**: Forward/backward fill or interpolation
2. **Encoding Errors**: Fallback encodings (UTF-8, Latin-1)
3. **Model Inference Failure**: Use alternative model or baseline
4. **File Read Error**: Log and skip, continue with next file

## Performance Characteristics

### Processing Speed
| Component | Time | Notes |
|-----------|------|-------|
| Feature Engineering | < 1 sec/sample | For 81 features |
| Classification | < 500 ms/sample | CatBoost primary |
| DO Extraction (Algo) | < 1 sec/sample | Savitzky-Golay |
| DO Extraction (ML) | < 200 ms/sample | XGBoost inference |
| LSTM Prediction | < 200 ms/sample | Forward pass |
| Dashboard Response | < 2 sec | Typical query |
| Batch Processing | < 5 min/100 samples | Full pipeline |

### Memory Usage
- Feature Engineering: ~100 MB (1000 samples)
- Model Loading: ~500 MB (all models)
- Dashboard: < 2 GB (full pipeline)
- Batch Processing: Scales linearly with sample count

### Accuracy Metrics
| Component | Metric | Target |
|-----------|--------|--------|
| Classification | Accuracy | 84.4% (518-file) |
| DO Extraction (ML) | Accuracy vs Manual | > 95% |
| Forecasting (LSTM) | MAE | < 2% DO deviation |
| Feature Matching | Fuzzy Match Success | > 95% |

## Scalability Considerations

### Current Limitations
- **Single-Machine**: No distributed training/inference
- **Batch Processing**: Sequential sample processing
- **Model Retraining**: Manual process via notebooks
- **Data Size**: Limited by available RAM

### Scaling Strategies (Future)
1. **Distributed Training**: Spark/Dask for large datasets
2. **Model Serving**: TensorFlow Serving for inference
3. **Database Integration**: Store results in database
4. **API Layer**: REST API for external integrations
5. **Caching**: Redis for feature caching
6. **Parallel Processing**: multiprocessing for batch jobs

## Security Considerations

### Data Security
- **Input Validation**: Check file types, sizes, content
- **Error Messages**: Sanitize to avoid information leakage
- **Logging**: Never log sensitive values (passwords, credentials)

### Model Security
- **Model Serialization**: Use joblib/pickle safely
- **Version Control**: Don't commit model files to git
- **Access Control**: Restrict model file permissions

### File Handling
- **Path Traversal**: Use `os.path.join()`, not string concatenation
- **Encoding**: Detect encoding, don't assume
- **Error Handling**: Graceful failure on malformed files

## Deployment Architecture

### Development Environment
```
Developer Machine
├── conda env: vhl (CatBoost 1.2.8, TensorFlow 2.19.0, Keras 3.10.0)
├── code/ (source scripts)
├── src/ (production modules)
├── notebooks/ (experimentation)
├── data/ (sample data)
└── model/ (trained models)

Running: conda activate vhl && streamlit run app.py
```

### Pipeline Verification (2026-03-11)

Full end-to-end pipeline tested:
```
Input:  TXT file (9,415 data points, UTF-16)
Step 1: Parse TXT → 277.24 – 284.75 mV DO range
Step 2: Adaptive Peak Extraction → 20 peaks (1 BOD10, 19 BOD5)
Step 3: CatBoost Classification → GGA (78.4% probability)
Step 4: Toxicity Calculation → 5.31%
Result: ALL 4 STEPS PASSED ✓
Environment: conda vhl (CatBoost 1.2.8, TensorFlow 2.19.0)
```

### Production Considerations
1. **Environment Variables**: Use .env for configuration
2. **Model Versioning**: Store multiple model versions
3. **Logging**: Comprehensive logging for debugging
4. **Monitoring**: Track model performance metrics
5. **Documentation**: Keep docs synchronized with code

## Extension Points

### Adding New Models
1. Train in notebook or standalone script
2. Save to versioned directory: `model/[Type]/[Date]/`
3. Update app.py to load new model
4. Update utils.py if new inference interface needed

### Adding New Features
1. Implement in utils.py `extract_features()`
2. Update feature count documentation
3. Retrain classification models
4. Test with validation set

### Adding New Data Sources
1. Create parser in tools/ or code/
2. Output normalized DataFrame
3. Integrate into pipeline
4. Update validation logic

## Monitoring & Observability

### Metrics to Track
- Classification accuracy on validation set
- Forecast MAE/RMSE on test set
- Processing time per sample
- File parsing success rate
- Model inference latency

### Logging Points
```python
logger.info("Processing %d samples", len(data))
logger.warning("Feature %s has %d missing values", name, count)
logger.error("Model prediction failed: %s", error)
```

## Related Documentation

- [Project Overview & PDR](./project-overview-pdr.md)
- [Code Standards](./code-standards.md)
- [Codebase Summary](./codebase-summary.md)
- [Project Roadmap](./project-roadmap.md)

## Unresolved Questions

1. **Real-Time Processing**: How to integrate with live instrument streams?
2. **Distributed Training**: Should we implement Spark-based distributed training?
3. **Model Serving**: Should we use TensorFlow Serving or similar?
4. **Database Backend**: Should we add database for result storage?
5. **API Gateway**: Should we build REST API for external systems?
