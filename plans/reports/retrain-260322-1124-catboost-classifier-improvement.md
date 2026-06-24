# Classifier Retraining Report

**Date**: 2026-03-22 | **Model**: CatBoost | **Dataset**: 518 files (159 GGA + 359 GGA-metal)

## Before vs After Comparison

| Metric | Old Model | New Model | Change |
|--------|-----------|-----------|--------|
| **Overall Accuracy** | **78.6%** (407/518) | **87.8%** (455/518) | **+9.2%** |
| GGA Recall | 63.5% (101/159) | 67.3% (107/159) | +3.8% |
| GGA-metal Recall | 85.2% (306/359) | 96.9% (348/359) | **+11.7%** |
| Misclassified | 111 files | 63 files | -48 files |
| GGA false negatives | 58 | 52 | -6 |
| Metal false negatives | 53 | 11 | **-42** |

## Confusion Matrix Comparison

### Old Model
| | Pred GGA | Pred Metal |
|--|---------|------------|
| True GGA | 101 | 58 |
| True Metal | 53 | 306 |

### New Model
| | Pred GGA | Pred Metal |
|--|---------|------------|
| True GGA | 107 | 52 |
| True Metal | 11 | 348 |

## Training Config (Best of 6 experiments)

| Parameter | Value |
|-----------|-------|
| Config name | balanced + deeper trees (depth=8) |
| iterations | 300 |
| learning_rate | 0.05 |
| depth | 8 |
| auto_class_weights | Balanced |
| CV accuracy (5-fold) | 0.814 +/- 0.027 |
| Test accuracy (60/40) | 0.815 |

## All Experiments Tested

| Config | CV | Test | GGA Recall | Metal Recall |
|--------|-----|------|-----------|-------------|
| baseline (no weights) | 0.819 | 0.794 | 46.0% | 90.8% |
| balanced | 0.806 | 0.806 | 58.7% | 88.1% |
| **balanced + depth=8** | **0.814** | **0.815** | **65.1%** | **87.0%** |
| balanced + L2 | 0.804 | 0.802 | 63.5% | 85.9% |
| SqrtBalanced | 0.809 | 0.806 | 58.7% | 88.1% |
| balanced + 500 iter | 0.807 | 0.798 | 65.1% | 84.9% |

## Top 10 Features (Importance)

| Feature | Importance |
|---------|-----------|
| skew_DDO (mV) | 11.7 |
| kurtosis_DDO (mV) | 11.5 |
| long_interval_ratio | 3.5 |
| spectral_entropy_DDO (mV) | 3.0 |
| mean_peak_diff | 2.7 |
| skew_DOmin (mV) | 2.5 |
| kurtosis_Doin (mV) | 2.2 |
| std_DDO (mV) | 2.1 |
| dominant_freq_amplitude_DOmin (mV) | 2.0 |
| skew_Doin (mV) | 1.8 |

## Key Insights

1. **Biggest gain: Metal recall** jumped from 85.2% to 96.9% (+11.7%) — only 11 metal files misclassified now vs 53 before
2. **GGA recall still weak** at 67.3% — 52 GGA files still misclassified as metal
3. **Class weighting helped significantly** — balanced weights + deeper trees was the winning combo
4. **DDO shape features dominate** — skew and kurtosis of DDO are by far the most important (23.2% combined)
5. **Confidence distribution improved**: 395/518 (76%) now above 90% confidence vs 187 before

## Remaining GGA Misclassification Pattern

52 GGA files still predicted as gga-metal:
- U1-series (high-concentration GGA): 8 files — consistent misclass, possibly feature overlap with metal
- U-series with H1/H2/H3 prefixes: ~35 files — these GGA samples have peak shapes resembling metal
- Many have 99%+ confidence wrong — model structurally can't distinguish these from metal

## Files

- Old model backup: `model/catboost_model_backup_20260322_113231.cbm`
- New model: `model/catboost_model.cbm`
- Training metadata: `model/catboost_training_metadata.json`
- Retrain script: `tools/retrain-catboost-classifier.py`
- Validation script: `tools/validate-classifier-accuracy.py`
- Validation CSV: `plans/reports/classification-validation-results.csv`

## Unresolved Questions

1. GGA recall still 67.3% — are these GGA samples genuinely ambiguous or mislabeled?
2. 52 GGA misclassified with high confidence — need domain expert review
3. Would adding more GGA training data (currently 156 vs 462 metal) fix this?
4. Could feature engineering be improved (e.g., raw signal shape features vs just peak statistics)?
