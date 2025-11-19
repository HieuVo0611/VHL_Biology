# train_xgboost.py
from xgboost import XGBRegressor
import xgboost as xgb
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error

X = np.load('X.npy')
y = np.load('y.npy')  # shape (N, 2)

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

models = []
for k, name in enumerate(['start', 'interval']):
    print(f"\n=== TRAINING {name.upper()} ===")
    dtrain = xgb.DMatrix(X_train, label=y_train[:, k])
    dvalid = xgb.DMatrix(X_test, label=y_test[:, k])
    bst = xgb.train({
        'objective': 'reg:squarederror', 'max_depth': 5, 'eta': 0.05,
        'subsample': 0.9, 'colsample_bytree': 0.9, 'eval_metric': 'mae',
        'tree_method': 'hist', 'seed': 42, 'nthread': -1
    }, dtrain, num_boost_round=2000, evals=[(dvalid, 'val')],
    early_stopping_rounds=50, verbose_eval=10)
    models.append(bst)
    bst.save_model(f'bod_model_{name}.json')

pred_start = models[0].predict(dvalid)
pred_interval = models[1].predict(dvalid)
print(f"MAE Start: {mean_absolute_error(y_test[:,0], pred_start):.1f}s")
print(f"MAE Interval: {mean_absolute_error(y_test[:,1], pred_interval):.1f}s")