# VHL Biology Project

This project contains code for analyzing and classifying biological data.

## File Structure

### Code Files (`/code`)
- `gga_classification_model.py`: Main script for training and evaluating classification models
  - Feature extraction and aggregation from input data
  - Training of both Random Forest and XGBoost models
  - Model evaluation and feature importance analysis
  - Prediction on test data

- `extract_DO_in.py`: Script for extracting dissolved oxygen (DO) data from input files

- `process_txt_data.py`: Utility for processing text data files

- `ema_model.py`: Implementation of Exponential Moving Average model

- `predict_BOD-value_future.ipynb`: Jupyter notebook for BOD value prediction

### Notebooks (`/notebooks`)
- `ARIMA_1_0_Bio_VHL.ipynb`: ARIMA model implementation for time series analysis
- `LSTM_Bio_VHL.ipynb`: LSTM neural network implementation
- `LR_BIO_VHL.ipynb`: Linear Regression model implementation
- `SMA_EWMA_method.ipynb`: Simple Moving Average and Exponential Weighted Moving Average methods

### Source Files (`/src`)
- `visualize_data.py`: Utilities for data visualization
- `utils.py`: General utility functions

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
python code/gga_classification_model.py
```

## Output
The script will generate:
- Classification reports for both Random Forest and XGBoost models
- Feature importance plots saved as 'feature_importance_comparison.png'
- Predictions for test samples 
