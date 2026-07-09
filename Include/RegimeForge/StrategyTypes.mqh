#ifndef REGIME_FORGE_STRATEGY_TYPES_MQH
#define REGIME_FORGE_STRATEGY_TYPES_MQH

enum MarketRegime
  {
   REGIME_UNKNOWN = 0,
   REGIME_TREND,
   REGIME_RANGE,
   REGIME_HIGH_VOLATILITY
  };

enum SignalDirection
  {
   SIGNAL_NONE = 0,
   SIGNAL_BUY = 1,
   SIGNAL_SELL = -1
  };

struct TradeSignal
  {
   SignalDirection direction;
   double          stop_distance;
   double          take_profit_distance;
   string          reason;
  };

TradeSignal EmptySignal(const string reason="")
  {
   TradeSignal signal;
   signal.direction=SIGNAL_NONE;
   signal.stop_distance=0.0;
   signal.take_profit_distance=0.0;
   signal.reason=reason;
   return signal;
  }

#endif
