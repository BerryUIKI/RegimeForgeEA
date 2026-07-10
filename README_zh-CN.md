# RegimeForgeEA

RegimeForgeEA 是一个模块化、按行情状态切换策略的自动交易框架，包含 MQL5 EA
和 Python 研究回测器。项目不绑定任何交易品种：当前附带的第一套策略是 XAUUSD
M5 趋势突破研究候选，但执行和风险架构本身与黄金无关。

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
- 用于候选评估、仅限研究的 Bollinger/RSI 震荡模型

当前 EA 只管理趋势突破研究候选。由于公开数据研究尚未发现可部署的策略，默认
禁止新开仓（`InpEnableNewEntries=false`）。EA 中震荡与高波动行情仍然保持空仓。

## 研究状态

已使用预先固定的候选和时间切分测试两类独立策略：2021–2023 训练、2024 验证、
2025 最终留出。两类候选均未达到验证资格，因此不会查看最终留出集，更不会声称
存在盈利默认策略。

- [趋势候选研究](reports/Trend_Candidate_Research.md)：8 个 M15/M30/H1
  EMA/ADX/Donchian 候选，均未通过训练门槛。
- [震荡候选研究](reports/Range_Candidate_Research.md)：8 个 M15/M30/H1
  Bollinger/RSI 候选，均未通过训练门槛。

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
