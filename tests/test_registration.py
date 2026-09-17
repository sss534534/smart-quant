import sys

sys.path.insert(0, "services/strategy-engine")

from strategies.factory import StrategyFactory
from strategies.builtin import register_strategies


def test_all_preloaded_strategies_registered():
    register_strategies()
    names = set(StrategyFactory.get_all().keys())
    expected = {
        "dual_ma", "rsi_mean_reversion", "macd",
        "boll_breakout", "turtle", "adx_trend", "triple_ma",
        "volume_breakout", "vol_price_up", "obv_divergence",
        "boll_meanrev", "rsi_extreme", "hammer", "engulfing",
        "doji_reversal", "gap_window",
        "momentum_factor", "low_volatility", "multi_factor",
    }
    missing = expected - names
    assert not missing, f"missing strategies: {missing}"