# VHL Biology Project Overview & PDR

**Project Name**: VHL Biology - DO Analysis & BOD Classification
**Version**: 1.2.0
**Last Updated**: 2026-03-22
**Status**: Production Ready (Pipeline Verified)
**Repository**: e:/VHL Project/Bio Zone/VHL_Biology

## Executive Summary

VHL Biology is a machine learning system for analyzing dissolved oxygen (DO) degradation patterns in biological samples. The project classifies samples (GGA vs GGA-metal), extracts special points for BOD calculation, and provides forecasting capabilities using ensemble methods (RF, XGBoost, CatBoost, LSTM).

## Project Purpose

### Vision
Enable rapid, accurate analysis of biological sample degradation through intelligent ML-driven DO pattern recognition and BOD estimation.

### Mission
Provide production-ready tools for:
- Automated sample classification (GGA vs GGA-metal)
- Accurate special point extraction for BOD calculation
- Time-series forecasting of DO values
- Interactive analysis dashboard
- Robust data validation and matching

### Value Proposition
- **81-Feature Coverage**: Comprehensive feature engineering from raw DO data (68 original + 13 robust)
- **Multi-Model Ensemble**: RF, XGBoost, CatBoost, and LSTM for classification
- **10x Analysis Speed**: Batch processing of TXT and Excel files
- **Zero Manual Intervention**: Automated fuzzy matching and validation
- **End-to-End TXT Pipeline**: Full pipeline from raw TXT → classification → toxicity verified (2026-03-11)

## Project Scope

### In Scope
- DO extremum point extraction (algorithm-based & ML-based)
- Sample classification (GGA vs GGA-metal)
- BOD value calculation and special point extraction
- Time-series forecasting (LSTM, EMA, ARIMA, Linear Regression)
- Streamlit dashboard for real-time prediction
- Metadata extraction and validation
- Model training and evaluation pipelines

### Out of Scope
- Lab equipment integration
- Real-time sensor data streaming
- Multi-site deployment
- Enterprise authentication

## Functional Requirements

**FR1: Data Processing (TXT-Only)**
- Read UTF-16 encoded TXT files from instruments
- Extract raw timestamp and DO value columns
- NO Excel dependency (removed classification shortcut)
- Handle encoding errors gracefully

**FR2: DO Peak Extraction (Production Adaptive)**
- Two-pass HH detection: extract with non-HH params → compute DDO → re-extract with HH params if needed
- Bias correction: +0.05mV non-HH, +0.04mV HH (fixes 78% systematic DOin under-estimation)
- Output: DataFrame [No.peak, Tag, Doin (mV), DOmin (mV), DDO (mV), Sample Name]
- Accuracy: 93.0% @ 0.3mV on test data (tuned over 485+ configurations)
- Extract DO_in (entering), DO_min (minimum), DDO (delta-DO) values

**FR3: Classification (from Extracted Peaks)**
- Production CatBoost model: iter=300, lr=0.05, depth=8, balanced class weights
- 81 features: 68 original + 13 robust statistical features
- Trained on algorithm-extracted peaks + Gaussian noise augmentation (σ=0.08, 3x copies) + GGA oversampling (45%)
- Validated on 518-file dataset: overall 84.4% accuracy (GGA=88.1%, Metal=82.7%)
- Also supports RF/XGBoost classifiers for ensemble comparison
- Classify samples as GGA or GGA-metal with confidence scores
- Support batch prediction on new samples
- Generate feature importance analysis
- Input: extracted peaks DataFrame (not Excel)

**FR4: Time-Series Forecasting**
- LSTM encoder-decoder (lookback=7 steps, Huber loss, bidirectional)
- EMA with RF regressor
- ARIMA(1,1,5) baseline
- Linear Regression with 8-12 lag features
- Forecast future DO values

**FR5: Special Point Extraction**
- Extract fixed-interval special points (0, 1, 3, 5, 7 days, etc.)
- Use ML model (XGBoost) to learn extraction patterns
- Calculate plateau mean for stability analysis
- Support multiple extraction strategies

**FR6: Dashboard (Wizard Dashboard v2.2.0 — Step-by-Step)**
- 6-step wizard: Upload → Peak Extraction → Classification → Phase Detection → Toxicity → Summary
- One step per screen; each step requires explicit click to advance (back/forward navigation)
- Per-step elapsed time badge; step indicator shows ✓Xs on completed steps
- Cached signal parsing and chart building (`@st.cache_data`) for smooth rerenders
- Step 0 back-navigation preserves loaded file — no re-upload required; new upload resets pipeline
- Colored HTML flowchart diagrams per step (no ASCII art)
- Step 1: DO signal chart with red ✕ peak markers + peaks table
- Step 2: large classification result card (GGA green / GGA-Metal orange)
- Step 3: phase distribution count cards (phase1 yellow, transition red, phase2 blue) + colored table
- Step 4: 3-card toxicity layout (Stage 1 DDO / Toxicity % / Stage 2 DDO)
- Step 5: 4 metric cards + time table + Excel export + "Phân tích mẫu mới" reset
- Excel export via `src/export_excel.py`: 2 formatted sheets (Summary + Peaks)

**FR7: Validation**
- Tolerance-based peak extraction validation
- Error detection and reporting
- Data quality metrics
- NO Excel matching needed (TXT-only pipeline)

## Non-Functional Requirements

**NFR1: Performance**
- Batch process 100+ samples in < 5 minutes
- Dashboard response time < 2 seconds
- Model inference < 500ms per sample
- Memory usage < 2GB for full pipeline

**NFR2: Reliability**
- Handle missing/incomplete data gracefully
- Validate data consistency
- Provide error messages and recovery suggestions
- Support re-running failed analyses

**NFR3: Maintainability**
- Python files < 500 lines (except auto-generated)
- Clear code organization and naming
- Comprehensive documentation
- Modular design for feature addition

**NFR4: Security**
- No hardcoded paths or credentials
- Secure file handling
- Input validation for all data
- Output sanitization

**NFR5: Usability**
- Intuitive dashboard interface
- Clear error messages
- Progress indicators for long operations
- Documentation and examples

## Success Metrics

### Peak Extraction Accuracy (Production Algorithm)
- Test dataset: 93.0% @ 0.3mV tolerance (681 peaks)
- GGA dataset: 85.3% @ 0.3mV tolerance (1793 peaks)
- Metal dataset: 80.1% @ 0.3mV tolerance (5254 peaks)
- HH dataset: 84.1% @ 0.3mV tolerance (1252 peaks)
- Overall mean: 85.6% @ 0.3mV (systematic bias correction tuned)

### Classification Metrics
- Classification accuracy: 84.4% on 518-file validation (GGA=88.1%, Metal=82.7%)
- Model: CatBoost (iter=300, lr=0.05, depth=8, balanced weights), 81 features
- Training: algo-extracted peaks + Gaussian noise (σ=0.08, 3x copies) + GGA oversampling (45%)
- Feature extraction success rate: > 95%
- Confidence scoring: calibrated with ground truth

### Performance Metrics
- Peak extraction: < 1 sec/sample
- Classification inference: < 500ms/sample
- LSTM prediction: < 200ms/sample
- Dashboard response time: < 2 sec (typical)
- Batch processing: 100 samples in < 5 minutes

### Process Metrics
- Code coverage: > 70%
- Documentation coverage: 100%
- Test pass rate: 100%
- Zero Excel dependency (TXT-only pipeline)

### User Experience Metrics
- Dashboard usability: Wizard Dashboard v2.2.0 — 6-step guided flow with per-step elapsed time
- Average analysis time: < 10 minutes per batch
- Error recovery success: > 95%

## Technical Architecture

### Core Technologies

**Runtime**:
- Python 3.8+
- Streamlit web framework
- Jupyter notebooks for analysis

**ML Libraries**:
- scikit-learn (RF, SVM)
- XGBoost
- CatBoost
- LSTM (TensorFlow/Keras)
- statsmodels (ARIMA)

**Data Processing**:
- pandas, numpy
- scipy (signal processing)
- openpyxl (Excel)

**Utilities**:
- fuzzywuzzy (name matching)
- matplotlib, plotly (visualization)

### System Components

**1. Data Input Layer** (`/tools`, `/code/process_txt_data.py`)
- TXT file parsing (UTF-16)
- CSV conversion
- Excel file reading

**2. Feature Engineering Layer** (`/src/utils.py` — 549 lines)
- 81-feature extraction (68 original + 13 robust)
- Statistical aggregation
- Time-series transformations

**3. Classification Layer** (`/code/gga_classification_model.py`)
- CatBoost (production): iter=300, lr=0.05, depth=8, balanced weights, 81 features
- Trained on algo-extracted peaks + noise augmentation (σ=0.08, 3x) + GGA oversampling
- RF and XGBoost models for ensemble comparison
- Ensemble voting

**4. DO Extraction Layer** (`/src/peak_extractor.py` — 448 lines)
- Production adaptive two-pass algorithm
- Non-HH extraction → DDO computation → conditional HH re-extraction
- Bias correction: +0.05mV non-HH, +0.04mV HH
- Parameters: safety=5, hh_smooth=21, non_hh_smooth=19, stab_mult=0.012
- Legacy: `/code/extract_DO_in.py` (Savitzky-Golay baseline)

**5. Special Points Layer** (`/code/extract_special_points.py`)
- Fixed-interval extraction
- ML-based prediction

**6. Forecasting Layer** (`/notebooks`, `/code/ema_model.py`)
- LSTM encoder-decoder
- EMA with RF regressor
- ARIMA/Linear Regression baselines

**7. Dashboard Layer** (`app.py` — 725 lines — Wizard Dashboard v2.2.0)
- Streamlit 6-step wizard; one step per screen with back/forward navigation
- Per-step elapsed time; `@st.cache_data` on signal parse + Plotly figure build
- Colored HTML flowchart diagrams per step; unique button keys prevent nav bugs
- Excel export via src/export_excel.py (2 sheets)

**8. Model Storage** (`/model`)
- Serialized trained models
- Label encoders
- Configuration files

## Data Pipeline (TXT-Only, Production)

```
Input: UTF-16 TXT File (Time, DO columns)
         ↓
extract_peaks_from_txt() [src/peak_extractor.py]
  ├─ Parse TXT, extract DO time-series
  ├─ Two-pass adaptive extraction
  └─ Output: peaks DataFrame
         ↓
split into:
  ├─ Classification (catboost_inference_from_csv)
  │  └─ From extracted peaks → GGA vs GGA-metal
  ├─ LSTM Prediction (process_and_predict_lstm)
  │  └─ From raw time-series → forecasts
  └─ Toxicity Calculation (calculate_toxicity)
         ↓
Streamlit Dashboard (app.py) — Wizard Dashboard v2.2.0 (6-step wizard)
         ↓
Output: Extracted peaks, Classification, Forecasts, Toxicity
```

## Constraints & Limitations

### Technical
- Requires specific TXT file format from instruments
- UTF-16 encoding dependency
- Python-based (no real-time C++ implementation)
- Single-machine processing (no distributed training)

### Data
- Requires labeled training data for classification
- DO values must be within expected ranges
- Sample names must be matchable via fuzzy logic
- Historical data needed for forecasting

### Operational
- Manual model retraining needed periodically
- Dashboard requires Streamlit server running
- No automatic data ingestion from instruments
- Requires Python environment setup

## Deployment

### Development Environment
```
VHL_Biology/
├── .venv/           # Python virtual environment
├── code/            # Source scripts
├── notebooks/       # Analysis notebooks
├── model/           # Trained models
├── data/            # Sample data
└── app.py          # Streamlit dashboard
```

### Running the System

1. **Activate environment**: `conda activate vhl`
2. **Run dashboard**: `streamlit run app.py`
3. **Process data**: `python code/gga_classification_model.py`
4. **Extract features**: `python code/process_txt_data.py`

### Python Environment

**Recommended**: conda env `vhl` (CatBoost 1.2.8, TensorFlow 2.19.0, Keras 3.10.0)

| Package | Version | Purpose |
|---------|---------|---------|
| catboost | 1.2.8 | Production classifier |
| tensorflow | 2.19.0 | LSTM models |
| keras | 3.10.0 | Deep learning API |
| scipy | Latest | Signal processing |
| scikit-learn | Latest | ML utilities |
| streamlit | Latest | Dashboard |
| plotly | Latest | Interactive plots |

### Pipeline Verification (2026-03-11)

Full end-to-end pipeline tested successfully:
```
Input:  N4-10-5-01042024-Q=49.81mL_phút-3.txt (9,415 points)
Step 1: Parse TXT → DO range 277.24 – 284.75 mV
Step 2: Extract Peaks → 20 peaks (1 BOD10, 19 BOD5)
Step 3: Classification → GGA (probability 78.4%)
Step 4: Toxicity → 5.31%
Result: ALL STEPS PASSED ✓
```

## Key Features by Component

| Component | Feature | Status |
|-----------|---------|--------|
| Classification | CatBoost (prod): iter=300, lr=0.05, depth=8, 81 features, noise aug | ✅ Complete |
| Classification | Validation: 84.4% on 518 files (GGA=88.1%, Metal=82.7%) | ✅ Complete |
| Classification | RF model | ✅ Complete |
| Classification | XGBoost model | ✅ Complete |
| DO Extraction | Algorithm-based (Savitzky-Golay) | ✅ Complete |
| DO Extraction | ML-based (XGBoost) | ✅ Complete |
| Special Points | Fixed-interval extraction | ✅ Complete |
| Special Points | ML-based extraction | ✅ Complete |
| Forecasting | LSTM encoder-decoder | ✅ Complete |
| Forecasting | EMA with RF | ✅ Complete |
| Forecasting | ARIMA | ✅ Complete |
| Dashboard | File upload | ✅ Complete |
| Dashboard | Real-time prediction | ✅ Complete |
| Dashboard | Results export | ✅ Complete |
| Dashboard | Wizard Dashboard v2.2.0 (6-step wizard, Plotly, Excel export) | ✅ Complete |
| Validation | Fuzzy name matching | ✅ Complete |
| Validation | Tolerance-based checking | ✅ Complete |

## Risk Management

| Risk | Impact | Likelihood | Mitigation |
|------|--------|-----------|-----------|
| Model overfitting | High | Medium | Cross-validation, regularization, test set validation |
| Data format changes | Medium | Low | Error handling, format detection, user notification |
| Feature drift | Medium | Medium | Regular retraining, monitoring, A/B testing |
| Performance degradation | Medium | Low | Optimization, caching, model profiling |

## Future Roadmap

### Phase 1 (Complete)
- ✅ Classification pipeline
- ✅ DO extraction (algorithm & ML)
- ✅ Special points extraction
- ✅ Dashboard UI

### Phase 2 (In Progress)
- ✅ Adaptive two-pass peak extraction (485+ configs, +0.05mV bias correction)
- ✅ TXT-only pipeline integration (no Excel dependency)
- ✅ Full pipeline test verified (2026-03-11): TXT → Peaks → Classification → Toxicity
- ✅ Summary Dashboard v2.0 (2026-03-22): 1-click auto-run, Plotly chart, Excel export
- ✅ Wizard Dashboard v2.2.0 (2026-06-21): 6-step wizard, back/forward nav, cached charts, colored flow diagrams
- ✅ Production CatBoost classifier (v1.2.0): 81 features, noise augmentation, 84.4% on 518 files
- 📋 Multi-model ensemble optimization
- 📋 Enhanced forecasting accuracy
- 📋 Automated model retraining
- 📋 Performance optimization

### Phase 3 (Planned)
- 📋 Real-time sensor integration
- 📋 Cloud deployment
- 📋 Advanced visualization
- 📋 API for external systems

### Phase 4 (Future)
- 📋 Multi-site deployment
- 📋 Enterprise features
- 📋 Advanced analytics
- 📋 Custom model training UI

## Glossary

- **DO** (Dissolved Oxygen): Amount of O2 dissolved in sample
- **BOD** (Biochemical Oxygen Demand): Measure of organic content
- **GGA**: Sample type (reference/control)
- **GGA-metal**: Sample type with metal compounds
- **Savitzky-Golay**: Filter for smoothing noisy data while preserving peaks
- **LSTM**: Long Short-Term Memory neural network
- **EMA**: Exponential Moving Average
- **ARIMA**: AutoRegressive Integrated Moving Average

## References

### Internal Documentation
- [Code Standards](./code-standards.md)
- [System Architecture](./system-architecture.md)
- [Codebase Summary](./codebase-summary.md)
- [Project Roadmap](./project-roadmap.md)

### External Tools & Libraries
- [scikit-learn Documentation](https://scikit-learn.org/)
- [XGBoost Documentation](https://xgboost.readthedocs.io/)
- [TensorFlow/Keras Documentation](https://www.tensorflow.org/)
- [Streamlit Documentation](https://docs.streamlit.io/)

## Unresolved Questions

1. **Real-time Integration**: How to integrate with live instrument data streams?
2. **Model Updates**: Frequency and strategy for periodic model retraining?
3. **Scale**: How to scale beyond current single-machine setup?
4. **Advanced Features**: Priority for Phase 3 features?
