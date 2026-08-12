"""paper_trading/runner.py icin sentetik veri + ag gerektirmeyen testler."""

from __future__ import annotations

import datetime as dt

import numpy as np
import pandas as pd
import pytest

import paper_trading.runner as runner_module
from paper_trading.logger import PaperTradingLogger
from paper_trading.runner import run_once
from paper_trading.state import PaperTradingState
from tests.conftest import append_bars, make_flat_range_df


@pytest.fixture
def state(tmp_path):
    s = PaperTradingState(db_path=tmp_path / "state.db", initial_capital=10_000.0)
    yield s
    s.close()


@pytest.fixture
def trade_logger(tmp_path):
    return PaperTradingLogger(log_dir=tmp_path / "logs")


def _breakout_df(n_base: int = 70) -> pd.DataFrame:
    base = make_flat_range_df(n=n_base, price=100.0, half_range=1.0, volume=1000.0)
    breakout = {"Open": 101.0, "High": 116.0, "Low": 100.5, "Close": 115.0, "Volume": 6000.0}
    return append_bars(base, [breakout])


def _short_breakout_df(n_base: int = 70) -> pd.DataFrame:
    base = make_flat_range_df(n=n_base, price=100.0, half_range=1.0, volume=1000.0)
    breakdown = {"Open": 99.0, "High": 99.5, "Low": 84.0, "Close": 85.0, "Volume": 6000.0}
    return append_bars(base, [breakdown])


def _uncorrelated_flat_df(n: int = 71) -> pd.DataFrame:
    """make_flat_range_df ile AYNI olcekte DEGIL, farkli bir zamansal
    desene (yavas sinus salinimi) sahip, sinyal-uretmeyen (duz/durgun)
    bir seri - iki testte AYNI make_flat_range_df cagrisini kullanmak
    (parametreler farkli olsa bile) mukemmel korelasyonlu (1.0) cikip
    korelasyon-kume testlerini yanlislikla etkiliyordu."""
    dates = pd.date_range("2020-01-01", periods=n, freq="B")
    t = np.arange(n)
    close = 50.0 + 0.5 * np.sin(2 * np.pi * t / 23.0)
    high = close + 0.2
    low = close - 0.2
    open_ = np.roll(close, 1)
    open_[0] = 50.0
    volume = np.full(n, 500.0)
    return pd.DataFrame({"Open": open_, "High": high, "Low": low, "Close": close, "Volume": volume}, index=dates)


def _trend_then_breakout_df(n_base: int = 70, weekly_step: float = -0.5, breakout_up: bool = True) -> pd.DataFrame:
    """N gunluk dogrusal trend (haftalik bias uretmek icin) + kirilim bari.

    weekly_step<0 (dusus trendi) + breakout_up=True -> CELISEN senaryo
    (haftalik bias 'down', ama Donchian long kirilimi tetikleniyor).
    weekly_step>0 (yukselis trendi) + breakout_up=True -> UYUMLU senaryo.
    """
    dates = pd.date_range("2020-01-01", periods=n_base, freq="B")
    close = 150.0 + weekly_step * np.arange(n_base)
    high = close + 1.0
    low = close - 1.0
    open_ = close + (0.3 if weekly_step < 0 else -0.3)
    volume = np.full(n_base, 1000.0)
    base = pd.DataFrame({"Open": open_, "High": high, "Low": low, "Close": close, "Volume": volume}, index=dates)

    last_close = close[-1]
    if breakout_up:
        bar = {"Open": last_close + 1, "High": last_close + 16, "Low": last_close + 0.5, "Close": last_close + 15, "Volume": 6000.0}
    else:
        bar = {"Open": last_close - 1, "High": last_close - 0.5, "Low": last_close - 16, "Close": last_close - 15, "Volume": 6000.0}
    return append_bars(base, [bar])


def _down_move_df(n_base: int = 70) -> pd.DataFrame:
    base = make_flat_range_df(n=n_base, price=100.0, half_range=1.0, volume=1000.0)
    down_bar = {"Open": 100.0, "High": 100.5, "Low": 90.0, "Close": 91.0, "Volume": 1000.0}
    return append_bars(base, [down_bar])


def _no_signal_df(n_base: int = 70) -> pd.DataFrame:
    return make_flat_range_df(n=n_base, price=100.0, half_range=1.0, volume=1000.0)


def _hold_far_from_stop_df(n_base: int = 70) -> pd.DataFrame:
    """Pozisyon acik kalir (stop tetiklenmez) ve fiyat stop'tan uzaktir."""
    base = make_flat_range_df(n=n_base, price=100.0, half_range=1.0, volume=1000.0)
    bar = {"Open": 99.8, "High": 100.5, "Low": 99.0, "Close": 99.9, "Volume": 1000.0}
    return append_bars(base, [bar])


def _hold_near_stop_df(n_base: int = 70) -> pd.DataFrame:
    """Pozisyon acik kalir (stop tetiklenmez) ama fiyat stop'a cok yakindir."""
    base = make_flat_range_df(n=n_base, price=100.0, half_range=1.0, volume=1000.0)
    bar = {"Open": 99.95, "High": 100.1, "Low": 99.85, "Close": 99.9, "Volume": 1000.0}
    return append_bars(base, [bar])


def _make_fetch_fn(dataframes: dict):
    def fetch_fn(ticker, start=None, end=None):
        if ticker not in dataframes:
            raise RuntimeError(f"bilinmeyen sembol: {ticker}")
        return dataframes[ticker].copy()

    return fetch_fn


def test_entry_opens_position(state, trade_logger):
    df = _breakout_df()
    run_date = df.index[-1].date()
    fetch_fn = _make_fetch_fn({"FAKE-USD": df})

    summary = run_once(
        strategies=["donchian"], run_date=run_date, dry_run=False,
        state=state, trade_logger=trade_logger, fetch_fn=fetch_fn,
        markets={"crypto": ["FAKE-USD"]}, verbose=False,
    )

    assert summary["results"][0].action == "entry_long"
    pos = state.get_position("FAKE-USD", "donchian")
    assert pos is not None
    assert pos.direction == 1
    assert pos.strategy == "donchian"

    trades = trade_logger.read_trades()
    assert len(trades) == 1
    assert trades.iloc[0]["event_type"] == "entry"


def test_stop_exit_closes_position(state, trade_logger):
    state.open_position(
        "FAKE-USD", "donchian", direction=1, entry_date=dt.date(2019, 1, 1),
        entry_price=100.0, stop_price=95.0, size=10.0,
    )
    starting_equity = state.get_equity()

    df = _down_move_df()
    run_date = df.index[-1].date()
    fetch_fn = _make_fetch_fn({"FAKE-USD": df})

    summary = run_once(
        strategies=["donchian"], run_date=run_date, dry_run=False,
        state=state, trade_logger=trade_logger, fetch_fn=fetch_fn,
        markets={"crypto": ["FAKE-USD"]}, verbose=False,
    )

    assert summary["results"][0].action == "exit"
    assert summary["results"][0].detail == "stop"
    assert state.get_position("FAKE-USD", "donchian") is None
    assert state.get_equity() < starting_equity  # stop kaybi

    trades = trade_logger.read_trades()
    assert len(trades) == 1
    assert trades.iloc[0]["event_type"] == "exit"
    assert trades.iloc[0]["exit_reason"] == "stop"
    assert trades.iloc[0]["pnl"] < 0


def test_idempotency_same_day_double_run(state, trade_logger):
    df = _breakout_df()
    run_date = df.index[-1].date()
    fetch_fn = _make_fetch_fn({"FAKE-USD": df})

    run_once(
        strategies=["donchian"], run_date=run_date, state=state, trade_logger=trade_logger,
        fetch_fn=fetch_fn, markets={"crypto": ["FAKE-USD"]}, verbose=False,
    )
    summary2 = run_once(
        strategies=["donchian"], run_date=run_date, state=state, trade_logger=trade_logger,
        fetch_fn=fetch_fn, markets={"crypto": ["FAKE-USD"]}, verbose=False,
    )

    assert summary2["results"][0].action == "skip_already_processed"
    # Ikinci calistirma sinyali TEKRAR islememeli: hala tek pozisyon, tek trade kaydi
    assert len(state.list_open_positions()) == 1
    trades = trade_logger.read_trades()
    assert len(trades) == 1


def test_fetch_failure_skips_symbol_and_continues(state, trade_logger):
    good_df = _breakout_df()
    run_date = good_df.index[-1].date()

    def flaky_fetch(ticker, start=None, end=None):
        if ticker == "BAD-USD":
            raise RuntimeError("gecici ag hatasi")
        return good_df.copy()

    summary = run_once(
        strategies=["donchian"], run_date=run_date, state=state, trade_logger=trade_logger,
        fetch_fn=flaky_fetch, markets={"crypto": ["BAD-USD", "GOOD-USD"]}, verbose=False,
        fetch_max_attempts=2, fetch_base_delay=0.0, fetch_sleep_fn=lambda s: None,
    )

    results_by_symbol = {r.symbol: r for r in summary["results"]}
    assert results_by_symbol["BAD-USD"].action == "skip_fetch_error"
    assert results_by_symbol["GOOD-USD"].action == "entry_long"
    # BAD-USD icin state/pozisyon degismemis olmali, GOOD-USD icin acilmis olmali
    assert state.get_position("BAD-USD", "donchian") is None
    assert state.get_position("GOOD-USD", "donchian") is not None


def test_multi_symbol_multi_position(state, trade_logger):
    df_a = _breakout_df()
    df_b = _breakout_df()
    run_date = df_a.index[-1].date()
    fetch_fn = _make_fetch_fn({"SYM-A": df_a, "SYM-B": df_b})

    run_once(
        strategies=["donchian"], run_date=run_date, state=state, trade_logger=trade_logger,
        fetch_fn=fetch_fn, markets={"crypto": ["SYM-A", "SYM-B"]}, verbose=False,
    )

    open_symbols = {p.symbol for p in state.list_open_positions()}
    assert open_symbols == {"SYM-A", "SYM-B"}


def test_bist_weekend_is_skipped_without_fetching(state, trade_logger):
    saturday = dt.date(2024, 1, 6)
    assert saturday.weekday() == 5

    def fetch_fn(ticker, start=None, end=None):
        raise AssertionError("hafta sonu BIST icin fetch cagrilmamali")

    summary = run_once(
        strategies=["donchian"], run_date=saturday, state=state, trade_logger=trade_logger,
        fetch_fn=fetch_fn, markets={"bist": ["THYAO.IS"]}, verbose=False,
    )
    assert summary["results"][0].action == "skip_weekend"


def test_crypto_runs_on_weekend(state, trade_logger):
    df = _breakout_df()
    # veri setini bilerek bir Cumartesi'ye "tasi" - kripto hafta sonu da calismali
    saturday = dt.date(2024, 1, 6)
    df.index = pd.date_range(end=saturday, periods=len(df), freq="D")
    fetch_fn = _make_fetch_fn({"BTC-USD": df})

    summary = run_once(
        strategies=["donchian"], run_date=saturday, state=state, trade_logger=trade_logger,
        fetch_fn=fetch_fn, markets={"crypto": ["BTC-USD"]}, verbose=False,
    )
    assert summary["results"][0].action != "skip_weekend"


def test_dry_run_makes_no_state_or_log_changes(state, trade_logger):
    df = _breakout_df()
    run_date = df.index[-1].date()
    fetch_fn = _make_fetch_fn({"FAKE-USD": df})

    run_once(
        strategies=["donchian"], run_date=run_date, dry_run=True,
        state=state, trade_logger=trade_logger, fetch_fn=fetch_fn,
        markets={"crypto": ["FAKE-USD"]}, verbose=False,
    )

    assert state.get_position("FAKE-USD", "donchian") is None
    assert state.get_equity() == 10_000.0
    assert state.get_last_processed_date("FAKE-USD", "donchian") is None
    assert not trade_logger.trades_jsonl_path.exists()
    assert not trade_logger.equity_jsonl_path.exists()


def test_state_and_idempotency_persist_across_separate_runner_instances(tmp_path):
    """Bir 'calistirma' (state+logger kapatilir) sonrasi YENI orneklerle
    tekrar calistirildiginda hem pozisyon hem de idempotency korunmali -
    programi kapatip acmanin runner uzerindeki karsiligi."""
    db_path = tmp_path / "state.db"
    log_dir = tmp_path / "logs"

    df = _breakout_df()
    run_date = df.index[-1].date()
    fetch_fn = _make_fetch_fn({"FAKE-USD": df})

    state1 = PaperTradingState(db_path=db_path, initial_capital=10_000.0)
    logger1 = PaperTradingLogger(log_dir=log_dir)
    run_once(
        strategies=["donchian"], run_date=run_date, state=state1, trade_logger=logger1,
        fetch_fn=fetch_fn, markets={"crypto": ["FAKE-USD"]}, verbose=False,
    )
    state1.close()

    state2 = PaperTradingState(db_path=db_path, initial_capital=10_000.0)
    logger2 = PaperTradingLogger(log_dir=log_dir)
    summary2 = run_once(
        strategies=["donchian"], run_date=run_date, state=state2, trade_logger=logger2,
        fetch_fn=fetch_fn, markets={"crypto": ["FAKE-USD"]}, verbose=False,
    )

    assert summary2["results"][0].action == "skip_already_processed"
    pos = state2.get_position("FAKE-USD", "donchian")
    assert pos is not None
    assert pos.direction == 1
    state2.close()


def test_no_signal_when_flat_range(state, trade_logger):
    df = _no_signal_df()
    run_date = df.index[-1].date()
    fetch_fn = _make_fetch_fn({"FAKE-USD": df})

    summary = run_once(
        strategies=["donchian"], run_date=run_date, state=state, trade_logger=trade_logger,
        fetch_fn=fetch_fn, markets={"crypto": ["FAKE-USD"]}, verbose=False,
    )
    assert summary["results"][0].action == "no_signal"
    assert state.get_position("FAKE-USD", "donchian") is None


def test_dry_run_with_no_existing_db_creates_no_file(tmp_path, trade_logger):
    """--dry-run, henuz hic state.db yokken diske HICBIR SEY yazmamali
    (bellek-ici fallback kullanilmali)."""
    db_path = tmp_path / "state.db"
    assert not db_path.exists()

    df = _breakout_df()
    run_date = df.index[-1].date()
    fetch_fn = _make_fetch_fn({"FAKE-USD": df})
    dry_state = PaperTradingState(db_path=db_path, initial_capital=10_000.0, read_only=True)

    summary = run_once(
        strategies=["donchian"], run_date=run_date, dry_run=True,
        state=dry_state, trade_logger=trade_logger, fetch_fn=fetch_fn,
        markets={"crypto": ["FAKE-USD"]}, verbose=False,
    )

    assert summary["results"][0].action == "entry_long"  # ne yapilacagi dogru hesaplanmis
    dry_state.close()
    assert not db_path.exists()  # ama diske hicbir sey yazilmamis


def test_real_run_creates_timestamped_backup(state, trade_logger):
    df = _no_signal_df()
    run_date = df.index[-1].date()
    fetch_fn = _make_fetch_fn({"FAKE-USD": df})
    backups_dir = state.db_path.parent / "backups"

    assert not backups_dir.exists()
    run_once(
        strategies=["donchian"], run_date=run_date, dry_run=False,
        state=state, trade_logger=trade_logger, fetch_fn=fetch_fn,
        markets={"crypto": ["FAKE-USD"]}, verbose=False,
    )
    assert backups_dir.exists()
    assert len(list(backups_dir.glob("*.db"))) == 1


def test_dry_run_does_not_create_backup(state, trade_logger):
    df = _no_signal_df()
    run_date = df.index[-1].date()
    fetch_fn = _make_fetch_fn({"FAKE-USD": df})
    backups_dir = state.db_path.parent / "backups"

    run_once(
        strategies=["donchian"], run_date=run_date, dry_run=True,
        state=state, trade_logger=trade_logger, fetch_fn=fetch_fn,
        markets={"crypto": ["FAKE-USD"]}, verbose=False,
    )
    assert not backups_dir.exists()


def test_stop_proximity_warning_not_sent_when_far_from_stop(state, trade_logger, monkeypatch):
    sent_messages = []
    monkeypatch.setattr(runner_module, "send_telegram_message", lambda text: sent_messages.append(text))

    state.open_position(
        "FAKE-USD", "price_action", direction=1, entry_date=dt.date(2019, 1, 1),
        entry_price=100.0, stop_price=90.0, size=1.0,
    )
    df = _hold_far_from_stop_df()
    run_date = df.index[-1].date()
    fetch_fn = _make_fetch_fn({"FAKE-USD": df})

    summary = run_once(
        strategies=["price_action"], run_date=run_date, dry_run=False,
        state=state, trade_logger=trade_logger, fetch_fn=fetch_fn,
        markets={"crypto": ["FAKE-USD"]}, verbose=False,
    )

    assert summary["results"][0].action == "hold"
    # Proksimite uyarisi gonderilmedi (uzak) ama gunluk islem formu ozeti
    # HER GUN acik pozisyon varken gonderilir (bkz. action_sheet.py) - o
    # yuzden liste TAMAMEN bos degil, sadece proksimite metni icermiyor.
    assert not any("stop'a yaklasiyor" in msg for msg in sent_messages)
    assert state.get_stop_warning_date("FAKE-USD", "price_action") is None


def test_stop_proximity_warning_sent_when_near_stop(state, trade_logger, monkeypatch):
    sent_messages = []
    monkeypatch.setattr(runner_module, "send_telegram_message", lambda text: sent_messages.append(text))

    state.open_position(
        "FAKE-USD", "price_action", direction=1, entry_date=dt.date(2019, 1, 1),
        entry_price=101.0, stop_price=99.8, size=1.0,
    )
    df = _hold_near_stop_df()
    run_date = df.index[-1].date()
    fetch_fn = _make_fetch_fn({"FAKE-USD": df})

    summary = run_once(
        strategies=["price_action"], run_date=run_date, dry_run=False,
        state=state, trade_logger=trade_logger, fetch_fn=fetch_fn,
        markets={"crypto": ["FAKE-USD"]}, verbose=False,
    )

    assert summary["results"][0].action == "hold"
    # Iki mesaj beklenir: proksimite uyarisi + HER GUN gonderilen gunluk
    # islem formu ozeti (bkz. action_sheet.py) - ikisi BAGIMSIZ mekanizmalar.
    assert len(sent_messages) == 2
    proximity_messages = [m for m in sent_messages if "stop'a yaklasiyor" in m]
    assert len(proximity_messages) == 1
    assert "FAKE-USD" in proximity_messages[0]
    assert state.get_stop_warning_date("FAKE-USD", "price_action") == run_date


def test_stop_proximity_warning_not_repeated_same_day(state, trade_logger, monkeypatch):
    sent_messages = []
    monkeypatch.setattr(runner_module, "send_telegram_message", lambda text: sent_messages.append(text))

    state.open_position(
        "FAKE-USD", "price_action", direction=1, entry_date=dt.date(2019, 1, 1),
        entry_price=101.0, stop_price=99.8, size=1.0,
    )
    df = _hold_near_stop_df()
    run_date = df.index[-1].date()
    fetch_fn = _make_fetch_fn({"FAKE-USD": df})

    # Bugun zaten uyarilmis durumu simule et (ayni pozisyon icin idempotency)
    state.set_stop_warning_date("FAKE-USD", "price_action", run_date)

    summary = run_once(
        strategies=["price_action"], run_date=run_date, dry_run=False,
        state=state, trade_logger=trade_logger, fetch_fn=fetch_fn,
        markets={"crypto": ["FAKE-USD"]}, verbose=False,
    )

    assert summary["results"][0].action == "hold"
    # Proksimite uyarisi ayni gun tekrar GONDERILMEZ (idempotency) ama
    # gunluk islem formu ozeti yine de gonderilir (bkz. action_sheet.py).
    assert not any("stop'a yaklasiyor" in msg for msg in sent_messages)


# -- M3: coklu strateji + portfoy tahsisi --------------------------------


def test_two_strategies_same_symbol_independent_positions(state, trade_logger):
    """Ayni sembolde iki strateji BAGIMSIZ pozisyon acabilmeli (kompozit anahtar)."""
    df = _breakout_df()
    run_date = df.index[-1].date()
    fetch_fn = _make_fetch_fn({"FAKE-USD": df})

    summary = run_once(
        strategies=["donchian", "price_action"], run_date=run_date, state=state, trade_logger=trade_logger,
        fetch_fn=fetch_fn, markets={"crypto": ["FAKE-USD"]}, verbose=False,
    )

    actions = {r.strategy: r.action for r in summary["results"]}
    assert actions["donchian"] in ("entry_long", "skip_risk_budget")
    assert actions["price_action"] in ("entry_long", "skip_risk_budget")
    # En az biri gercekten acilmis olmali (veri identik oldugundan ikisi de
    # sinyal uretir; portfoy tahsisi ikisini de agirliklandirabilir)
    positions = state.list_open_positions()
    assert len(positions) >= 1


def test_candidate_rejected_when_gross_budget_exhausted(state, trade_logger):
    """Mevcut acik pozisyonlar zaten %100 brut kaldiraci tuketmisse, yeni
    adaylar ACILMAMALI (skip_risk_budget) - M3'un sert korelasyon/kaldirac kosulu."""
    # Mevcut pozisyon: TUM equity'i (10.000) kaplayan buyuk bir maruziyet
    state.open_position(
        "EXISTING-USD", "donchian", direction=1, entry_date=dt.date(2024, 1, 1),
        entry_price=100.0, stop_price=95.0, size=100.0,  # 100*100 = 10.000 = %100 equity
    )

    df = _breakout_df()
    run_date = df.index[-1].date()
    fetch_fn = _make_fetch_fn({"EXISTING-USD": df, "NEW-USD": df})

    summary = run_once(
        strategies=["donchian"], run_date=run_date, state=state, trade_logger=trade_logger,
        fetch_fn=fetch_fn, markets={"crypto": ["EXISTING-USD", "NEW-USD"]}, verbose=False,
    )

    new_result = next(r for r in summary["results"] if r.symbol == "NEW-USD")
    assert new_result.action == "skip_risk_budget"
    assert state.get_position("NEW-USD", "donchian") is None


def test_correlated_candidates_capped_by_cluster_exposure(state, trade_logger):
    """Iki adayin fiyat serisi neredeyse ozdes (yuksek korelasyonlu) ise,
    korelasyon-kume kisiti toplam maruziyetlerini sinirlamali (M2 entegrasyonu)."""
    df_a = _breakout_df()
    df_b = _breakout_df()  # deterministik uretim -> df_a ile ozdes/yuksek korelasyonlu
    run_date = df_a.index[-1].date()
    fetch_fn = _make_fetch_fn({"SYM-A": df_a, "SYM-B": df_b})

    run_once(
        strategies=["donchian"], run_date=run_date, state=state, trade_logger=trade_logger,
        fetch_fn=fetch_fn, markets={"crypto": ["SYM-A", "SYM-B"]}, verbose=False,
    )

    positions = state.list_open_positions()
    total_exposure = sum(abs(p.size * p.entry_price) for p in positions)
    # RISK_MAX_SECTOR_EXPOSURE=0.4 -> ayni kumedeki toplam maruziyet
    # equity'nin %40'ini (kucuk bir toleransla) asmamali
    assert total_exposure <= 10_000.0 * 0.4 + 1e-6


def test_cross_day_cluster_exposure_limits_new_candidate(state, trade_logger):
    """M7 - dun (baska bir calistirmada) acilmis, YUKSEK KORELASYONLU bir
    pozisyon zaten kume butcesinin cogunu tuketmisse, BUGUNKU yeni bir aday
    (ayni kumede) o kalan kucuk butceyle SINIRLANMALI - M3'un birakip M7'ye
    devrettigi capraz-gun kume takibi."""
    # Mevcut (dunku) pozisyon equity'nin %35'ini kapliyor (RISK_MAX_SECTOR_EXPOSURE=0.4,
    # kalan kume butcesi ~%5 olmali)
    state.open_position(
        "EXISTING-USD", "donchian", direction=1, entry_date=dt.date(2024, 1, 1),
        entry_price=100.0, stop_price=95.0, size=35.0,  # 35*100=3500 = equity'nin %35'i
    )

    existing_df = _breakout_df()
    new_df = _breakout_df()  # deterministik uretim -> existing_df ile ozdes/yuksek korelasyonlu
    run_date = existing_df.index[-1].date()
    fetch_fn = _make_fetch_fn({"EXISTING-USD": existing_df, "NEW-USD": new_df})

    run_once(
        strategies=["donchian"], run_date=run_date, state=state, trade_logger=trade_logger,
        fetch_fn=fetch_fn, markets={"crypto": ["EXISTING-USD", "NEW-USD"]}, verbose=False,
    )

    new_pos = state.get_position("NEW-USD", "donchian")
    if new_pos is not None:
        new_exposure = abs(new_pos.size * new_pos.entry_price) / 10_000.0
        # Capraz-gun kume takibi OLMASAYDI yeni aday tek basina RISK_MAX_POSITION_SIZE'a
        # (0.2) kadar acilabilirdi; kume butcesi ZATEN %35 tuketildigi icin
        # KALAN ~%5'i asmamali (kucuk bir tolerans).
        assert new_exposure <= 0.4 - 0.35 + 0.02


# -- Net yonlu maruziyet kisiti (M2 eki, risk/net_exposure.py) -------------


def test_net_exposure_limit_caps_new_candidate_same_direction_as_existing(state, trade_logger):
    """Mevcut acik pozisyonlar ZATEN buyuk oranda SHORT'a yaslanmissa
    (net maruziyet sinira yakin), AYNI yonde (SHORT) yeni bir aday KUCUK
    bir boyutla acilmali/reddedilmeli - farkli kumede olsa bile."""
    # equity 10_000, mevcut SHORT pozisyon net maruziyetin %45'ini kapliyor
    # (MAX_NET_EXPOSURE_PCT=0.5 -> yeni SHORT adaya kalan pay ~%5)
    state.open_position(
        "EXISTING-SHORT", "donchian", direction=-1, entry_date=dt.date(2024, 1, 1),
        entry_price=100.0, stop_price=105.0, size=45.0,  # 45*100=4500 = equity'nin %45'i
    )

    existing_df = make_flat_range_df(n=70, price=100.0, half_range=1.0, volume=1000.0)
    new_df = _short_breakout_df()  # farkli/korelasyonsuz fiyat serisi, YENI bir SHORT sinyali
    run_date = new_df.index[-1].date()
    fetch_fn = _make_fetch_fn({"EXISTING-SHORT": existing_df, "NEW-SHORT": new_df})

    run_once(
        strategies=["donchian"], run_date=run_date, state=state, trade_logger=trade_logger,
        fetch_fn=fetch_fn, markets={"crypto": ["EXISTING-SHORT", "NEW-SHORT"]}, verbose=False,
    )

    positions = {p.symbol: p for p in state.list_open_positions()}
    equity = 10_000.0
    if "NEW-SHORT" in positions:
        new_exposure = abs(positions["NEW-SHORT"].size * positions["NEW-SHORT"].entry_price) / equity
        # Kalan net-maruziyet butcesi ~%5 - yeni pozisyon buna gore KUCUK olmali
        assert new_exposure <= 0.10 + 0.02


def test_net_exposure_limit_allows_opposite_direction_candidate(state, trade_logger):
    """Mevcut pozisyonlar SHORT'a yaslanmis olsa bile, TERS yonde (LONG)
    bir aday net maruziyeti DENGELEDIGI icin kisitlanmamali.

    NOT: EXISTING-SHORT ve NEW-LONG icin BILEREK FARKLI (korelasyonsuz)
    fiyat serileri kullanilir - ikisi de ayni duz taban veriyi paylassaydi
    (make_flat_range_df) mukemmel korelasyonlu (1.0) cikip AYNI kume
    kisitina (M7a, yonsuz/mutlak maruziyet takibi) takilirlardi; bu,
    net-maruziyet kisitinden BAGIMSIZ, ayrica not edilen bir gozlem
    (kume takibinin yon-farkinda olmamasi) - bu testin odagi DEGIL."""
    state.open_position(
        "EXISTING-SHORT", "donchian", direction=-1, entry_date=dt.date(2024, 1, 1),
        entry_price=100.0, stop_price=105.0, size=45.0,
    )

    existing_df = _uncorrelated_flat_df()
    new_df = _breakout_df()  # LONG sinyali (mevcut SHORT'un TERSI), KORELASYONSUZ bir taban veri
    run_date = new_df.index[-1].date()
    fetch_fn = _make_fetch_fn({"EXISTING-SHORT": existing_df, "NEW-LONG": new_df})

    summary = run_once(
        strategies=["donchian"], run_date=run_date, state=state, trade_logger=trade_logger,
        fetch_fn=fetch_fn, markets={"crypto": ["EXISTING-SHORT", "NEW-LONG"]}, verbose=False,
    )

    new_result = next(r for r in summary["results"] if r.symbol == "NEW-LONG")
    assert new_result.action == "entry_long"
    assert state.get_position("NEW-LONG", "donchian") is not None


def test_dry_run_does_not_mutate_last_processed_date_for_candidates(state, trade_logger):
    df = _breakout_df()
    run_date = df.index[-1].date()
    fetch_fn = _make_fetch_fn({"FAKE-USD": df})

    run_once(
        strategies=["donchian"], run_date=run_date, dry_run=True,
        state=state, trade_logger=trade_logger, fetch_fn=fetch_fn,
        markets={"crypto": ["FAKE-USD"]}, verbose=False,
    )
    assert state.get_last_processed_date("FAKE-USD", "donchian") is None


# -- M7: haftalik kalite filtresi (opsiyonel, varsayilan KAPALI) -----------


def test_conflicts_with_weekly_bias_none_never_filters():
    assert runner_module._conflicts_with_weekly_bias(1, None) is False
    assert runner_module._conflicts_with_weekly_bias(-1, None) is False


def test_conflicts_with_weekly_bias_matrix():
    assert runner_module._conflicts_with_weekly_bias(1, "down") is True
    assert runner_module._conflicts_with_weekly_bias(1, "up") is False
    assert runner_module._conflicts_with_weekly_bias(-1, "up") is True
    assert runner_module._conflicts_with_weekly_bias(-1, "down") is False


def test_weekly_bias_filter_disabled_by_default_allows_conflicting_entry(state, trade_logger):
    """weekly_bias_filter verilmezse (varsayilan False), haftalik trendle
    CELISEN bir kirilim yine de acilmali - mevcut davranis DEGISMEMELI."""
    df = _trend_then_breakout_df(weekly_step=-0.5, breakout_up=True)
    run_date = df.index[-1].date()
    fetch_fn = _make_fetch_fn({"FAKE-USD": df})

    summary = run_once(
        strategies=["donchian"], run_date=run_date, state=state, trade_logger=trade_logger,
        fetch_fn=fetch_fn, markets={"crypto": ["FAKE-USD"]}, verbose=False,
    )
    assert summary["results"][0].action == "entry_long"


def test_weekly_bias_filter_blocks_conflicting_entry_when_enabled(state, trade_logger):
    """weekly_bias_filter=True iken, haftalik dusus trendine RAGMEN gelen
    bir long kirilimi ELENMELI (skip_weekly_trend_filter), pozisyon acilmamali."""
    df = _trend_then_breakout_df(weekly_step=-0.5, breakout_up=True)
    run_date = df.index[-1].date()
    fetch_fn = _make_fetch_fn({"FAKE-USD": df})

    summary = run_once(
        strategies=["donchian"], run_date=run_date, state=state, trade_logger=trade_logger,
        fetch_fn=fetch_fn, markets={"crypto": ["FAKE-USD"]}, verbose=False,
        weekly_bias_filter=True,
    )
    assert summary["results"][0].action == "skip_weekly_trend_filter"
    assert state.get_position("FAKE-USD", "donchian") is None


def test_weekly_bias_filter_allows_aligned_entry_when_enabled(state, trade_logger):
    """weekly_bias_filter=True iken, haftalik YUKSELIS trendiyle UYUMLU bir
    long kirilimi normal sekilde acilmali."""
    df = _trend_then_breakout_df(weekly_step=0.5, breakout_up=True)
    run_date = df.index[-1].date()
    fetch_fn = _make_fetch_fn({"FAKE-USD": df})

    summary = run_once(
        strategies=["donchian"], run_date=run_date, state=state, trade_logger=trade_logger,
        fetch_fn=fetch_fn, markets={"crypto": ["FAKE-USD"]}, verbose=False,
        weekly_bias_filter=True,
    )
    assert summary["results"][0].action == "entry_long"
    assert state.get_position("FAKE-USD", "donchian") is not None


def test_weekly_bias_filter_marks_idempotency_for_blocked_candidate(state, trade_logger):
    df = _trend_then_breakout_df(weekly_step=-0.5, breakout_up=True)
    run_date = df.index[-1].date()
    fetch_fn = _make_fetch_fn({"FAKE-USD": df})

    run_once(
        strategies=["donchian"], run_date=run_date, state=state, trade_logger=trade_logger,
        fetch_fn=fetch_fn, markets={"crypto": ["FAKE-USD"]}, verbose=False,
        weekly_bias_filter=True,
    )
    assert state.get_last_processed_date("FAKE-USD", "donchian") == run_date
