# 预置业界量化策略集 设计文档

日期：2026-09-17
状态：已批准（A+C 方案）

## 目标

预置一批业界常用的量化策略，覆盖趋势跟踪、均值回归、量价分析、多因子选股、K线形态识别五大类，并通过风控 mixin 增强。采用方案 A（策略类内嵌风控）+ 方案 C（DB 预置元数据），分批交付。

## 现状

- 已有 3 个基础策略：`dual_ma` / `rsi_mean_reversion` / `macd`
- 指标库已有：SMA/EMA/WMA/MACD/RSI/KDJ/BOLL/ATR/OBV/VWAP/MFI/ADX/CCI/布林带宽/历史波动率/支撑阻力/金叉死叉
- 策略类继承 `BaseStrategy`，实现 `initialize(params)` + `on_bar(bar)`
- 引擎 `feed.py` 每 30 秒喂 bar，当前 `provider="mock"`

## 架构

### 组件

1. **新策略类**（`services/strategy-engine/strategies/`）
   - 复用现有 `BaseStrategy` / `StrategyFactory` / 指标库
   - 全部保持单标的 `on_bar` 回调，与引擎架构零冲突
2. **RiskMixin**（新增 `strategies/risk_mixin.py`）
   - ATR 动态止损、移动止盈、最大持仓/单笔比例
   - 可选注入策略类（默认开启）
3. **seed_strategies 预置**（新增 `strategies/seed.py` 或并入 router）
   - 启动时检查 `strategies` 表，为每个新策略插入元数据行
   - 幂等：已存在的 code 跳过
4. **feed 修复**：`feed.py` 中 `provider="mock"` → `provider="eastmoney"`

### 数据流

```
DB strategies 表 (seed 预置)
   → StrategyFactory.create(name, id, params)  [前端/手动触发启动]
   → feed_market_bars (eastmoney 行情) 
   → strategy.on_bar(bar) → 信号
   → manager.emit_signals → bridge → trading-service
```

## 策略清单

### 批1 趋势+量价（7个）

| code | 名称 | 逻辑 | 关键参数 |
|------|------|------|----------|
| `boll_breakout` | 布林带突破 | 收盘突破上轨买/跌破下轨卖 | boll_period=20, std=2 |
| `turtle` | 海龟交易 | 唐奇安20日上轨突破买/10日下轨卖，ATR仓位 | entry_period=20, exit_period=10, atr_period=14 |
| `adx_trend` | ADX趋势过滤 | ADX>25 且 +DI>-DI 买，金叉死叉 | adx_period=14, threshold=25 |
| `triple_ma` | 三均线 | 5/20/60 多头排列买，空头排列卖 | fast=5, mid=20, slow=60 |
| `volume_breakout` | 放量突破 | 突破20日高+量>5日均量2倍买 | high_period=20, vol_ratio=2.0 |
| `vol_price_up` | 量价齐升 | 价格量能同创新高买入 | lookback=20 |
| `obv_divergence` | OBV背离 | 价创新高量OBV未新高→顶背离卖 | obv_period=20 |

### 批2 均值回归+K线形态（6个）

| code | 名称 | 逻辑 | 关键参数 |
|------|------|------|----------|
| `boll_meanrev` | 布林回归 | 触及下轨买/上轨卖，中轨止盈 | boll_period=20, std=2 |
| `rsi_extreme` | RSI极限回归 | RSI<20买/RSI>80卖 | rsi_period=14, oversold=20, overbought=80 |
| `hammer` | 锤子线 | 下影线>2倍实体+低位买入 | body_ratio=2.0, lookback=20 |
| `engulfing` | 吞没形态 | 低位阳包阴买/高位阴包阳卖 | lookback=20 |
| `doji_reversal` | 十字星反转 | 高位十字星卖/低位十字星买 | doji_tolerance=0.1 |
| `gap_window` | 跳空缺口 | 向上跳空不回补买入 | gap_ratio=0.01 |

### 批3 多因子选股（3个）

| code | 名称 | 逻辑 | 关键参数 |
|------|------|------|----------|
| `momentum_factor` | 动量因子 | 多周期收益率加权评分>阈值买 | lookbacks=[10,20,60], threshold=0.05 |
| `low_volatility` | 低波动因子 | 20日收益率方差低买 | vol_period=20, percentile=30 |
| `multi_factor` | 综合评分 | 动量+低波+量能+趋势综合打分 | 见参数表 |

### 批4 风控增强

- `RiskMixin`：ATR 动态止损、移动止盈（max(ATR·k, 固定%)）、最大持仓/单笔比例
- 注入全部新策略（`risk_enabled=True` 默认）

## 实施步骤

1. 新增 `strategies/risk_mixin.py`
2. 新增各策略类文件（按批），在 `strategies/__init__.py` 与 `builtin.py`（或新 `preloaded.py`）注册
3. 新增 `seed_strategies()` 幂等预置 DB 元数据
4. `feed.py` 改 `provider="eastmoney"`
5. 前端 `Strategy.vue` 无需改（列表读取 DB，自动显示预置策略）
6. 测试：py_compile + 前端 build

## 验证

- `py_compile` 所有新策略文件
- `npm run build` 前端
- seed 幂等性：重复启动不产生重复行

## 风险

- 多因子/布林指标依赖足够历史数据（`_max_history_length=1000` 足够）
- RSI/MFI 除以零：沿用现有 `fillna` 处理