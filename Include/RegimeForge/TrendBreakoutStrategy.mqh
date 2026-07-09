#ifndef REGIME_FORGE_TREND_BREAKOUT_STRATEGY_MQH
#define REGIME_FORGE_TREND_BREAKOUT_STRATEGY_MQH

#include <RegimeForge/StrategyTypes.mqh>

class CTrendBreakoutStrategy
  {
private:
   string          m_symbol;
   ENUM_TIMEFRAMES m_timeframe;
   int             m_breakout_bars;
   double          m_stop_atr;
   double          m_take_profit_atr;

public:
                    CTrendBreakoutStrategy(void)
     {
      m_symbol="";
      m_timeframe=PERIOD_M5;
      m_breakout_bars=18;
      m_stop_atr=1.6;
      m_take_profit_atr=3.0;
     }

   void Configure(const string symbol,
                  const ENUM_TIMEFRAMES timeframe,
                  const int breakout_bars,
                  const double stop_atr,
                  const double take_profit_atr)
     {
      m_symbol=symbol;
      m_timeframe=timeframe;
      m_breakout_bars=MathMax(5,breakout_bars);
      m_stop_atr=stop_atr;
      m_take_profit_atr=take_profit_atr;
     }

   TradeSignal Evaluate(const double fast_ma,
                        const double slow_ma,
                        const double atr)
     {
      if(atr<=0.0)
         return EmptySignal("ATR unavailable");

      MqlRates rates[];
      ArraySetAsSeries(rates,true);
      const int required=m_breakout_bars+2;
      if(CopyRates(m_symbol,m_timeframe,0,required,rates)<required)
         return EmptySignal("Not enough price history");

      double prior_high=rates[2].high;
      double prior_low=rates[2].low;
      for(int i=3;i<required;i++)
        {
         prior_high=MathMax(prior_high,rates[i].high);
         prior_low=MathMin(prior_low,rates[i].low);
        }

      // Use the last closed candle only. This avoids intrabar signal repainting.
      if(fast_ma>slow_ma && rates[1].close>prior_high && rates[1].close>rates[1].open)
        {
         TradeSignal signal;
         signal.direction=SIGNAL_BUY;
         signal.stop_distance=m_stop_atr*atr;
         signal.take_profit_distance=m_take_profit_atr*atr;
         signal.reason="Trend breakout long";
         return signal;
        }

      if(fast_ma<slow_ma && rates[1].close<prior_low && rates[1].close<rates[1].open)
        {
         TradeSignal signal;
         signal.direction=SIGNAL_SELL;
         signal.stop_distance=m_stop_atr*atr;
         signal.take_profit_distance=m_take_profit_atr*atr;
         signal.reason="Trend breakout short";
         return signal;
        }

      return EmptySignal("No breakout");
     }
  };

#endif
