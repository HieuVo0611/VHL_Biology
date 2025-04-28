# VHL Biology Project

This project contains code for analyzing and classifying biological data.

## File Structure

### `gga_classification_model.py`
This is the main script for training and evaluating classification models. It includes:
- Feature extraction and aggregation from input data
- Training of both Random Forest and XGBoost models
- Model evaluation and feature importance analysis
- Prediction on test data

### Input Data Files
- `metadata-gga-2024-10-23.csv`: Training data for GGA samples
- `metadata-gga-metal-2024-10-23.csv`: Training data for GGA-metal samples
- `metadata-gga-metal-hh-2024-10-23.csv`: Additional training data for GGA-metal samples
- `sample/test_example.csv`: Test data for model prediction

## Setup
1. Install required dependencies:
```bash
pip install -r requirements.txt
```

2. Run the classification model:
```bash
python gga_classification_model.py
```

## Output
The script will generate:
- Classification reports for both Random Forest and XGBoost models
- Feature importance plots saved as 'feature_importance_comparison.png'
- Predictions for test samples 
