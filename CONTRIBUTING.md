# Contributing to RegimeForgeEA

Contributions are welcome. Open an issue before substantial strategy or
architecture work so the research scope and validation plan can be agreed.

## Development workflow

1. Create a focused branch from `main`.
2. Keep MQL5 source and code comments in English.
3. Add or update Python tests for changed backtest behavior.
4. Run `python -m unittest discover -s tests -v`.
5. Explain data sources, execution assumptions, and limitations for every
   reported performance result.

## Strategy contributions

Strategy modules must produce the shared `TradeSignal` interface. Do not bypass
the main EA's position sizing, execution, or risk locks. A pull request that
adds a strategy should include:

- The precise entry, exit, and regime conditions.
- The data source, period, and transaction-cost assumptions.
- In-sample, out-of-sample, and walk-forward evidence where applicable.
- A statement of known limitations and the target instrument assumptions.

Do not submit account credentials, broker statements containing personal data,
or proprietary market data.
