import pandas as pd
from src.utils import calculate_toxicity


def test_calculate_toxicity_filters_transition():
    """Transition rows should NOT contribute to stage1 or stage2 mean."""
    df = pd.DataFrame({
        'Sample Name': ['A'] * 7,
        'Tag': ['phase1', 'phase1', 'phase1',
                'transition',
                'phase2', 'phase2', 'phase2'],
        'Doin (mV)': [260.0] * 7,
        'DDO (mV)': [4.0, 4.2, 3.8, 99.0, 2.0, 2.2, 1.8],  # 99 in transition must be ignored
    })
    out = calculate_toxicity(df)
    row = out.iloc[0]
    assert row['Stage 1'] == 'phase1'
    assert row['Stage 2'] == 'phase2'
    # toxicity = (4.0 - 2.0) / 4.0 * 100 = 50.0
    assert abs(row['Toxicity (%)'] - 50.0) < 0.1


def test_calculate_toxicity_backward_compat_bod_tags():
    """Old BOD10/BOD5 tags should still work (backward compat fallback)."""
    df = pd.DataFrame({
        'Sample Name': ['A'] * 4,
        'Tag': ['BOD10', 'BOD10', 'BOD5', 'BOD5'],
        'Doin (mV)': [260.0] * 4,
        'DDO (mV)': [4.0, 4.0, 2.0, 2.0],
    })
    out = calculate_toxicity(df)
    row = out.iloc[0]
    assert abs(row['Toxicity (%)'] - 50.0) < 0.1


def test_calculate_toxicity_all_phase1_returns_none():
    """All phase1 (no phase2) → toxicity None."""
    df = pd.DataFrame({
        'Sample Name': ['A'] * 3,
        'Tag': ['phase1', 'phase1', 'phase1'],
        'Doin (mV)': [260.0] * 3,
        'DDO (mV)': [4.0, 4.1, 3.9],
    })
    out = calculate_toxicity(df)
    assert out.iloc[0]['Toxicity (%)'] is None
