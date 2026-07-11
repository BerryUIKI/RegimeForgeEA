#property copyright "Berry Wahlberg"
#property version   "1.00"
#property strict
#property description "H4 EMA crossover research candidate; entries disabled by default"

#include <Trade/Trade.mqh>

input group "General"
input ENUM_TIMEFRAMES InpSignalTimeframe=PERIOD_H4;
input ulong           InpMagicNumber=26071101;
input bool            InpEnableNewEntries=false;
input int             InpMaxSpreadPoints=80;
input int             InpSlippagePoints=30;

input group "EMA Crossover Signal"
input int             InpFastMAPeriod=20;
input int             InpSlowMAPeriod=50;
input int             InpATRPeriod=14;
input bool            InpAllowLong=true;
input bool            InpAllowShort=true;

input group "Risk and Exit Model"
input double          InpRiskPerTradePct=0.50;
input double          InpMaxDailyLossPct=2.00;
input double          InpMaxPeakDrawdownPct=20.00;
input double          InpStopATR=2.50;
input double          InpTakeProfitATR=4.00;
input double          InpTrailingATR=2.50;
input int             InpHoldBars=42;

CTrade   g_trade;
datetime g_last_bar_time=0;
int      g_day_key=-1;
double   g_day_start_equity=0.0;
double   g_peak_equity=0.0;
int      g_fast_handle=INVALID_HANDLE;
int      g_slow_handle=INVALID_HANDLE;
int      g_atr_handle=INVALID_HANDLE;

int CurrentDayKey()
  {
   MqlDateTime now;
   TimeToStruct(TimeCurrent(),now);
   return now.year*1000+now.day_of_year;
  }

void RefreshRiskState()
  {
   const double equity=AccountInfoDouble(ACCOUNT_EQUITY);
   if(g_peak_equity<=0.0)
      g_peak_equity=equity;
   g_peak_equity=MathMax(g_peak_equity,equity);
   const int day_key=CurrentDayKey();
   if(day_key!=g_day_key)
     {
      g_day_key=day_key;
      g_day_start_equity=equity;
     }
  }

bool RiskLockActive()
  {
   RefreshRiskState();
   const double equity=AccountInfoDouble(ACCOUNT_EQUITY);
   if(InpMaxDailyLossPct>0.0 && g_day_start_equity>0.0 &&
      equity<=g_day_start_equity*(1.0-InpMaxDailyLossPct/100.0))
      return true;
   if(InpMaxPeakDrawdownPct>0.0 && g_peak_equity>0.0 &&
      equity<=g_peak_equity*(1.0-InpMaxPeakDrawdownPct/100.0))
      return true;
   return false;
  }

bool IsNewSignalBar()
  {
   const datetime current=iTime(_Symbol,InpSignalTimeframe,0);
   if(current==0 || current==g_last_bar_time)
      return false;
   g_last_bar_time=current;
   return true;
  }

bool SpreadAllowed()
  {
   MqlTick tick;
   const double point=SymbolInfoDouble(_Symbol,SYMBOL_POINT);
   return point>0.0 && SymbolInfoTick(_Symbol,tick) &&
          (tick.ask-tick.bid)/point<=InpMaxSpreadPoints;
  }

bool HasManagedPosition(ulong &ticket)
  {
   ticket=0;
   for(int index=PositionsTotal()-1;index>=0;index--)
     {
      const ulong candidate=PositionGetTicket(index);
      if(candidate==0 || !PositionSelectByTicket(candidate))
         continue;
      if(PositionGetString(POSITION_SYMBOL)==_Symbol &&
         (ulong)PositionGetInteger(POSITION_MAGIC)==InpMagicNumber)
        {
         ticket=candidate;
         return true;
        }
     }
   return false;
  }

bool HasUnmanagedNettingPosition()
  {
   const ENUM_ACCOUNT_MARGIN_MODE mode=(ENUM_ACCOUNT_MARGIN_MODE)AccountInfoInteger(ACCOUNT_MARGIN_MODE);
   if(mode==ACCOUNT_MARGIN_MODE_RETAIL_HEDGING || !PositionSelect(_Symbol))
      return false;
   return (ulong)PositionGetInteger(POSITION_MAGIC)!=InpMagicNumber;
  }

int CrossoverSignal()
  {
   double fast[];
   double slow[];
   ArrayResize(fast,2);
   ArrayResize(slow,2);
   ArraySetAsSeries(fast,true);
   ArraySetAsSeries(slow,true);
   if(CopyBuffer(g_fast_handle,0,1,2,fast)!=2 || CopyBuffer(g_slow_handle,0,1,2,slow)!=2)
      return 0;
   if(InpAllowLong && fast[0]>slow[0] && fast[1]<=slow[1])
      return 1;
   if(InpAllowShort && fast[0]<slow[0] && fast[1]>=slow[1])
      return -1;
   return 0;
  }

double CurrentATR()
  {
   double atr[1];
   if(CopyBuffer(g_atr_handle,0,1,1,atr)!=1 || atr[0]<=0.0)
      return 0.0;
   return atr[0];
  }

double NormalizeVolume(const double raw_volume)
  {
   const double minimum=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN);
   const double maximum=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX);
   const double step=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP);
   if(step<=0.0 || raw_volume<minimum)
      return 0.0;
   return NormalizeDouble(MathMax(minimum,MathMin(maximum,MathFloor(raw_volume/step)*step)),8);
  }

double RiskVolume(const int direction,const double entry,const double stop)
  {
   const double risk_money=AccountInfoDouble(ACCOUNT_EQUITY)*InpRiskPerTradePct/100.0;
   double profit=0.0;
   const ENUM_ORDER_TYPE type=(direction>0 ? ORDER_TYPE_BUY : ORDER_TYPE_SELL);
   if(risk_money<=0.0 || !OrderCalcProfit(type,_Symbol,1.0,entry,stop,profit) || profit>=0.0)
      return 0.0;
   return NormalizeVolume(risk_money/MathAbs(profit));
  }

bool CloseExpiredPosition(const ulong ticket)
  {
   if(!PositionSelectByTicket(ticket))
      return false;
   const int seconds=PeriodSeconds(InpSignalTimeframe);
   const datetime entry=(datetime)PositionGetInteger(POSITION_TIME);
   if(seconds<=0 || entry<=0 || TimeCurrent()<entry+InpHoldBars*seconds)
      return false;
   if(!g_trade.PositionClose(ticket))
      Print("Time exit failed: ",g_trade.ResultRetcode()," ",g_trade.ResultRetcodeDescription());
   return true;
  }

void ManageTrailingStop(const ulong ticket)
  {
   if(!PositionSelectByTicket(ticket))
      return;
   const double atr=CurrentATR();
   MqlTick tick;
   if(atr<=0.0 || !SymbolInfoTick(_Symbol,tick))
      return;
   const long position_type=PositionGetInteger(POSITION_TYPE);
   const double old_stop=PositionGetDouble(POSITION_SL);
   const double take_profit=PositionGetDouble(POSITION_TP);
   const int digits=(int)SymbolInfoInteger(_Symbol,SYMBOL_DIGITS);
   double candidate=0.0;
   if(position_type==POSITION_TYPE_BUY)
     {
      candidate=NormalizeDouble(tick.bid-InpTrailingATR*atr,digits);
      if(candidate<=old_stop)
         return;
     }
   else if(position_type==POSITION_TYPE_SELL)
     {
      candidate=NormalizeDouble(tick.ask+InpTrailingATR*atr,digits);
      if(old_stop>0.0 && candidate>=old_stop)
         return;
     }
   else
      return;
   if(!g_trade.PositionModify(ticket,candidate,take_profit))
      Print("Trailing-stop update failed: ",g_trade.ResultRetcode()," ",g_trade.ResultRetcodeDescription());
  }

int OnInit()
  {
   if(InpFastMAPeriod<=0 || InpSlowMAPeriod<=InpFastMAPeriod || InpATRPeriod<=0 ||
      InpRiskPerTradePct<=0.0 || InpStopATR<=0.0 || InpTakeProfitATR<=0.0 ||
      InpTrailingATR<=0.0 || InpHoldBars<=0 || InpMaxDailyLossPct<0.0 || InpMaxPeakDrawdownPct<0.0)
      return INIT_PARAMETERS_INCORRECT;
   g_trade.SetExpertMagicNumber(InpMagicNumber);
   g_trade.SetDeviationInPoints(InpSlippagePoints);
   g_fast_handle=iMA(_Symbol,InpSignalTimeframe,InpFastMAPeriod,0,MODE_EMA,PRICE_CLOSE);
   g_slow_handle=iMA(_Symbol,InpSignalTimeframe,InpSlowMAPeriod,0,MODE_EMA,PRICE_CLOSE);
   g_atr_handle=iATR(_Symbol,InpSignalTimeframe,InpATRPeriod);
   if(g_fast_handle==INVALID_HANDLE || g_slow_handle==INVALID_HANDLE || g_atr_handle==INVALID_HANDLE)
      return INIT_FAILED;
   RefreshRiskState();
   return INIT_SUCCEEDED;
  }

void OnDeinit(const int reason)
  {
   if(g_fast_handle!=INVALID_HANDLE) IndicatorRelease(g_fast_handle);
   if(g_slow_handle!=INVALID_HANDLE) IndicatorRelease(g_slow_handle);
   if(g_atr_handle!=INVALID_HANDLE) IndicatorRelease(g_atr_handle);
  }

void OnTick()
  {
   ulong ticket=0;
   if(HasManagedPosition(ticket))
     {
      ManageTrailingStop(ticket);
      if(IsNewSignalBar())
         CloseExpiredPosition(ticket);
      return;
     }
   if(!IsNewSignalBar() || !InpEnableNewEntries || HasUnmanagedNettingPosition() ||
      !SpreadAllowed() || RiskLockActive())
      return;
   const int direction=CrossoverSignal();
   const double atr=CurrentATR();
   if(direction==0 || atr<=0.0)
      return;
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick))
      return;
   const int digits=(int)SymbolInfoInteger(_Symbol,SYMBOL_DIGITS);
   const double point=SymbolInfoDouble(_Symbol,SYMBOL_POINT);
   const double minimum_stop=(double)SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL)*point;
   const double stop_distance=MathMax(InpStopATR*atr,minimum_stop);
   const double target_distance=MathMax(InpTakeProfitATR*atr,minimum_stop);
   const double entry=(direction>0 ? tick.ask : tick.bid);
   const double stop=NormalizeDouble(entry-direction*stop_distance,digits);
   const double target=NormalizeDouble(entry+direction*target_distance,digits);
   const double volume=RiskVolume(direction,entry,stop);
   if(volume<=0.0)
     {
      Print("Risk volume is below the broker minimum or cannot be calculated");
      return;
     }
   const bool placed=(direction>0 ?
                      g_trade.Buy(volume,_Symbol,0.0,stop,target,"H4 EMA crossover") :
                      g_trade.Sell(volume,_Symbol,0.0,stop,target,"H4 EMA crossover"));
   if(!placed)
      Print("Entry failed: ",g_trade.ResultRetcode()," ",g_trade.ResultRetcodeDescription());
  }
