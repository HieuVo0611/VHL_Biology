# VHL Biology - Code Standards & Codebase Structure

**Last Updated**: 2026-03-22
**Version**: 1.1.0
**Applies To**: All Python code in VHL Biology project

## Directory Structure

```
VHL_Biology/
├── code/                    # Core analysis scripts
├── src/                     # Utility modules
├── tools/                   # Data processing utilities
├── model/                   # Trained models (versioned)
├── notebooks/               # Jupyter analysis & experimentation
├── data/                    # Sample and training data
├── docs/                    # Project documentation
├── app.py                   # Streamlit Summary Dashboard v2.0 (root)
├── app_legacy.py            # Legacy 5-step dashboard backup (root)
├── test.py                  # Standalone testing script (root)
├── peak_finder.py           # OriginLab integration (root)
└── requirements.txt         # Python dependencies
```

## File Organization Standards

### Code Directory (`/code`)
- **gga_classification_model.py**: Classification pipeline (RF + XGBoost)
- **extract_DO_in.py**: DO extremum extraction using Savitzky-Golay
- **extract_special_points.py**: Fixed-interval special point extraction
- **ema_model.py**: EMA forecasting with RF regressor
- **process_txt_data.py**: UTF-16 TXT → CSV conversion
- **check_matching_name.py**: Fuzzy name matching between samples
- **train extract special points/**: ML-based extraction subdirectory
  - create_dataset.py, train_xgboost.py, predict_and_extract.py

### Src Directory (`/src`)
- **peak_extractor.py**: Production adaptive peak extraction (448 lines)
  - Two-pass HH detection, bias correction, tuned 485+ configs
  - Input: DO time-series array
  - Output: DataFrame [No.peak, Tag, Doin, DOmin, DDO, Sample Name]
- **utils.py**: Core utilities (549 lines — feature engineering, 85+ features, inference)
  - extract_peaks_from_txt(): TXT file wrapper for peak_extractor.py
  - catboost_inference_from_csv(): Classification from peaks
  - process_and_predict_lstm(): LSTM prediction on raw data
  - calculate_toxicity(): Domain-specific metrics
  - aggregate_features(): 81 features (9 categories) per sample
- **export_excel.py**: Excel report generator (Summary Dashboard v2.0)
  - Generates formatted 2-sheet workbook via openpyxl
  - Sheet 1 (Summary): sample name, classification, toxicity, signal stats
  - Sheet 2 (Peaks): full peaks table with BOD10/BOD5 color coding
- **visualize_data.py**: Visualization utilities with peak marking

### Tools Directory (`/tools`)
- **derive_metadata_from_txt.py**: Signal processing peak detection
- **validate_metadata.py**: Tolerance-based validation
- **generate_comprehensive_report.py**: Word document report generation
- **analyze_metal_errors.py**: Per-peak error analysis (4 datasets, failure modes)
- **test_metal_targeted.py**: 47 bias/param config sweep
- **test_bias_finetune.py**: Bias fine-tuning (19 configs)
- **test_ml_correction.py**: ML correction experiment (GBR/RF vs uniform bias)
- **generate-progress-report-260311.py**: Vietnamese progress report (.docx)

### Root Level
- **app.py**: Streamlit Summary Dashboard v2.0 (349 lines, 1-click auto-run pipeline)
- **app_legacy.py**: Legacy 5-step sequential dashboard (backup, original 152-line version)
- **test.py**: Standalone peak detection and testing
- **peak_finder.py**: OriginLab Pro automation integration

### Python Environment
- **Recommended**: conda env `vhl` (pre-configured)
- **Key packages**: CatBoost 1.2.8, TensorFlow 2.19.0, Keras 3.10.0, SciPy, scikit-learn
- **Activation**: `conda activate vhl`
- **Alternative**: `pip install -r requirements.txt` (system Python)

### Models Directory (`/model`)
- **LSTM Model/**: Trained LSTM encoder-decoder variants (2024-2025)
- **RF Model/**: Random Forest classifiers with dates
- **catboost_model.cbm**: CatBoost classifier
- **label_encoder_classes.npy**: Label encoding for predictions

## Naming Conventions

### Python Files
- **Format**: snake_case with descriptive names
- **Examples**: `gga_classification_model.py`, `extract_DO_in.py`, `process_txt_data.py`
- **Convention**: Verbs first for action scripts, nouns for utilities

### Python Functions
- **Format**: snake_case, lowercase
- **Examples**: `extract_features()`, `train_classifier()`, `predict_do_values()`
- **Convention**: Start with verb when performing action

### Python Classes
- **Format**: PascalCase
- **Examples**: `DoExtractor`, `ClassificationPipeline`, `LSTMPredictor`
- **Convention**: Noun-based names describing entity

### Python Variables
- **Format**: snake_case, lowercase
- **Examples**: `do_values`, `sample_name`, `feature_importance`
- **Convention**: Descriptive names for clarity

### Constants
- **Format**: UPPER_SNAKE_CASE
- **Examples**: `SAVITZKY_GOLAY_WINDOW = 31`, `BOD_5_DAY_THRESHOLD = 5`
- **Convention**: All caps for module-level constants

### Data Files
- **Metadata**: `metadata-gga-*.csv`, `metadata-gga-txt.csv`
- **Results**: `special_points_perfect.csv`, `special_points_plateau_mean.csv`
- **Models**: `random_forest.pkl`, `enc-dec_lstm_model.h5`, `catboost_model.cbm`

## File Size Management

**Limit**: 500 lines per Python file (except auto-generated, marked clearly)

**Refactoring Strategies When Exceeded**:
1. Extract utility functions to utils module
2. Split large pipelines into focused components
3. Move data processing to separate files
4. Create separate test files for unit tests

**Exceptions**:
- Notebooks (Jupyter) – no line limit
- Generated config files – mark with `# AUTO-GENERATED`
- Model files – stored as pickles, not code

## Code Style Guidelines

### Indentation & Formatting
- **Indentation**: 4 spaces (Python standard)
- **Line Length**: Max 100 characters (exceed when necessary)
- **Blank Lines**: 2 lines between functions/classes, 1 within functions
- **Whitespace**: `if (`, `for (`, `while (` – consistent spacing

### Comments & Documentation

**File Headers** (recommended):
```python
"""
Module: gga_classification_model.py
Purpose: Train and evaluate RF/XGBoost classifiers for sample classification
Author: VHL Team
Version: 1.0.0
"""
```

**Function Documentation**:
```python
def extract_features(data, window_size=31):
    """
    Extract 85+ features from time-series data.

    Args:
        data (array-like): Time-series DO values
        window_size (int): Savitzky-Golay window size

    Returns:
        dict: Dictionary of engineered features

    Raises:
        ValueError: If data is empty or invalid window size
    """
```

**Inline Comments**:
- Explain WHY, not WHAT
- Mark TODOs with date: `# TODO(2026-01-16): Optimize feature extraction`
- Mark WORKAROUNDs: `# WORKAROUND: UTF-16 encoding issues on Windows`

### Error Handling

**Always Use Try-Catch**:
```python
try:
    data = pd.read_csv(filepath, encoding='utf-16')
except UnicodeDecodeError:
    logger.warning(f"UTF-16 decode failed for {filepath}, trying UTF-8")
    data = pd.read_csv(filepath, encoding='utf-8')
except Exception as e:
    logger.error(f"Failed to read {filepath}: {str(e)}")
    raise
```

**Custom Exceptions**:
```python
class DataValidationError(Exception):
    """Raised when data validation fails"""
    pass

class ModelInferenceError(Exception):
    """Raised when model prediction fails"""
    pass
```

## Testing Standards

### Test File Organization
- **Unit Tests**: In `test.py` or `tests/` directory
- **Integration Tests**: In notebooks for pipeline validation
- **Validation Tests**: In `tools/validate_metadata.py`

### Test Naming
```python
def test_extract_do_values():
    """Test DO value extraction from sample data"""
    # Arrange
    sample_data = load_sample_data()

    # Act
    result = extract_features(sample_data)

    # Assert
    assert len(result) == 85  # 85 expected features
    assert 'DO_in' in result
```

### Test Requirements
- **Coverage**: > 70% for critical paths
- **Data Validation**: Test with real sample data
- **Error Cases**: Test missing/malformed data
- **Edge Cases**: Test boundary conditions

## Git Standards

### Commit Messages
**Format**: Conventional Commits

```
type(scope): description

Optional body with more details.
Lines wrapped at 72 characters.

Optional footer:
Fixes #123
```

**Types**:
- `feat`: New feature (e.g., new extraction method)
- `fix`: Bug fix (e.g., encoding issue)
- `docs`: Documentation update
- `refactor`: Code refactoring without functionality change
- `perf`: Performance improvement
- `test`: Test addition/modification
- `ci`: CI/CD changes

**Examples**:
```
feat(extraction): add ML-based DO extraction using XGBoost

Implements trained XGBoost model for more accurate DO extraction.
Replaces algorithm-based extraction for production.

Fixes #42

---

fix(encoding): handle UTF-16 encoding errors gracefully

Use chardet for automatic encoding detection instead of hardcoded UTF-16.
Falls back to UTF-8 if UTF-16 fails.
```

### Branch Naming
- `feature/`: New features (e.g., `feature/ml-extraction`)
- `fix/`: Bug fixes (e.g., `fix/utf16-encoding`)
- `refactor/`: Code improvements (e.g., `refactor/feature-engineering`)
- `docs/`: Documentation (e.g., `docs/api-reference`)

### Pre-Commit Checklist
- ✅ Code follows style guidelines
- ✅ No hardcoded paths or credentials
- ✅ Tests pass locally
- ✅ Docstrings updated
- ✅ Files under 500 lines
- ✅ No debug prints or console.log statements

## Security Standards

### Input Validation
```python
def validate_sample_data(data):
    """Validate input data before processing"""
    if not isinstance(data, pd.DataFrame):
        raise TypeError("Expected DataFrame")
    if data.empty:
        raise ValueError("DataFrame is empty")
    if 'DO_value' not in data.columns:
        raise ValueError("Missing 'DO_value' column")
    return True
```

### Sensitive Data Handling
- **Never**: Hardcode API keys, credentials, or paths
- **Never**: Log passwords or sensitive values
- **Use**: Environment variables for configuration
- **Store**: Credentials in `.env` (add to `.gitignore`)

### File Path Security
```python
# GOOD: Configurable paths
model_path = os.getenv('MODEL_PATH', 'model/default.pkl')
data_path = os.path.join('data', 'processed', filename)

# BAD: Hardcoded paths
model = load('C:\\Users\\John\\model.pkl')
```

## Data Processing Standards

### Feature Engineering
**85+ Features Extracted**:
1. **Statistical** (mean, std, min, max, median, quantiles)
2. **Time-Series** (autocorr, entropy, trend, seasonality)
3. **Domain-Specific** (degradation rate, half-life, plateau metrics)
4. **Aggregate** (slope, acceleration, variability)

**Feature Scaling**:
```python
from sklearn.preprocessing import StandardScaler

scaler = StandardScaler()
features_scaled = scaler.fit_transform(features)
```

### Data Validation
```python
def validate_metadata(df):
    """Validate extracted metadata"""
    # Check required columns
    required = ['Timestamp', 'DO_value', 'Temperature']
    assert all(col in df.columns for col in required)

    # Check value ranges
    assert df['DO_value'].between(0, 15).all(), "DO out of range"
    assert df['Temperature'].between(0, 50).all(), "Temp out of range"

    return True
```

## Model Management Standards

### Model Storage
- **Location**: `model/[Type]/[Date]/[model_name]`
- **Example**: `model/LSTM Model/28_07_2025/enc-dec_lstm_model.h5`
- **Versioning**: Use dates and version numbers
- **Documentation**: Save hyperparameters alongside models

### Model Loading
```python
import joblib
import json

# Load model
model = joblib.load('model/RF Model/03012025/random_forest.pkl')

# Load hyperparameters
with open('model/RF Model/03012025/hyperparameters.json') as f:
    params = json.load(f)
```

### Model Evaluation
```python
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score

# Evaluate
accuracy = accuracy_score(y_test, y_pred)
f1 = f1_score(y_test, y_pred, average='weighted')
cm = confusion_matrix(y_test, y_pred)

print(f"Accuracy: {accuracy:.3f}")
print(f"F1-Score: {f1:.3f}")
print(f"Confusion Matrix:\n{cm}")
```

## Performance Standards

### Classification Pipeline
- **Accuracy Target**: > 85%
- **Training Time**: < 1 hour
- **Inference Time**: < 500ms/sample
- **Feature Count**: 70-85 engineered features

### DO Extraction
- **Algorithm Method**: < 1 second/sample
- **ML Method**: < 200ms/sample
- **Accuracy**: > 95% vs manual

### Dashboard
- **Response Time**: < 2 seconds
- **Memory Usage**: < 2GB
- **Batch Size**: 100 samples in < 5 minutes

## Documentation Standards

### Inline Documentation
- **Self-documenting code**: Clear names reduce need for comments
- **Complex logic**: Always comment non-obvious algorithms
- **Configuration**: Document all parameters and their defaults
- **Changes**: Document why, not what

### External Documentation
- **README**: Quick start and overview
- **API Docs**: Function signatures and usage examples
- **Architecture**: System design and data flow diagrams
- **Roadmap**: Future plans and milestones

## Python Best Practices

### Imports
```python
# Standard library first
import os
import json
from pathlib import Path

# Third-party packages
import numpy as np
import pandas as pd
from scipy import signal

# Project modules
from src.utils import extract_features
from src.visualize_data import plot_results
```

### Type Hints (recommended)
```python
from typing import Dict, List, Optional, Tuple

def extract_features(data: np.ndarray,
                     window: int = 31) -> Dict[str, float]:
    """Extract features from time-series data"""
    pass

def predict_batch(samples: List[pd.DataFrame]) -> Tuple[np.ndarray, float]:
    """Predict on batch of samples"""
    pass
```

### Logging
```python
import logging

logger = logging.getLogger(__name__)

logger.debug("Processing sample: %s", sample_id)
logger.info("Classification complete: %d samples", count)
logger.warning("Low confidence score: %.2f", score)
logger.error("Failed to extract features: %s", str(error))
```

## Collaboration Guidelines

### Code Review Checklist
- ✅ Code follows naming conventions
- ✅ Functions have docstrings
- ✅ Error handling is comprehensive
- ✅ No hardcoded credentials
- ✅ Tests pass with good coverage
- ✅ Files under 500 lines
- ✅ Commit messages are clear
- ✅ Documentation is updated

### Pull Request Template
```markdown
## Description
Brief summary of changes

## Type of Change
- [ ] Feature
- [ ] Bug fix
- [ ] Documentation update

## Testing
- Tested with sample data: [yes/no]
- Code coverage: [%]
- Error cases handled: [yes/no]

## Related Issues
Fixes #123
```

## Configuration Management

### Environment Variables
```python
import os
from dotenv import load_dotenv

load_dotenv()  # Load from .env file

MODEL_PATH = os.getenv('MODEL_PATH', 'model/default.pkl')
DATA_PATH = os.getenv('DATA_PATH', 'data/')
DEBUG_MODE = os.getenv('DEBUG_MODE', 'false').lower() == 'true'
```

### Configuration Files
- **Models**: Store hyperparameters in JSON alongside model files
- **Paths**: Use configuration constants defined at module top
- **Secrets**: Never commit .env file, use .env.example template

## Maintenance Notes

### Regular Tasks
- **Monthly**: Review model performance metrics
- **Quarterly**: Retrain models with new data
- **Annually**: Comprehensive code audit and refactoring

### Deprecation Process
1. Add `DeprecationWarning` to old functions
2. Document migration path
3. Maintain 2-3 releases before removal
4. Clear changelog entry

### Bug Reporting
Include:
- Description and reproduction steps
- Expected vs actual behavior
- Python version and OS
- Relevant error trace
- Sample data if applicable

## References

### Internal Documentation
- [Project Overview & PDR](./project-overview-pdr.md)
- [System Architecture](./system-architecture.md)
- [Codebase Summary](./codebase-summary.md)
- [Project Roadmap](./project-roadmap.md)

### External Resources
- [PEP 8 – Style Guide](https://pep8.org/)
- [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html)
- [Python Logging Documentation](https://docs.python.org/3/library/logging.html)
- [Conventional Commits](https://conventionalcommits.org/)

## Unresolved Questions

1. **Testing Framework**: Should we adopt pytest instead of unittest?
2. **Type Checking**: Should we enforce mypy for type checking?
3. **Linting**: Which linter (black, flake8, pylint) to standardize on?
4. **CI/CD**: How often should models be automatically retrained?
