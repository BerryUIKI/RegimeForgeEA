#property copyright "RegimeForgeEA contributors"
#property version   "1.00"
#property strict
#property description "Regime-aware, risk-sized multi-strategy Expert Advisor"

#include <Trade/Trade.mqh>
#include <RegimeForge/StrategyTypes.mqh>
#include <RegimeForge/TrendBreakoutStrategy.mqh>

input group "General"
input ENUM_TIMEFRAMES InpSignalTimeframe=PERIOD_M5;
input ulong           InpMagicNumber=26070901;
input bool            InpAllowLong=true;
input bool            InpAllowShort=true;
input int             InpSlippagePoints=30;
input int             InpMaxSpreadPoints=80;

input group "Risk"
input double InpRiskPerTradePct=1.00;
input double InpMaxDailyLossPct=4.00;
input double InpMaxDrawdownPct=12.00;

input group "Regime"
input int    InpFastMAPeriod=20;
input int    InpSlowMAPeriod=50;
input int    InpATRPeriod=14;
input int    InpADXPeriod=14;
input double InpADXTrendLevel=20.0;
input double InpHighVolatilityATRRatio=1.80;

input group "Aggressive Trend Breakout"
input int    InpBreakoutBars=18;
input double InpStopATR=1.60;
input double InpTakeProfitATR=3.00;
input double InpTrailingATR=1.20;

CTrade                 g_trade;
CTrendBreakoutStrategy g_trend_strategy;
int                    g_fast_ma_handle=INVALID_HANDLE;
int                    g_slow_ma_handle=INVALID_HANDLE;
int                    g_atr_handle=INVALID_HANDLE;
int                    g_atr_slow_handle=INVALID_HANDLE;
int                    g_adx_handle=INVALID_HANDLE;
datetime               g_last_bar_time=0;
double                 g_day_start_equity=0.0;
double                 g_peak_equity=0.0;
int                    g_day_key=-1;

bool ReadBufferValue(const int handle,const int buffer,const int shift,double &value)
  {
   double data[1];
   if(handle==INVALID_HANDLE || CopyBuffer(handle,buffer,shift,1,data)!=1)
      return false;
   value=data[0];
   return MathIsValidNumber(value);
  }

int CurrentDayKey()
  {
   MqlDateTime now;
   TimeToStruct(TimeCurrent(),now);
   return now.year*1000+now.day_of_year;
  }

void RefreshRiskSession()
  {
   const double equity=AccountInfoDouble(ACCOUNT_EQUITY);
   const int day_key=CurrentDayKey();
   if(g_day_key!=day_key)
     {
      g_day_key=day_key;
      g_day_start_equity=equity;
     }
   if(equity>g_peak_equity)
      g_peak_equity=equity;
  }

bool RiskLockActive(string &reason)
  {
   RefreshRiskSession();
   const double equity=AccountInfoDouble(ACCOUNT_EQUITY);

   if(g_day_start_equity>0.0 &&
      equity<=g_day_start_equity*(1.0-InpMaxDailyLossPct/100.0))
     {
      reason="Daily equity loss limit";
      return true;
     }

   if(g_peak_equity>0.0 &&
      equity<=g_peak_equity*(1.0-InpMaxDrawdownPct/100.0))
     {
      reason="Peak equity drawdown limit";
      return true;
     }
   return false;
  }

double NormalizeVolume(const double raw_volume)
  {
   const double min_volume=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN);
   const double max_volume=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX);
   const double step=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP);
   if(step<=0.0 || raw_volume<min_volume)
      return 0.0;
   double volume=MathFloor(raw_volume/step)*step;
   volume=MathMax(min_volume,MathMin(max_volume,volume));
   return NormalizeDouble(volume,8);
  }

double CalculateRiskVolume(const SignalDirection direction,
                           const double entry,
                           const double stop)
  {
   const double equity=AccountInfoDouble(ACCOUNT_EQUITY);
   const double risk_money=equity*InpRiskPerTradePct/100.0;
   if(risk_money<=0.0 || entry==stop)
      return 0.0;

   double loss_one_lot=0.0;
   const ENUM_ORDER_TYPE order_type=
      (direction==SIGNAL_BUY ? ORDER_TYPE_BUY : ORDER_TYPE_SELL);
   if(!OrderCalcProfit(order_type,_Symbol,1.0,entry,stop,loss_one_lot))
      return 0.0;
   loss_one_lot=MathAbs(loss_one_lot);
   if(loss_one_lot<=0.0)
      return 0.0;
   return NormalizeVolume(risk_money/loss_one_lot);
  }

bool HasManagedPosition()
  {
   for(int i=PositionsTotal()-1;i>=0;i--)
     {
      const ulong ticket=PositionGetTicket(i);
      if(ticket==0 || !PositionSelectByTicket(ticket))
         continue;
      if(PositionGetString(POSITION_SYMBOL)==_Symbol &&
         (ulong)PositionGetInteger(POSITION_MAGIC)==InpMagicNumber)
         return true;
     }
   return false;
  }

bool SpreadAllowed()
  {
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick))
      return false;
   const double point=SymbolInfoDouble(_Symbol,SYMBOL_POINT);
   return point>0.0 && (tick.ask-tick.bid)/point<=InpMaxSpreadPoints;
  }

MarketRegime DetectRegime(double &fast_ma,double &slow_ma,double &atr)
  {
   double atr_slow=0.0;
   double adx=0.0;
   if(!ReadBufferValue(g_fast_ma_handle,0,1,fast_ma) ||
      !ReadBufferValue(g_slow_ma_handle,0,1,slow_ma) ||
      !ReadBufferValue(g_atr_handle,0,1,atr) ||
      !ReadBufferValue(g_atr_slow_handle,0,1,atr_slow) ||
      !ReadBufferValue(g_adx_handle,0,1,adx))
      return REGIME_UNKNOWN;

   if(atr_slow>0.0 && atr/atr_slow>=InpHighVolatilityATRRatio)
      return REGIME_HIGH_VOLATILITY;
   if(adx>=InpADXTrendLevel)
      return REGIME_TREND;
   return REGIME_RANGE;
  }

void ManageTrailingStop()
  {
   double atr=0.0;
   if(!ReadBufferValue(g_atr_handle,0,1,atr) || atr<=0.0)
      return;

   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick))
      return;
   const int digits=(int)SymbolInfoInteger(_Symbol,SYMBOL_DIGITS);
   const double point=SymbolInfoDouble(_Symbol,SYMBOL_POINT);
   const double min_stop=(double)SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL)*point;

   for(int i=PositionsTotal()-1;i>=0;i--)
     {
      const ulong ticket=PositionGetTicket(i);
      if(ticket==0 || !PositionSelectByTicket(ticket))
         continue;
      if(PositionGetString(POSITION_SYMBOL)!=_Symbol ||
         (ulong)PositionGetInteger(POSITION_MAGIC)!=InpMagicNumber)
         continue;

      const ENUM_POSITION_TYPE type=(ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE);
      const double old_sl=PositionGetDouble(POSITION_SL);
      const double tp=PositionGetDouble(POSITION_TP);
      double new_sl=0.0;

      if(type==POSITION_TYPE_BUY)
        {
         new_sl=NormalizeDouble(tick.bid-MathMax(InpTrailingATR*atr,min_stop),digits);
         if((old_sl==0.0 || new_sl>old_sl) && new_sl<tick.bid)
           {
            if(!g_trade.PositionModify(ticket,new_sl,tp) ||
               (g_trade.ResultRetcode()!=TRADE_RETCODE_DONE &&
                g_trade.ResultRetcode()!=TRADE_RETCODE_NO_CHANGES))
               Print("Trailing stop update failed: ",g_trade.ResultRetcode(),
                     " ",g_trade.ResultRetcodeDescription());
           }
        }
      else if(type==POSITION_TYPE_SELL)
        {
         new_sl=NormalizeDouble(tick.ask+MathMax(InpTrailingATR*atr,min_stop),digits);
         if((old_sl==0.0 || new_sl<old_sl) && new_sl>tick.ask)
           {
            if(!g_trade.PositionModify(ticket,new_sl,tp) ||
               (g_trade.ResultRetcode()!=TRADE_RETCODE_DONE &&
                g_trade.ResultRetcode()!=TRADE_RETCODE_NO_CHANGES))
               Print("Trailing stop update failed: ",g_trade.ResultRetcode(),
                     " ",g_trade.ResultRetcodeDescription());
           }
        }
     }
  }

void TryOpenPosition(const TradeSignal &signal)
  {
   if(signal.direction==SIGNAL_NONE || HasManagedPosition() || !SpreadAllowed())
      return;
   if((signal.direction==SIGNAL_BUY && !InpAllowLong) ||
      (signal.direction==SIGNAL_SELL && !InpAllowShort))
      return;

   string lock_reason;
   if(RiskLockActive(lock_reason))
     {
      Print("Entry blocked: ",lock_reason);
      return;
     }

   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick))
      return;

   const int digits=(int)SymbolInfoInteger(_Symbol,SYMBOL_DIGITS);
   const double point=SymbolInfoDouble(_Symbol,SYMBOL_POINT);
   const double min_stop=(double)SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL)*point;
   const double stop_distance=MathMax(signal.stop_distance,min_stop);
   const double tp_distance=MathMax(signal.take_profit_distance,min_stop);
   const double entry=(signal.direction==SIGNAL_BUY ? tick.ask : tick.bid);
   const double stop=NormalizeDouble(
      signal.direction==SIGNAL_BUY ? entry-stop_distance : entry+stop_distance,digits);
   const double take_profit=NormalizeDouble(
      signal.direction==SIGNAL_BUY ? entry+tp_distance : entry-tp_distance,digits);
   const double volume=CalculateRiskVolume(signal.direction,entry,stop);
   if(volume<=0.0)
     {
      Print("Entry blocked: calculated volume is below broker minimum");
      return;
     }

   bool sent=false;
   if(signal.direction==SIGNAL_BUY)
      sent=g_trade.Buy(volume,_Symbol,0.0,stop,take_profit,signal.reason);
   else
      sent=g_trade.Sell(volume,_Symbol,0.0,stop,take_profit,signal.reason);

   if(!sent)
      Print("Order failed: ",g_trade.ResultRetcode()," ",g_trade.ResultRetcodeDescription());
  }

int OnInit()
  {
   if(InpRiskPerTradePct<=0.0 || InpRiskPerTradePct>10.0 ||
      InpMaxDailyLossPct<=0.0 || InpMaxDrawdownPct<=0.0 ||
      InpFastMAPeriod>=InpSlowMAPeriod)
     {
      Print("Invalid EA inputs");
      return INIT_PARAMETERS_INCORRECT;
     }

   g_fast_ma_handle=iMA(_Symbol,InpSignalTimeframe,InpFastMAPeriod,0,MODE_EMA,PRICE_CLOSE);
   g_slow_ma_handle=iMA(_Symbol,InpSignalTimeframe,InpSlowMAPeriod,0,MODE_EMA,PRICE_CLOSE);
   g_atr_handle=iATR(_Symbol,InpSignalTimeframe,InpATRPeriod);
   g_atr_slow_handle=iATR(_Symbol,InpSignalTimeframe,InpATRPeriod*4);
   g_adx_handle=iADX(_Symbol,InpSignalTimeframe,InpADXPeriod);
   if(g_fast_ma_handle==INVALID_HANDLE || g_slow_ma_handle==INVALID_HANDLE ||
      g_atr_handle==INVALID_HANDLE || g_atr_slow_handle==INVALID_HANDLE ||
      g_adx_handle==INVALID_HANDLE)
     {
      Print("Failed to create indicator handles: ",GetLastError());
      return INIT_FAILED;
     }

   g_trade.SetExpertMagicNumber(InpMagicNumber);
   g_trade.SetDeviationInPoints(InpSlippagePoints);
   g_trade.SetTypeFillingBySymbol(_Symbol);
   g_trend_strategy.Configure(_Symbol,InpSignalTimeframe,InpBreakoutBars,
                              InpStopATR,InpTakeProfitATR);
   RefreshRiskSession();
   return INIT_SUCCEEDED;
  }

void OnDeinit(const int reason)
  {
   if(g_fast_ma_handle!=INVALID_HANDLE) IndicatorRelease(g_fast_ma_handle);
   if(g_slow_ma_handle!=INVALID_HANDLE) IndicatorRelease(g_slow_ma_handle);
   if(g_atr_handle!=INVALID_HANDLE) IndicatorRelease(g_atr_handle);
   if(g_atr_slow_handle!=INVALID_HANDLE) IndicatorRelease(g_atr_slow_handle);
   if(g_adx_handle!=INVALID_HANDLE) IndicatorRelease(g_adx_handle);
  }

void OnTick()
  {
   RefreshRiskSession();
   ManageTrailingStop();

   const datetime bar_time=iTime(_Symbol,InpSignalTimeframe,0);
   if(bar_time==0 || bar_time==g_last_bar_time)
      return;
   g_last_bar_time=bar_time;

   double fast_ma=0.0,slow_ma=0.0,atr=0.0;
   const MarketRegime regime=DetectRegime(fast_ma,slow_ma,atr);
   if(regime==REGIME_TREND)
      TryOpenPosition(g_trend_strategy.Evaluate(fast_ma,slow_ma,atr));
  }
