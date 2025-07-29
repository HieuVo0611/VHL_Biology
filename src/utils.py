
from sklearn.preprocessing import LabelEncoder
from catboost import CatBoostClassifier
import numpy as np
import os
import tensorflow as tf
import plotly.express as px
from sklearn.preprocessing import MinMaxScaler
from keras.models import load_model
from sklearn.metrics import mean_squared_error

def extract_stages_from_metadata(df, sample_name):
    """
    Trích xuất stage1 và stage2 từ bảng metadata dựa trên sample_name.

    Parameters:
    - df: pandas.DataFrame chứa cột 'Tag' và 'Sample Name'
    - sample_name: tên mẫu cần trích xuất

    Returns:
    - (stage1, stage2): tuple chứa 2 tag đầu tiên (nếu có)
    """
    import re
    # Lọc các dòng có cùng Sample Name
    filtered = df[df['Sample Name'] == sample_name]

    # Lấy danh sách các Tag duy nhất theo thứ tự xuất hiện
    tags = filtered['Tag'].dropna().unique().tolist()

    # Trả về 2 tag đầu tiên (nếu có)
    stage1 = tags[0] if len(tags) > 0 else None
    stage2 = tags[1] if len(tags) > 1 else None

    return stage1, stage2

def calculate_toxicity(metadata_df):
    """
    Calculate toxicity for all samples in the metadata DataFrame.

    Parameters:
    - metadata_df (pd.DataFrame): DataFrame containing columns 'Sample Name', 'Tag', 'Doin (mV)'

    Returns:
    - pd.DataFrame: Summary table with columns:
      ['Sample Name', 'Stage 1', 'Stage 2', 'Toxicity (%)']
    """
    import pandas as pd
    results = []

    for sample_name in metadata_df['Sample Name'].unique():
        # Extract stage tags from metadata
        stage1, stage2 = extract_stages_from_metadata(metadata_df, sample_name)

        if stage1 and stage2:
            # Filter rows for each stage
            df_sample = metadata_df[metadata_df['Sample Name'] == sample_name]
            df_stage1 = df_sample[df_sample['Tag'].str.strip() == stage1.strip()]
            df_stage2 = df_sample[df_sample['Tag'].str.strip() == stage2.strip()]

            if not df_stage1.empty and not df_stage2.empty:
                doin1 = df_stage1['DDO (mV)'].mean()
                doin2 = df_stage2['DDO (mV)'].mean()
                toxicity = round((doin1 - doin2) / doin1 * 100, 2)
            else:
                toxicity = None
        else:
            toxicity = None

        results.append({
            'Sample Name': sample_name,
            'Stage 1': stage1,
            'Stage 2': stage2,
            'Toxicity (%)': toxicity
        })

    return pd.DataFrame(results)

def extract_metadata_single_sample(file_path):
    """
    Extract metadata from a single Excel file with one sample.
    
    Parameters:
    file_path (str): Path to the Excel file
    
    Returns:
    pd.DataFrame: DataFrame containing metadata with columns ['Tag', 'Doin (mV)', 'No.peak', 'DOmin (mV)', 'DDO (mV)', 'Sheet Name', 'Sample Name']
    """
    import pandas as pd
    # Read the Excel file
    xls = pd.ExcelFile(file_path)
    sheet_name = xls.sheet_names[0]  # Assume single sheet
    df = pd.read_excel(xls, sheet_name=sheet_name, header=None)
    
    # Initialize result DataFrame
    result_df = pd.DataFrame(columns=['Tag', 'Doin (mV)', 'No.peak', 'DOmin (mV)', 'DDO (mV)', 'Sheet Name', 'Sample Name'])
    
    # Find sample name (first row, looking for string with 'Q=' pattern)
    sample_name = None
    for col in df.iloc[0]:
        if isinstance(col, str) and 'Q=' in col:
            sample_name = col
            sample_col = df.iloc[0][df.iloc[0] == col].index[0]
            break
    
    if sample_name is None:
        raise ValueError("No sample name found in the Excel file")
    
    # Extract data columns based on sample name column
    min_col = sample_col - 1
    max_col = sample_col + 3
    data_dict = {}
    
    # Process columns in reverse order
    len_data = 0
    for col in range(max_col, min_col-1, -1):
        lst = []
        if col == min_col:
            start_row = df[col].loc[df[col].str.strip() != ""].first_valid_index()
            num_rows = len_data
            subset = df[col].iloc[start_row:start_row+num_rows].replace(" ", np.nan).ffill()
            lst = subset.tolist()
        else:
            for value in df[col]:
                if isinstance(value, (float, int)) and not pd.isna(value):
                    lst.append(value)
            len_data = len(lst)
        data_dict[col] = lst
    
    # Sort dictionary by column index
    sorted_dict = dict(sorted(data_dict.items()))
    
    # Rename keys without modifying dictionary during iteration
    target_names = ['Tag', 'Doin (mV)', 'No.peak', 'DOmin (mV)', 'DDO (mV)']
    new_dict = {}
    for i, key in enumerate(list(sorted_dict.keys())):  # Convert keys to list to avoid iteration issue
        new_dict[target_names[i]] = sorted_dict[key]
    
    # Create DataFrame for the sample
    df_sample = pd.DataFrame(dict([(k, pd.Series(v)) for k, v in new_dict.items()]))
    df_sample['Sheet Name'] = sheet_name
    df_sample['Sample Name'] = sample_name
    
    # Concatenate to result DataFrame
    result_df = pd.concat([result_df.astype(df_sample.dtypes), df_sample.astype(result_df.dtypes)], ignore_index=True)
    
    return result_df

def aggregate_features(df, has_label=True):
    """
    Extract features from DataFrame and return aggregated DataFrame.
    
    Parameters:
    - df: Input DataFrame (df_train or df_test)
    - has_label: If True, include 'label' column in output (for df_train)
    
    Returns:
    - DataFrame with feature columns and label column (if has_label=True)
    """
    from scipy.stats import skew, kurtosis
    from scipy.fft import fft
    import pandas as pd
    # Group by Sample Name
    grouped = df.groupby('Sample Name')
    
    # Initialize dictionary to store features
    feature_dict = {}
    
    # List of columns for statistical feature extraction
    signal_cols = ['Doin (mV)', 'DOmin (mV)', 'DDO (mV)']
    
    # Iterate through each sample
    for sample_name, group in grouped:
        # Initialize dictionary for current sample
        sample_features = {}
        
        # 1. Basic statistics
        for col in signal_cols:
            data = group[col]
            sample_features[f'mean_{col}'] = data.mean() if not data.empty else 0
            sample_features[f'std_{col}'] = data.std() if len(data) > 1 else 0
            sample_features[f'max_{col}'] = data.max() if not data.empty else 0
            sample_features[f'min_{col}'] = data.min() if not data.empty else 0
            sample_features[f'skew_{col}'] = skew(data) if len(data) > 2 else 0
            sample_features[f'kurtosis_{col}'] = kurtosis(data) if len(data) > 3 else 0
            sample_features[f'q25_{col}'] = data.quantile(0.25) if not data.empty else 0
            sample_features[f'q50_{col}'] = data.quantile(0.50) if not data.empty else 0
            sample_features[f'q75_{col}'] = data.quantile(0.75) if not data.empty else 0
        
        # 2. Time series trend features
        for col in signal_cols:
            data = group[col]
            slopes = (data - data.shift(1)) / (group['No.peak'] - group['No.peak'].shift(1))
            sample_features[f'mean_slope_{col}'] = slopes.mean() if not slopes.empty else 0
            sample_features[f'total_abs_change_{col}'] = np.sum(np.abs(data.diff())) if len(data) > 1 else 0
            sample_features[f'sign_changes_{col}'] = np.sum(np.diff(np.sign(data.diff())) != 0) if len(data) > 1 else 0
        
        # 3. Peak distance features
        peak_diffs = group['No.peak'].diff()
        sample_features['mean_peak_diff'] = peak_diffs.mean() if not peak_diffs.empty else 0
        sample_features['std_peak_diff'] = peak_diffs.std() if len(peak_diffs) > 1 else 0
        
        # 4. Frequency features
        for col in signal_cols:
            signal = group[col].values
            fft_vals = np.abs(fft(signal))
            fft_freq = np.fft.fftfreq(len(signal))
            sample_features[f'dominant_freq_amplitude_{col}'] = np.max(fft_vals) if len(fft_vals) > 0 else 0
            sample_features[f'dominant_freq_{col}'] = np.abs(fft_freq[np.argmax(fft_vals)]) if len(fft_vals) > 0 else 0
            sample_features[f'spectral_power_{col}'] = np.sum(fft_vals ** 2) if len(fft_vals) > 0 else 0
            fft_norm = fft_vals / (np.sum(fft_vals) + 1e-10)
            sample_features[f'spectral_entropy_{col}'] = -np.sum(fft_norm * np.log2(fft_norm + 1e-10)) if len(fft_vals) > 0 else 0
        
        # 5. Variable relationship features
        sample_features['mean_DDO_Doin_ratio'] = (group['DDO (mV)'] / group['Doin (mV)']).mean() if len(group) > 0 else 0
        sample_features['mean_DDO_DOmin_ratio'] = (group['DDO (mV)'] / group['DOmin (mV)']).mean() if len(group) > 0 else 0
        sample_features['std_DDO_Doin_ratio'] = (group['DDO (mV)'] / group['Doin (mV)']).std() if len(group) > 1 else 0
        sample_features['corr_Doin_DOmin'] = group['Doin (mV)'].corr(group['DOmin (mV)']) if len(group) > 1 else 0
        sample_features['corr_Doin_DDO'] = group['Doin (mV)'].corr(group['DDO (mV)']) if len(group) > 1 else 0
        
        # 6. Peak features
        hpeak = group['DDO (mV)']
        mean_hpeak = hpeak.mean() if not hpeak.empty else 0
        std_hpeak = hpeak.std() if len(hpeak) > 1 else 0
        sample_features['high_peak_ratio'] = np.sum(hpeak > (mean_hpeak + std_hpeak)) / len(hpeak) if len(hpeak) > 0 else 0
        max_hpeak_peak = group['No.peak'][hpeak.idxmax()] if not hpeak.empty else 0
        sample_features['mean_dist_to_max_peak'] = np.mean(np.abs(group['No.peak'] - max_hpeak_peak)) if len(hpeak) > 0 else 0
        close_peaks = np.sum(peak_diffs < peak_diffs.mean()) / (len(peak_diffs) - 1) if len(peak_diffs) > 1 else 0
        sample_features['close_peak_ratio'] = close_peaks
        top_hpeak = hpeak[hpeak > hpeak.quantile(0.75)]
        sample_features['std_top_hpeak'] = top_hpeak.std() if len(top_hpeak) > 1 else 0
        
        # 7. Cycle features
        crossings = np.sum(np.diff(np.sign(hpeak - mean_hpeak)) != 0) / 2
        sample_features['num_cycles'] = crossings if crossings > 0 else 1
        crossing_indices = np.where(np.diff(np.sign(hpeak - mean_hpeak)) != 0)[0]
        cycle_lengths = np.diff(group['No.peak'].iloc[crossing_indices]) if len(crossing_indices) > 1 else [0]
        sample_features['mean_cycle_length'] = np.mean(cycle_lengths) if len(cycle_lengths) > 0 else 0
        cycle_amplitudes = []
        for i in range(len(crossing_indices) - 1):
            start_idx = crossing_indices[i]
            end_idx = crossing_indices[i + 1]
            cycle_data = hpeak.iloc[start_idx:end_idx + 1]
            amplitude = cycle_data.max() - cycle_data.min()
            cycle_amplitudes.append(amplitude)
        mean_amplitude = np.mean(cycle_amplitudes) if len(cycle_amplitudes) > 0 else 0
        std_amplitude = np.std(cycle_amplitudes) if len(cycle_amplitudes) > 0 else 0
        sample_features['mean_cycle_amplitude'] = mean_amplitude
        sample_features['abnormal_cycle_ratio'] = np.sum(np.array(cycle_amplitudes) > (mean_amplitude + std_amplitude)) / len(cycle_amplitudes) if len(cycle_amplitudes) > 0 else 0
        
        # 8. Time interval features
        q1 = peak_diffs.quantile(0.25) if not peak_diffs.empty else 0
        q3 = peak_diffs.quantile(0.75) if not peak_diffs.empty else 0
        iqr = q3 - q1
        sample_features['short_interval_ratio'] = np.sum(peak_diffs < q1) / len(peak_diffs) if not peak_diffs.empty else 0
        sample_features['long_interval_ratio'] = np.sum(peak_diffs > q3) / len(peak_diffs) if not peak_diffs.empty else 0
        sample_features['coeff_variation_intervals'] = (peak_diffs.std() / peak_diffs.mean()) if peak_diffs.mean() != 0 else 0
        outliers = np.sum((peak_diffs < (q1 - 1.5 * iqr)) | (peak_diffs > (q3 + 1.5 * iqr))) / len(peak_diffs) if not peak_diffs.empty else 0
        sample_features['outlier_interval_ratio'] = outliers
        
        # 9. Number of peaks
        sample_features['num_peaks'] = len(group)
        
        # Add label if exists
        if has_label:
            sample_features['label'] = group['label'].iloc[0]
        
        # Append features to dictionary
        for key, value in sample_features.items():
            if key not in feature_dict:
                feature_dict[key] = []
            feature_dict[key].append(value)
    
    # Convert dictionary to DataFrame
    df_aggregated = pd.DataFrame(feature_dict)
    
    # Handle NaN values
    if has_label:
        df_aggregated.fillna({col: 0 for col in df_aggregated.columns if col != 'label'}, inplace=True)
    else:
        df_aggregated.fillna(0, inplace=True)
    
    return df_aggregated

def catboost_inference_from_csv(df, model_path, label_encoder_path):
    """
    Inference CatBoost model từ file csv.
    Trả về list các tuple (Sample Name, Prediction, Probability)
    """

    df_test_aggregated = aggregate_features(df, has_label=False)
    features = [col for col in df_test_aggregated.columns if col != 'label']
    X_test = df_test_aggregated[features]

    # Load model
    model = CatBoostClassifier()
    model.load_model(model_path)

    # Load label encoder
    le = LabelEncoder()
    le.classes_ = np.load(label_encoder_path, allow_pickle=True)

    # Predict
    y_pred = model.predict(X_test)
    y_pred_label = le.inverse_transform(y_pred.astype(int))
    y_pred_proba = model.predict_proba(X_test)

    # Trả về list các tuple (Sample Name, Prediction, Probability)
    return list(zip(df['Sample Name'].unique(), y_pred_label, y_pred_proba))

def process_and_predict_lstm(txt_file_path, model_path, lookback=7, train_size=0.6, val_size=0.2):
    """
    Process a .txt file, run inference with a pre-trained LSTM model, and return a Plotly figure.
    
    Parameters:
    - txt_file_path: Path to the input .txt file
    - model_path: Path to the pre-trained LSTM model (.keras or .h5)
    - lookback: Number of previous time steps to use as input (default: 7)
    - train_size: Proportion of data for training split (used for indexing, not training)
    - val_size: Proportion of data for validation split (used for indexing, not training)
    
    Returns:
    - Plotly figure comparing actual and predicted DO values for train, validation, test sets, and full real values
    """
    import pandas as pd
    # Set seed for reproducibility
    seed = 42
    np.random.seed(seed)
    tf.random.set_seed(seed)

    # Process .txt file into DataFrame
    def process_txt_file(file_path):
        time_list = []
        do_list = []
        try:
            # Attempt to read with UTF-16 encoding
            temp_data = pd.read_csv(file_path, sep="\t", header=None, usecols=[0, 1], names=["Time", "DO"], encoding='utf-16')
        except UnicodeError:
            # Fallback for files without BOM
            with open(file_path, "r") as f:
                for line in f:
                    parts = line.split()
                    if len(parts) >= 2:
                        time_list.append(float(parts[0].replace("\x00", "")))
                        do_list.append(float(parts[1].replace("\x00", "")))
            temp_data = pd.DataFrame({"Time": time_list, "DO": do_list})
        temp_data["Sample_name"] = os.path.basename(file_path).strip()
        return temp_data

    # Load and process data
    data = process_txt_file(txt_file_path)
    sample_name = data['Sample_name'].iloc[0]
    one_sample_data = data[['DO']].values.astype("float32")

    # Split data into train, validation, and test sets
    def split_data(dataframe, train_size, val_size):
        train_end = int(len(dataframe) * train_size)
        val_end = int(len(dataframe) * (train_size + val_size))
        train = dataframe[:train_end]
        val = dataframe[train_end:val_end]
        test = dataframe[val_end:]
        return train, val, test

    train, val, test = split_data(one_sample_data, train_size, val_size)

    # Check if splits have enough data
    if len(train) < lookback:
        raise ValueError(f"Train set has {len(train)} samples, but lookback requires at least {lookback} samples.")
    if len(val) < lookback:
        raise ValueError(f"Validation set has {len(val)} samples, but lookback requires at least {lookback} samples.")
    if len(test) < lookback:
        raise ValueError(f"Test set has {len(test)} samples, but lookback requires at least {lookback} samples.")

    # Scale data
    scaler_train = MinMaxScaler(feature_range=(0, 1))
    train = scaler_train.fit_transform(train)
    scaler_val = MinMaxScaler(feature_range=(0, 1))
    val = scaler_val.fit_transform(val)
    scaler_test = MinMaxScaler(feature_range=(0, 1))
    test = scaler_test.fit_transform(test)

    # Create features
    def create_features(data, lookback):
        X, Y = [], []
        for i in range(lookback, len(data)):
            X.append(data[i - lookback:i, 0])
            Y.append(data[i, 0])
        return np.array(X), np.array(Y)

    X_train, y_train = create_features(train, lookback)
    X_val, y_val = create_features(val, lookback)
    X_test, y_test = create_features(test, lookback)

    # Check if feature arrays are empty
    if len(X_train) == 0 or len(y_train) == 0:
        raise ValueError("No training samples after applying lookback. Increase train_size or data length.")
    if len(X_val) == 0 or len(y_val) == 0:
        raise ValueError("No validation samples after applying lookback. Increase val_size or data length.")
    if len(X_test) == 0 or len(y_test) == 0:
        raise ValueError("No test samples after applying lookback. Increase data length or reduce train_size/val_size.")

    # Reshape data for LSTM
    X_train = np.reshape(X_train, (X_train.shape[0], 1, X_train.shape[1]))
    X_val = np.reshape(X_val, (X_val.shape[0], 1, X_val.shape[1]))
    X_test = np.reshape(X_test, (X_test.shape[0], 1, X_test.shape[1]))
    y_train = y_train.reshape(-1, 1)
    y_val = y_val.reshape(-1, 1)
    y_test = y_test.reshape(-1, 1)

    # Load pre-trained model
    try:
        model = load_model(model_path)
    except Exception as e:
        raise ValueError(f"Error loading model from {model_path}: {str(e)}")

    # Make predictions
    train_predict = model.predict(X_train, verbose=0)
    val_predict = model.predict(X_val, verbose=0)
    test_predict = model.predict(X_test, verbose=0)

    # Inverse transform predictions and actual values
    train_predict = scaler_train.inverse_transform(train_predict)
    val_predict = scaler_val.inverse_transform(val_predict)
    test_predict = scaler_test.inverse_transform(test_predict)
    y_train = scaler_train.inverse_transform(y_train)
    y_val = scaler_val.inverse_transform(y_val)
    y_test = scaler_test.inverse_transform(y_test)

    # Calculate RMSE for each set
    train_rmse = np.sqrt(mean_squared_error(y_train, train_predict))
    val_rmse = np.sqrt(mean_squared_error(y_val, val_predict))
    test_rmse = np.sqrt(mean_squared_error(y_test, test_predict))

    # Create time axis for plotting
    train_time_steps = data['Time'].values[lookback:lookback+len(y_train)]
    val_time_steps = data['Time'].values[len(train)+lookback:len(train)+lookback+len(y_val)]
    test_time_steps = data['Time'].values[len(train)+len(val)+lookback:len(train)+len(val)+lookback+len(y_test)]

    # Full real values for the entire dataset
    real_time_steps = data['Time'].values
    real_values = one_sample_data.flatten()

    # Verify lengths
    if not (len(train_time_steps) == len(y_train) == len(train_predict) and
            len(val_time_steps) == len(y_val) == len(val_predict) and
            len(test_time_steps) == len(y_test) == len(test_predict)):
        raise ValueError(f"Array length mismatch: "
                         f"Train (time: {len(train_time_steps)}, actual: {len(y_train)}, predicted: {len(train_predict)}), "
                         f"Val (time: {len(val_time_steps)}, actual: {len(y_val)}, predicted: {len(val_predict)}), "
                         f"Test (time: {len(test_time_steps)}, actual: {len(y_test)}, predicted: {len(test_predict)})")

    # Create DataFrame for Plotly
    # Real values DataFrame
    real_df = pd.DataFrame({
        'Time': real_time_steps,
        'DO': real_values,
        'Type': ['Real Values'] * len(real_time_steps)
    })

    # Predicted values DataFrame
    pred_df = pd.DataFrame({
        'Time': np.concatenate([train_time_steps, val_time_steps, test_time_steps]),
        'DO': np.concatenate([train_predict.flatten(), val_predict.flatten(), test_predict.flatten()]),
        'Type': ['Train Predicted'] * len(train_time_steps) + 
                ['Validation Predicted'] * len(val_time_steps) + 
                ['Test Predicted'] * len(test_time_steps)
    })

    # Combine DataFrames
    plot_df = pd.concat([real_df, pred_df], ignore_index=True)

    # Create Plotly figure
    fig = px.line(plot_df, x='Time', y='DO', color='Type',
                  title=f'LSTM Predictions vs Actual DO Values (Train RMSE: {train_rmse:.4f}, Val RMSE: {val_rmse:.4f}, Test RMSE: {test_rmse:.4f}) - {sample_name}',
                  labels={'DO': 'DO', 'Time': 'Time (s)'},
                  color_discrete_map={
                      'Real Values': '#2ca02c',  # Green
                      'Train Predicted': '#1f77b4',  # Blue
                      'Validation Predicted': '#ff7f0e',  # Orange
                      'Test Predicted': '#d62728'  # Red
                  })
    fig.update_layout(legend_title_text='Data Type', showlegend=True)

    return fig

if __name__ == "__main__":
    
    import pandas as pd
    import numpy as np
    import plotly.express as px
    import os

    file_path = r'data/GGA/File Excel/1 sample.xlsx'

    metadata_df = extract_metadata_single_sample(file_path)
    toxicity_df = calculate_toxicity(metadata_df)
    print(toxicity_df)

    for col in ['Doin (mV)', 'No.peak', 'DOmin (mV)', 'DDO (mV)']:
        metadata_df[col] = pd.to_numeric(metadata_df[col], errors='coerce')

    results = catboost_inference_from_csv(
        metadata_df,
        model_path='model/catboost_model.cbm',
        label_encoder_path='model/label_encoder_classes.npy',
    )
    for name, pred, prob in results:
        print(f"Sample: {name} | Prediction: {pred} | Probability: {prob.max():.3f}")

    # Example usage in Streamlit:
    import streamlit as st
    fig = process_and_predict_lstm(r'data/GGA/File txt/N4-VS1-25-03-2024/10-5/N4-10-5-01042024-Q=49.81mL_phút-3.txt', 'model/LSTM Model/28_07_2025/enc-dec_lstm_model.h5')
    st.plotly_chart(fig)

