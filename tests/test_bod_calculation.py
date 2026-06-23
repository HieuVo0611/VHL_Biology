import pytest
from src.utils import calculate_bod_from_calibration


def test_basic_linear_fit():
    # 2 calibration points: BOD=20 → DDO=11.3, BOD=15 → DDO=9.13
    # slope a = (9.13 - 11.3) / (15 - 20) = -2.17 / -5 = 0.434
    # intercept b = 11.3 - 0.434 * 20 = 11.3 - 8.68 = 2.62
    # BOD from DDO=10: (10 - 2.62) / 0.434 = 17.004...
    # BOD from DDO=6:  (6  - 2.62) / 0.434 = 7.788...
    result = calculate_bod_from_calibration(
        ddo_phase1=10.0, ddo_phase2=6.0,
        bod1_cal=20.0, ddo1_cal=11.3,
        bod2_cal=15.0, ddo2_cal=9.13,
    )
    assert abs(result["a"] - 0.434) < 0.001
    assert abs(result["b"] - 2.62)  < 0.01
    assert abs(result["bod_phase1"] - 17.004) < 0.01
    assert abs(result["bod_phase2"] - 7.788)  < 0.01


def test_raises_on_equal_bod_calibration():
    with pytest.raises(ValueError, match="khác nhau"):
        calculate_bod_from_calibration(
            ddo_phase1=10.0, ddo_phase2=6.0,
            bod1_cal=20.0, ddo1_cal=11.3,
            bod2_cal=20.0, ddo2_cal=9.13,  # same BOD → zero slope
        )


def test_return_keys_present():
    result = calculate_bod_from_calibration(
        ddo_phase1=10.0, ddo_phase2=6.0,
        bod1_cal=20.0, ddo1_cal=11.3,
        bod2_cal=15.0, ddo2_cal=9.13,
    )
    assert set(result.keys()) == {"a", "b", "bod_phase1", "bod_phase2"}


def test_values_rounded_to_3dp():
    result = calculate_bod_from_calibration(
        ddo_phase1=10.0, ddo_phase2=6.0,
        bod1_cal=20.0, ddo1_cal=11.3,
        bod2_cal=15.0, ddo2_cal=9.13,
    )
    # bod_phase1 and bod_phase2 rounded to 3 decimal places
    assert result["bod_phase1"] == round(result["bod_phase1"], 3)
    assert result["bod_phase2"] == round(result["bod_phase2"], 3)
