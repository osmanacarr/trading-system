"""validation/alpha_evaluation.py testleri - sentetik veriyle (Modul 3)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from validation import alpha_evaluation as ae


def test_compute_ic_perfect_positive_correlation():
    factor = [1.0, 2.0, 3.0, 4.0, 5.0]
    returns = [1.0, 2.0, 3.0, 4.0, 5.0]
    assert np.isclose(ae.compute_ic(factor, returns), 1.0)


def test_compute_ic_perfect_negative_correlation():
    factor = [1.0, 2.0, 3.0, 4.0, 5.0]
    returns = [5.0, 4.0, 3.0, 2.0, 1.0]
    assert np.isclose(ae.compute_ic(factor, returns), -1.0)


def test_compute_ic_insufficient_samples_returns_zero():
    factor = [1.0, 2.0, 3.0]
    returns = [1.0, 2.0, 3.0]
    assert ae.compute_ic(factor, returns) == 0.0


def test_compute_ic_handles_nan_pairs():
    factor = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0]
    returns = [1.0, 2.0, 3.0, 4.0, np.nan, 6.0]
    assert np.isclose(ae.compute_ic(factor, returns), 1.0)


def test_compute_ic_mismatched_length_raises():
    with pytest.raises(ValueError):
        ae.compute_ic([1.0, 2.0], [1.0, 2.0, 3.0])


def test_compute_forward_returns_known_values():
    dates = pd.date_range("2020-01-01", periods=5, freq="B")
    df = pd.DataFrame({"Close": [100.0, 110.0, 121.0, 133.1, 146.41]}, index=dates)
    result = ae.compute_forward_returns({"AAA": df}, horizon_days=2)
    row0 = result[result["date"] == dates[0]].iloc[0]
    assert np.isclose(row0["forward_return"], 121.0 / 100.0 - 1.0)
    last_rows = result[result["date"].isin(dates[-2:])]
    assert last_rows["forward_return"].isna().all()


def test_ic_time_series_reflects_daily_direction_and_filters_thin_dates():
    dates = pd.to_datetime(["2020-01-01", "2020-01-02", "2020-01-03"])
    symbols_5 = [f"S{i}" for i in range(5)]

    factor_rows = []
    return_rows = []
    # 2020-01-01: pozitif iliski (IC ~ +1)
    for i, sym in enumerate(symbols_5):
        factor_rows.append({"date": dates[0], "symbol": sym, "factor_name": "f1", "value": float(i)})
        return_rows.append({"date": dates[0], "symbol": sym, "forward_return": float(i)})
    # 2020-01-02: negatif iliski (IC ~ -1)
    for i, sym in enumerate(symbols_5):
        factor_rows.append({"date": dates[1], "symbol": sym, "factor_name": "f1", "value": float(i)})
        return_rows.append({"date": dates[1], "symbol": sym, "forward_return": float(4 - i)})
    # 2020-01-03: sadece 3 sembol (RESEARCH_MIN_IC_SAMPLE_SIZE=5'in altinda) -> ATLANMALI
    for i, sym in enumerate(symbols_5[:3]):
        factor_rows.append({"date": dates[2], "symbol": sym, "factor_name": "f1", "value": float(i)})
        return_rows.append({"date": dates[2], "symbol": sym, "forward_return": float(i)})

    factor_df = pd.DataFrame(factor_rows)
    returns_df = pd.DataFrame(return_rows)

    ic_series = ae.ic_time_series(factor_df, returns_df, factor_name="f1")
    assert list(ic_series.index) == [dates[0], dates[1]]
    assert np.isclose(ic_series.loc[dates[0]], 1.0)
    assert np.isclose(ic_series.loc[dates[1]], -1.0)


def test_ic_time_series_excludes_dates_with_all_nan_forward_returns():
    # bkz. bug fix: forward_return TUMU NaN olan bir tarih (orn. henuz
    # horizon_days kadar gun gecmemis, "gelecek" bilinmiyor) grup buyuklugu
    # esigi gecse bile ATLANMALI - sahte bir IC=0.0 uretilmemeli.
    dates = pd.to_datetime(["2020-01-01", "2020-01-02"])
    symbols_5 = [f"S{i}" for i in range(5)]

    factor_rows = []
    return_rows = []
    for i, sym in enumerate(symbols_5):
        factor_rows.append({"date": dates[0], "symbol": sym, "factor_name": "f1", "value": float(i)})
        return_rows.append({"date": dates[0], "symbol": sym, "forward_return": float(i)})
        factor_rows.append({"date": dates[1], "symbol": sym, "factor_name": "f1", "value": float(i)})
        return_rows.append({"date": dates[1], "symbol": sym, "forward_return": float("nan")})

    factor_df = pd.DataFrame(factor_rows)
    returns_df = pd.DataFrame(return_rows)

    ic_series = ae.ic_time_series(factor_df, returns_df, factor_name="f1")
    assert list(ic_series.index) == [dates[0]]  # dates[1] (tamamen NaN) DAHIL edilmemeli


def test_ic_time_series_empty_when_no_overlap():
    factor_df = pd.DataFrame(columns=["date", "symbol", "factor_name", "value"])
    returns_df = pd.DataFrame(columns=["date", "symbol", "forward_return"])
    result = ae.ic_time_series(factor_df, returns_df, factor_name="f1")
    assert result.empty


def test_detect_decay_flags_declining_ic():
    ic_series = pd.Series([0.5, 0.5, 0.5, 0.5, 0.1, 0.1, 0.1, 0.1])
    result = ae.detect_decay(ic_series)
    assert result["decayed"] is True
    assert np.isclose(result["first_half_mean_ic"], 0.5)
    assert np.isclose(result["second_half_mean_ic"], 0.1)


def test_detect_decay_flags_improving_ic_as_not_decayed():
    ic_series = pd.Series([0.1, 0.1, 0.1, 0.1, 0.5, 0.5, 0.5, 0.5])
    result = ae.detect_decay(ic_series)
    assert result["decayed"] is False


def test_detect_decay_insufficient_data_returns_none_fields():
    result = ae.detect_decay(pd.Series([0.3]))
    assert result["first_half_mean_ic"] is None
    assert result["decayed"] is False


def test_count_active_filters_dict_and_list():
    assert ae.count_active_filters({"a": True, "b": False, "c": True}) == 2
    assert ae.count_active_filters([True, False, True, True]) == 3


def test_check_rule_burden_flags_when_exceeded():
    result = ae.check_rule_burden(n_filters := 6)
    assert result["overfitting_risk"] is True
    assert result["n_filters"] == n_filters


def test_check_rule_burden_no_flag_within_threshold():
    result = ae.check_rule_burden({"a": True, "b": True})
    assert result["overfitting_risk"] is False
