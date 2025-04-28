import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import xgboost as xgb
from icecream import ic
from scipy.stats import skew, kurtosis
from scipy.fft import fft
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
from sklearn.preprocessing import LabelEncoder

# Set random seed for all libraries
SEED = 42
np.random.seed(SEED)
pd.set_option('mode.chained_assignment', None)  # Disable SettingWithCopyWarning

def aggregate_features(df, has_label=True):
    """
    Extract features from DataFrame and return aggregated DataFrame.
    
    Parameters:
    - df: Input DataFrame (df_train or df_test)
    - has_label: If True, include 'label' column in output (for df_train)
    
    Returns:
    - DataFrame with feature columns and label column (if has_label=True)
    """
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
        ddo = group['DDO (mV)']
        mean_ddo = ddo.mean() if not ddo.empty else 0
        std_ddo = ddo.std() if len(ddo) > 1 else 0
        sample_features['high_peak_ratio'] = np.sum(ddo > (mean_ddo + std_ddo)) / len(ddo) if len(ddo) > 0 else 0
        max_ddo_peak = group['No.peak'][ddo.idxmax()] if not ddo.empty else 0
        sample_features['mean_dist_to_max_peak'] = np.mean(np.abs(group['No.peak'] - max_ddo_peak)) if len(ddo) > 0 else 0
        close_peaks = np.sum(peak_diffs < peak_diffs.mean()) / (len(peak_diffs) - 1) if len(peak_diffs) > 1 else 0
        sample_features['close_peak_ratio'] = close_peaks
        top_ddo = ddo[ddo > ddo.quantile(0.75)]
        sample_features['std_top_ddo'] = top_ddo.std() if len(top_ddo) > 1 else 0
        
        # 7. Cycle features
        crossings = np.sum(np.diff(np.sign(ddo - mean_ddo)) != 0) / 2
        sample_features['num_cycles'] = crossings if crossings > 0 else 1
        crossing_indices = np.where(np.diff(np.sign(ddo - mean_ddo)) != 0)[0]
        cycle_lengths = np.diff(group['No.peak'].iloc[crossing_indices]) if len(crossing_indices) > 1 else [0]
        sample_features['mean_cycle_length'] = np.mean(cycle_lengths) if len(cycle_lengths) > 0 else 0
        cycle_amplitudes = []
        for i in range(len(crossing_indices) - 1):
            start_idx = crossing_indices[i]
            end_idx = crossing_indices[i + 1]
            cycle_data = ddo.iloc[start_idx:end_idx + 1]
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

# Read and combine training data
df_gga = pd.read_csv('metadata-gga-2024-10-23.csv')
df_gga['label'] = 'gga' #157
df_gga_metal = pd.read_csv('metadata-gga-metal-2024-10-23.csv')
df_gga_metal['label'] = 'gga-metal' #360 
df_gga_metal_hh = pd.read_csv('metadata-gga-metal-hh-2024-10-23.csv')
df_gga_metal_hh['label'] = 'gga-metal'  #105

# Print sample counts
print("\nSample counts:")
print(f"gga: {len(df_gga['Sample Name'].unique())} samples")
print(f"gga-metal (from df_gga_metal): {len(df_gga_metal['Sample Name'].unique())} samples")
print(f"gga-metal (from df_gga_metal_hh): {len(df_gga_metal_hh['Sample Name'].unique())} samples")

# Combine data
df_train = pd.concat([df_gga, df_gga_metal, df_gga_metal_hh])

# Check input data
for col in ['Doin (mV)', 'DOmin (mV)', 'DDO (mV)', 'No.peak']:
    non_numeric = df_train[col][~pd.to_numeric(df_train[col], errors='coerce').notnull()]
    if not non_numeric.empty:
        print(f"Column {col} contains non-numeric values: {non_numeric.unique()}")

# Create aggregated training dataset
df_train_aggregated = aggregate_features(df_train, has_label=True)

# Select features and labels
features = [col for col in df_train_aggregated.columns if col not in ['label']]
X = df_train_aggregated[features]
y = df_train_aggregated['label']

# Convert column names to string
X.columns = X.columns.astype(str)

# Split data into training and test sets
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.4, stratify=y, random_state=SEED)

# Reset indices
X_train = X_train.reset_index(drop=True)
y_train = y_train.reset_index(drop=True)
X_test = X_test.reset_index(drop=True)
y_test = y_test.reset_index(drop=True)

# Debug
ic(X_train.head())
ic(X_train.shape)
ic(y_train.head())
ic(len(y_train))

# Encode labels for XGBoost
le = LabelEncoder()
y_train_encoded = le.fit_transform(y_train)
y_test_encoded = le.transform(y_test)

# Train Random Forest model
rf_model = RandomForestClassifier(n_estimators=100, random_state=SEED, class_weight='balanced')
rf_model.fit(X_train, y_train)

# Train XGBoost model
xgb_model = xgb.XGBClassifier(
    n_estimators=100,
    learning_rate=0.1,
    max_depth=6,
    min_child_weight=1,
    gamma=0,
    subsample=0.8,
    colsample_bytree=0.8,
    objective='binary:logistic',
    scale_pos_weight=1,
    random_state=SEED
)
xgb_model.fit(X_train, y_train_encoded)

# Evaluate Random Forest model
rf_y_pred = rf_model.predict(X_test)
print("\nRandom Forest Model evaluation on test set:")
print(classification_report(y_test, rf_y_pred))

# Evaluate XGBoost model
xgb_y_pred = le.inverse_transform(xgb_model.predict(X_test))
print("\nXGBoost Model evaluation on test set:")
print(classification_report(y_test, xgb_y_pred))

# Feature importance analysis for Random Forest
rf_feature_importance = pd.DataFrame({
    'feature': X.columns,
    'importance': rf_model.feature_importances_
})
rf_feature_importance = rf_feature_importance.sort_values('importance', ascending=False)

# Feature importance analysis for XGBoost
xgb_feature_importance = pd.DataFrame({
    'feature': X.columns,
    'importance': xgb_model.feature_importances_
})
xgb_feature_importance = xgb_feature_importance.sort_values('importance', ascending=False)

# Print top 20 most important features for both models
print("\nTop 20 most important features - Random Forest:")
print(rf_feature_importance.head(20))

print("\nTop 20 most important features - XGBoost:")
print(xgb_feature_importance.head(20))

# Plot feature importance for both models
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(20, 8))

# Random Forest feature importance
sns.barplot(x='importance', y='feature', data=rf_feature_importance.head(20), ax=ax1)
ax1.set_title('Top 20 Most Important Features - Random Forest')
ax1.set_xlabel('Importance Score')
ax1.set_ylabel('Feature')

# XGBoost feature importance
sns.barplot(x='importance', y='feature', data=xgb_feature_importance.head(20), ax=ax2)
ax2.set_title('Top 20 Most Important Features - XGBoost')
ax2.set_xlabel('Importance Score')
ax2.set_ylabel('Feature')

plt.tight_layout()
plt.savefig('feature_importance_comparison.png')
plt.close()

# Inference on test_example.csv
df_test = pd.read_csv('sample/test_example.csv')
df_test_aggregated = aggregate_features(df_test, has_label=False)
df_test_aggregated.fillna(0, inplace=True)

# Make predictions with both models
X_test_final = df_test_aggregated[features]
X_test_final.columns = X_test_final.columns.astype(str)

# Random Forest predictions
rf_predictions = rf_model.predict(X_test_final)
rf_probabilities = rf_model.predict_proba(X_test_final)

# XGBoost predictions
xgb_predictions = le.inverse_transform(xgb_model.predict(X_test_final))
xgb_probabilities = xgb_model.predict_proba(X_test_final)

# Print results
print("\nPredictions for samples in test_example.csv:")
for name, rf_pred, rf_prob, xgb_pred, xgb_prob in zip(
    df_test['Sample Name'].unique(), 
    rf_predictions, 
    rf_probabilities,
    xgb_predictions,
    xgb_probabilities
):
    print(f"\nSample: {name}")
    print(f"Random Forest - Prediction: {rf_pred}, Probability: {rf_prob}")
    print(f"XGBoost - Prediction: {xgb_pred}, Probability: {xgb_prob}")