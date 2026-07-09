# RegimeForgeEA

RegimeForgeEA 是一个模块化、按行情状态切换策略的自动交易框架，包含 MQL5 EA
和 Python 研究回测器。项目不绑定任何交易品种：当前附带的第一套策略以 XAUUSD
M5 偏激进趋势突破为默认配置，但执行和风险架构本身与黄金无关。

> [!WARNING]
> 本软件仅用于研究与教育。交易具有重大风险。启用真实交易前，必须验证品种合约、
> 交易成本及策略行为。

## 功能

- 趋势、震荡、高波动和未知行情分类
- 使用统一信号接口的可插拔策略模块
- 集中管理仓位计算、订单执行和持仓
- ATR 止损、止盈和移动止损
- 点差、单日亏损和峰值回撤开仓锁定
- 仅使用已收盘 K 线，避免未来数据
- 与第一套 EA 策略对齐的 Python 事件回测器

目前 EA 只在趋势行情中开仓。震荡和高波动行情暂时保持空仓，后续将为它们增加
独立策略。

## MQL5 文件结构

```text
MQL5/
├── Experts/RegimeForgeEA.mq5
└── Include/RegimeForge/
    ├── StrategyTypes.mqh
    └── TrendBreakoutStrategy.mqh
```

将文件复制到 MT5 数据目录下 `MQL5` 的对应位置，然后使用 MetaEditor 编译
`Experts/RegimeForgeEA.mq5`。EA 使用 `_Symbol`，应挂载到需要交易的品种图表。

## Python 回测

安装依赖：

```bash
python -m pip install -r requirements.txt
```

运行：

```bash
python backtest/regime_forge_backtest.py data/XAUUSD_M5.csv \
  --output outputs/run_001
```

CSV 必须包含以下字段：

```text
time,open,high,low,close
```

可选字段包括 `tick_volume`、`real_volume` 和 `spread`。`spread` 按券商 points
解释。字段名不区分大小写，也支持 MT5 常见的 `Date`、`Time` 分列导出格式。

常用参数示例：

```bash
python backtest/regime_forge_backtest.py data/XAUUSD_M5.csv \
  --initial-equity 10000 \
  --risk-percent 1.0 \
  --spread-points 35 \
  --point 0.01 \
  --contract-size 100 \
  --output outputs/aggressive
```

每次回测会生成：

- `summary.json`：绩效和运行参数
- `trades.csv`：完整交易记录
- `equity.csv`：逐根 K 线的净值和行情状态

信号在 K 线收盘后计算，下一根 K 线开盘计入点差成交。OHLC 数据无法还原 K 线
内部的价格先后顺序，因此同一根 K 线同时触碰止损和止盈时，按止损先发生处理；
移动止损在收盘时更新。因此结果不会与 MT5 的逐 Tick 策略测试完全相同。

## 主要参数

- `InpRiskPerTradePct`：每笔交易风险占净值百分比，默认 `1.00%`
- `InpMaxDailyLossPct`：单日净值亏损开仓锁定
- `InpMaxDrawdownPct`：峰值净值回撤开仓锁定
- `InpMaxSpreadPoints`：允许开仓的最大点差
- `InpBreakoutBars`：突破回看长度
- `InpFastMAPeriod` / `InpSlowMAPeriod`：趋势方向
- `InpADXTrendLevel`：趋势强度门槛
- `InpStopATR` / `InpTakeProfitATR`：ATR 止损与止盈倍数

默认值有意设置为偏激进，不代表预期收益。未经券商数据验证，不应直接用于真实资金。

## 扩展策略

新增策略放在 `Include/RegimeForge/`，并统一输出 `TradeSignal`。主 EA 继续集中负责
仓位、订单、保护性止损和持仓管理。

计划增加：

1. 震荡行情：布林带或统计均值回归
2. 高波动行情：假突破过滤或事件后动量
3. 低波动行情：波动压缩突破
4. 组合层：在同一风控引擎下按行情状态分配策略

## 开发测试

```bash
python -m unittest discover -s tests -v
```

## 许可证

[MIT](LICENSE)

