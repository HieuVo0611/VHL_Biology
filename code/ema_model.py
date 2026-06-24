import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error

# scikit-learn-1.5.2

# Step 1: Read data from .txt file
file_path = "BOD2024-Nhung/GGA/File txt/U1-VS1-26-03-2024/2.5-0/U1-2.5-0-04042024-Q=49.96mL_phút-1.txt"  # Path to your file

df = pd.read_csv(file_path, sep="\t", header=None, names=["Time", "DO"])

# Calculate EMA
ema_span = 12
df['EMA'] = df['DO'].ewm(span=ema_span, adjust=False).mean()

# Create lag features using pd.concat for better performance
lags = pd.concat([df['DO'].shift(lag).rename(f'DO_lag_{lag}') for lag in range(1, 101)], axis=1)
df = pd.concat([df, lags], axis=1)

df = df.dropna()  # Drop rows with NaN values

# Split data into training and testing sets
train_len = round(len(df)*0.6)
train = df[:train_len]
test = df[train_len:]

# Prepare features and target
X_train = train[[f'DO_lag_{i}' for i in range(1, 101)] + ['EMA']]
y_train = train['DO']
X_test = test[[f'DO_lag_{i}' for i in range(1, 101)] + ['EMA']]
y_test = test['DO']

# Train Random Forest model
model = RandomForestRegressor(n_estimators=100, random_state=42)
model.fit(X_train, y_train)

# Make predictions on test set
y_pred = model.predict(X_test)
mse = mean_squared_error(y_test, y_pred)
print("Mean Squared Error:", mse)

# Forecast future values (1000 future values)
num_predictions = 1000  # Number of future values to predict
last_values = df.iloc[-100:][[f'DO_lag_{i}' for i in range(1, 101)] + ['EMA']].values.flatten().tolist()  # Last 100 values as starting point
future_predictions = []

for _ in range(num_predictions):
    input_features = last_values[-100:] + [np.mean(last_values[-100:])]
    future_pred = model.predict([input_features])
    future_predictions.append(future_pred[0])
    last_values.append(future_pred[0])

# Append forecasted values to the main DataFrame
time_max = df['Time'].max()
forecast_df = pd.DataFrame({
    'Time': range(time_max + 1, time_max + num_predictions + 1),
    'DO': future_predictions
})
df = pd.concat([df, forecast_df], ignore_index=True)

# Visualization
y_hat_ema = df.copy()
y_hat_ema['ema_forecast'] = df['DO'].ewm(span=ema_span, adjust=False).mean()
y_hat_ema['ema_forecast'][train_len:] = y_hat_ema['ema_forecast'][train_len-1]

plt.figure(figsize=(20,5))
plt.grid()
plt.plot(train['DO'], label='Train')
plt.plot(test['DO'], label='Test')
plt.plot(y_hat_ema['ema_forecast'], label='Exponential moving average forecast')
plt.legend(loc='best')
plt.title('Exponential Moving Average Method')
plt.show()

# Calculate RMSE and MAPE
rmse = np.sqrt(mean_squared_error(test['DO'], y_hat_ema['ema_forecast'][train_len:])).round(2)
mape = np.round(np.mean(np.abs(test['DO'] - y_hat_ema['ema_forecast'][train_len:]) / test['DO']) * 100, 2)

results = pd.DataFrame({'Method': ['Exponential moving average forecast'], 'RMSE': [rmse], 'MAPE': [mape]})
results = results[['Method', 'RMSE', 'MAPE']]
print(results)
