# RegimeForgeEA

[![Python tests](https://github.com/BerryUIKI/RegimeForgeEA/actions/workflows/python-tests.yml/badge.svg)](https://github.com/BerryUIKI/RegimeForgeEA/actions/workflows/python-tests.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
![MQL5](https://img.shields.io/badge/Execution-MQL5-167AC6)
![研究状态](https://img.shields.io/badge/Live%20candidate-Not%20yet%20qualified-BA3D3D)

RegimeForgeEA 是一个模块化、按行情状态切换策略的自动交易框架，包含 MQL5 EA
和 Python 研究回测器。项目不绑定任何交易品种：当前附带的第一套策略是 XAUUSD
M5 趋势突破研究候选，但执行和风险架构本身与黄金无关。

> [!WARNING]
> 本软件仅用于研究与教育。交易具有重大风险。启用真实交易前，必须验证品种合约、
> 交易成本及策略行为。

## 实盘研究状态

成交量依赖型候选不再适用于实盘研究路径，因为不同黄金交易场所与经纪商的成交量口径
并不一致。第一轮价格型 M5 多空研究已包含 ATR 止损、止盈、移动止损、时间退出、
风险仓位和账户级锁；所有预先定义候选均在训练期失败。当前没有合格的实盘候选。

被拒绝的价格型家族使用如下已收盘 K 线公式：

$$r_k(t)=\frac{C_t}{C_{t-k}}-1$$

$$Long(t)=T_{up}(t)\land r_k(t)\le q_L(t),\qquad Short(t)=T_{down}(t)\land r_k(t)\ge q_U(t)$$

其中 $T_{up}$ 与 $T_{down}$ 是已完成 H1 的 EMA 趋势状态。它在实盘风格订单级测试中
被拒绝；这正是研究门槛的预期作用。详见[价格型详细拒绝报告](reports/Price_Only_Live_Candidate_Research_Detailed.md)
及其 [PDF](reports/Price_Only_Live_Candidate_Research_Detailed.pdf)。

独立的[时段突破研究](reports/Session_Breakout_Candidate_Research.md)也在相同的
价格型风险和退出标准下未通过训练；它作为负面证据保留，并非 EA 候选。

独立的 [ATR 压缩突破研究](reports/Compression_Breakout_Candidate_Research.md)同样
未通过训练。因此，在当前公开代理数据和实盘风格成本假设下，三个不同的价格型家族
均保持淘汰状态。

此前通过的成交量代理候选仅为研究留档，不能视为实盘建议。

## 功能

- 趋势、震荡、高波动和未知行情分类
- 使用统一信号接口的可插拔策略模块
- 集中管理仓位计算、订单执行和持仓
- ATR 止损、止盈和移动止损
- 点差、单日亏损和峰值回撤开仓锁定
- 仅使用已收盘 K 线，避免未来数据
- 与第一套 EA 策略对齐的 Python 事件回测器
- 用于候选评估、仅限研究的 Bollinger/RSI 震荡模型

当前 EA 只管理趋势突破研究候选。由于公开数据研究尚未发现可部署的策略，默认
禁止新开仓（`InpEnableNewEntries=false`）。EA 中震荡与高波动行情仍然保持空仓。

## 研究状态

已使用预先固定的候选与时间切分进行测试：2021–2023 训练、2024 验证、2025 最终
留出。大多数候选已淘汰；此前通过的代理候选依赖成交量，已排除在实盘路径之外。当前
价格型候选也在训练期淘汰，因此没有任何价格型规则默认启用。

- [趋势候选研究](reports/Trend_Candidate_Research.md)：8 个 M15/M30/H1
  EMA/ADX/Donchian 候选，均未通过训练门槛。
- [震荡候选研究](reports/Range_Candidate_Research.md)：8 个 M15/M30/H1
  Bollinger/RSI 候选，均未通过训练门槛。
- [高频候选研究](reports/High_Frequency_Candidate_Research.md)：使用已收盘
  H1/H4 趋势过滤的 M5 回撤候选，均未通过订单级回测。
- [日内因子筛选](reports/Intraday_Factor_Screen.md)：计入成本的 M5 因子筛选；
  初始反转规则在订单级转换后未通过。
- [成交量反转订单研究](reports/Volume_Reversal_Candidate_Research.md)：固定时间
  M5 退出和 ATR 止损候选，均未通过训练门槛。
- [M5 订单流因子筛选](reports/Order_Flow_Factor_Screen.md)及其
  [订单级结果](reports/Order_Flow_Absorption_Backtest.md)：表面上的事件级吸收
  效应在纳入下一根成交与非重叠持仓后失败。
- [M1 订单流因子筛选](reports/Order_Flow_Factor_Screen_1m.md)及其
  [订单级结果](reports/Order_Flow_Absorption_Backtest_1m.md)：一分钟、
  1,542,455 根柱的筛选在训练和验证中出现事件级正均值，但预先固定的可成交规则
  在三个样本期均失败；因此已淘汰，不会接入 EA。
- [M5 可成交因子网格](reports/M5_Executable_Factor_Grid.md)及其
  [预先固定的留出检验](reports/M5_Volume_Reversal_Holdout.md)：成交量确认的
  三根收益反转候选在公开 PAXGUSDT 代理的 2021–2023 训练、2024 验证和 2025
  留出集均通过；在经纪商原生 XAUUSD Bid/Ask 验证前，它仍仅限研究，不会接入 EA。
  完整的[正式研究报告](reports/M5_Volume_Reversal_Research_Report.md)及 PDF 也已
  随仓库提供。

Python 中的震荡模型仅供研究，尚未实现到 MQL5。启用 EA 新开仓前，仍需要券商
原生 XAUUSD bid/ask 数据、走样本外验证和模拟盘前向测试。

下载公开数据后，可使用下列固定候选研究命令复现结果：

```bash
python scripts/research_trend_candidates.py \
  data/derived/PAXGUSDT_5m_2021_2025_weekdays.csv \
  --output-json outputs/trend_candidate_research.json \
  --report reports/Trend_Candidate_Research.md

python scripts/research_range_candidates.py \
  data/derived/PAXGUSDT_5m_2021_2025_weekdays.csv \
  --output-json outputs/range_candidate_research.json \
  --report reports/Range_Candidate_Research.md

python scripts/download_binance_aggtrades.py \
  --symbol PAXGUSDT --start 2021-01 --end 2025-12 \
  --bar-interval 1min --weekdays-only \
  --output data/derived/PAXGUSDT_order_flow_1m_2021_2025_weekdays.csv

python scripts/explore_order_flow_factors.py \
  data/derived/PAXGUSDT_order_flow_1m_2021_2025_weekdays.csv \
  data/derived/PAXGUSDT_order_flow_1m_2021_2025_weekdays.csv \
  --bar-minutes 1 --horizons 5,10,20,30 \
  --output outputs/order_flow_factor_screen_1m.csv \
  --report reports/Order_Flow_Factor_Screen_1m.md

python scripts/research_m5_order_flow_grid.py \
  data/derived/PAXGUSDT_5m_2021_2025_weekdays.csv \
  data/derived/PAXGUSDT_order_flow_5m_2021_2025.csv \
  --output outputs/m5_executable_factor_grid.csv \
  --report reports/M5_Executable_Factor_Grid.md

python scripts/research_order_flow_absorption.py \
  data/derived/PAXGUSDT_5m_2021_2025_weekdays.csv \
  data/derived/PAXGUSDT_order_flow_5m_2021_2025.csv \
  --factor volume_return_3_reversal --bar-minutes 5 --hold-bars 24 \
  --side long --session-hours 0-23 \
  --trades outputs/m5_volume_reversal_holdout_trades.csv \
  --report reports/M5_Volume_Reversal_Holdout.md
```

## 最新公开数据回测

未经优化的默认策略已使用 2021–2025 年 375,413 根工作日 `PAXGUSDT` M5 K 线
进行回测。数据来自 Binance Data Vision 月度归档，每个文件均使用发布方提供的
SHA-256 校验值验证。

| 指标 | 启用风控 | 连续策略诊断 |
|---|---:|---:|
| 总收益率 | -11.55% | -98.87% |
| 最大回撤 | 12.35% | 98.90% |
| 交易次数 | 44 | 2,054 |
| 胜率 | 22.73% | 24.49% |
| Profit Factor | 0.47 | 0.28 |

启用风控的回测在 2021 年 1 月 11 日触发峰值回撤锁，此后停止开仓。连续诊断结果
说明当前默认策略本身不可用。PAXGUSDT 只是与黄金挂钩的公开代理数据，并非券商
XAUUSD 报价，因此不能把结果描述为实盘验证。

请阅读[完整回测报告](reports/PAXGUSDT_2021_2025.md)并查看
[数据清单](reports/PAXGUSDT_2021_2025_data_manifest.json)。

## MQL5 文件结构

```text
MQL5/
├── Experts/RegimeForgeEA.mq5
├── Experts/RegimeForgeVolumeReversalEA.mq5
└── Include/RegimeForge/
    ├── StrategyTypes.mqh
    └── TrendBreakoutStrategy.mqh
```

将文件复制到 MT5 数据目录下 `MQL5` 的对应位置，然后使用 MetaEditor 编译
`Experts/RegimeForgeEA.mq5`。EA 使用 `_Symbol`，应挂载到需要交易的品种图表。

### M5 成交量反转测试 EA

`Experts/RegimeForgeVolumeReversalEA.mq5` 是代理数据研究候选的独立实现。
在 MT5 策略测试器中将其挂载到 XAUUSD M5 图表，使用经纪商真实点差与 tick 设置；
仅为测试将 `InpEnableNewEntries=true`。候选核心参数为
`InpReturnLookbackBars=3`、`InpQuantileBars=5760`、
`InpMinimumVolumeRatio=1.50` 和 `InpHoldBars=24`。EA 使用 MT5 tick volume，
它与代理数据的交易所成交量不同；这正是经纪商原生测试将高于代理结果的原因。

保守的自适应测试档已作为默认值启用：`InpFixedLots=0.02`、仅在已完成 H1 满足
`EMA(20) > EMA(50)` 时交易、2% 日内已实现亏损锁，以及连续四笔亏损后冷却 12 根
M5。其代理数据[自适应回测](reports/M5_Adaptive_Volume_Reversal_Backtest.md)降低了
2025 最大回撤，但并未改善每个历史样本；必须在 MT5 中独立验证。
详细的[自适应研究论文](reports/M5_Adaptive_Volume_Reversal_Research_Paper.md)及其
[PDF](reports/M5_Adaptive_Volume_Reversal_Research_Paper.pdf)记录了选型限制、
风险分析和专业测试流程。
完整的英文审计级说明见[详细报告](reports/M5_Adaptive_Volume_Reversal_Detailed_Report.md)
及其[详细 PDF](reports/M5_Adaptive_Volume_Reversal_Detailed_Report.pdf)。

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

复现公开数据回测所需命令见[回测报告](reports/PAXGUSDT_2021_2025.md)。
原始行情和运行输出不会提交到 Git；下载器会从经过校验的公开归档重新构建它们。

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
在策略通过文档化门槛前，EA 默认禁止新开仓。

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

策略、数据和验证要求见 [CONTRIBUTING.md](CONTRIBUTING.md)。安全问题请按
[SECURITY.md](SECURITY.md) 的流程私下报告，不要公开提交 issue。

## 许可证

[MIT](LICENSE)
