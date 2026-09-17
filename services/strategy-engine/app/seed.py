"""
预置策略元数据（DB seed）
启动时幂等写入，保证前端策略列表开箱即有业界策略
"""
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from common import get_logger
from common.models.strategy import Strategy

logger = get_logger("strategy-engine")

SEED_STRATEGIES: List[Dict[str, Any]] = [
    # ---- 趋势 ----
    {"code": "boll_breakout", "name": "布林带突破", "type": "technical",
     "description": "收盘突破布林上轨买入、跌破下轨卖出，捕捉趋势启动",
     "params": {"boll_period": 20, "std": 2.0, "code": "600000", "position_size": 100}},
    {"code": "turtle", "name": "海龟交易", "type": "technical",
     "description": "唐奇安通道20日上轨突破买入，10日下轨离场，ATR 计算仓位与止损",
     "params": {"entry_period": 20, "exit_period": 10, "atr_period": 14, "code": "600000"}},
    {"code": "adx_trend", "name": "ADX趋势过滤", "type": "technical",
     "description": "ADX 大于阈值且方向向上时顺势买入，趋势转弱卖出",
     "params": {"adx_period": 14, "threshold": 25, "code": "600000"}},
    {"code": "triple_ma", "name": "三均线趋势", "type": "technical",
     "description": "5/20/60 多头排列买入，空头排列卖出",
     "params": {"fast": 5, "mid": 20, "slow": 60, "code": "600000"}},
    # ---- 量价 ----
    {"code": "volume_breakout", "name": "放量突破", "type": "technical",
     "description": "突破20日高点且成交量放大 2 倍以上买入",
     "params": {"high_period": 20, "vol_ratio": 2.0, "code": "600000"}},
    {"code": "vol_price_up", "name": "量价齐升", "type": "technical",
     "description": "价格与成交量同步创 N 日新高时买入",
     "params": {"lookback": 20, "code": "600000"}},
    {"code": "obv_divergence", "name": "OBV 背离", "type": "technical",
     "description": "价格创新高而 OBV 未创新高（顶背离）卖出",
     "params": {"lookback": 20, "code": "600000"}},
    # ---- 均值回归 ----
    {"code": "boll_meanrev", "name": "布林回归", "type": "technical",
     "description": "触及布林下轨买入、上轨卖出、中轨止盈",
     "params": {"boll_period": 20, "std": 2.0, "code": "600000"}},
    {"code": "rsi_extreme", "name": "RSI 极限回归", "type": "technical",
     "description": "RSI 低于 20 超卖买入、高于 80 超买卖出",
     "params": {"rsi_period": 14, "oversold": 20, "overbought": 80, "code": "600000"}},
    # ---- K线形态 ----
    {"code": "hammer", "name": "锤子线", "type": "technical",
     "description": "下跌末段出现长下影线锤子线形态买入",
     "params": {"body_ratio": 2.0, "lookback": 20, "code": "600000"}},
    {"code": "engulfing", "name": "吞没形态", "type": "technical",
     "description": "低位阳包阴买入、高位阴包阳卖出",
     "params": {"lookback": 20, "code": "600000"}},
    {"code": "doji_reversal", "name": "十字星反转", "type": "technical",
     "description": "高位十字星卖出、低位十字星买入",
     "params": {"doji_tolerance": 0.1, "lookback": 20, "code": "600000"}},
    {"code": "gap_window", "name": "跳空缺口", "type": "technical",
     "description": "向上跳空且当日收阳不全回补时买入",
     "params": {"gap_ratio": 0.01, "code": "600000"}},
    # ---- 多因子 ----
    {"code": "momentum_factor", "name": "动量因子", "type": "factor",
     "description": "多周期加权收益率打分，超过阈值买入",
     "params": {"lookbacks": [10, 20, 60], "threshold": 0.05, "code": "600000"}},
    {"code": "low_volatility", "name": "低波动因子", "type": "factor",
     "description": "年化波动率低于阈值时买入，追求稳健",
     "params": {"vol_period": 20, "max_vol": 0.25, "code": "600000"}},
    {"code": "multi_factor", "name": "综合多因子", "type": "factor",
     "description": "动量 + 趋势 + 量能综合评分择时",
     "params": {"lookback": 20, "buy_threshold": 0.6, "sell_threshold": -0.3, "code": "600000"}},
]


def seed_strategies(db: Session) -> int:
    """幂等写入预置策略，返回新增条数"""
    inserted = 0
    for item in SEED_STRATEGIES:
        exists = db.query(Strategy).filter(Strategy.code == item["code"]).first()
        if exists:
            continue
        db.add(Strategy(
            name=item["name"],
            code=item["code"],
            type=item["type"],
            description=item["description"],
            params=item["params"],
            status="active",
        ))
        inserted += 1
    db.commit()
    if inserted:
        logger.info(f"Seeded {inserted} preloaded strategies")
    return inserted