#property copyright "Berry Wahlberg"
#property version   "1.00"
#property strict
#property description "M5 volume-confirmed reversal research candidate"

#include <Trade/Trade.mqh>

input group "General"
input ENUM_TIMEFRAMES InpSignalTimeframe=PERIOD_M5;
input ulong           InpMagicNumber=26071002;
input bool            InpEnableNewEntries=false;
input double          InpFixedLots=0.02;
input int             InpMaxSpreadPoints=80;
input int             InpSlippagePoints=30;
input double          InpMaxDailyLossPct=2.00;
input int             InpMaxConsecutiveLosses=4;
input int             InpCooldownBars=12;

input group "Completed Higher-Timeframe Trend Filter"
input bool            InpUseHigherTrendFilter=true;
input ENUM_TIMEFRAMES InpTrendTimeframe=PERIOD_H1;
input int             InpTrendFastMAPeriod=20;
input int             InpTrendSlowMAPeriod=50;

input group "Volume-Confirmed Reversal"
input int             InpReturnLookbackBars=3;
input int             InpQuantileBars=5760;
input double          InpLowerQuantile=0.20;
input int             InpVolumeMAPeriod=60;
input double          InpMinimumVolumeRatio=1.50;
input int             InpHoldBars=24;

CTrade   g_trade;
datetime g_last_bar_time=0;
datetime g_cooldown_until=0;
double   g_day_start_balance=0.0;
int      g_day_key=-1;
int      g_consecutive_losses=0;
int      g_trend_fast_handle=INVALID_HANDLE;
int      g_trend_slow_handle=INVALID_HANDLE;

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

bool SpreadAllowed()
  {
   MqlTick tick;
   const double point=SymbolInfoDouble(_Symbol,SYMBOL_POINT);
   return point>0.0 && SymbolInfoTick(_Symbol,tick) &&
          (tick.ask-tick.bid)/point<=InpMaxSpreadPoints;
  }

int CurrentDayKey()
  {
   MqlDateTime now;
   TimeToStruct(TimeCurrent(),now);
   return now.year*1000+now.day_of_year;
  }

void RefreshDailyRiskState()
  {
   const int day_key=CurrentDayKey();
   if(day_key!=g_day_key)
     {
      g_day_key=day_key;
      g_day_start_balance=AccountInfoDouble(ACCOUNT_BALANCE);
     }
  }

bool DailyLossLockActive()
  {
   RefreshDailyRiskState();
   if(InpMaxDailyLossPct<=0.0 || g_day_start_balance<=0.0)
      return false;
   return AccountInfoDouble(ACCOUNT_BALANCE)<=
          g_day_start_balance*(1.0-InpMaxDailyLossPct/100.0);
  }

bool HigherTrendAllowed()
  {
   if(!InpUseHigherTrendFilter)
      return true;
   double fast[1];
   double slow[1];
   if(g_trend_fast_handle==INVALID_HANDLE || g_trend_slow_handle==INVALID_HANDLE ||
      CopyBuffer(g_trend_fast_handle,0,1,1,fast)!=1 ||
      CopyBuffer(g_trend_slow_handle,0,1,1,slow)!=1)
      return false;
   return MathIsValidNumber(fast[0]) && MathIsValidNumber(slow[0]) &&
          fast[0]>slow[0];
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
   const ENUM_ACCOUNT_MARGIN_MODE margin_mode=
      (ENUM_ACCOUNT_MARGIN_MODE)AccountInfoInteger(ACCOUNT_MARGIN_MODE);
   if(margin_mode==ACCOUNT_MARGIN_MODE_RETAIL_HEDGING || !PositionSelect(_Symbol))
      return false;
   return (ulong)PositionGetInteger(POSITION_MAGIC)!=InpMagicNumber;
  }

bool IsNewSignalBar()
  {
   const datetime current_time=iTime(_Symbol,InpSignalTimeframe,0);
   if(current_time==0 || current_time==g_last_bar_time)
      return false;
   g_last_bar_time=current_time;
   return true;
  }

bool IsLongSignal()
  {
   if(InpReturnLookbackBars<=0 || InpQuantileBars<20 ||
      InpVolumeMAPeriod<=0 || InpLowerQuantile<=0.0 ||
      InpLowerQuantile>=0.5)
      return false;

   const int required_bars=MathMax(InpQuantileBars+InpReturnLookbackBars+1,
                                   InpVolumeMAPeriod+1);
   MqlRates rates[];
   ArraySetAsSeries(rates,true);
   if(CopyRates(_Symbol,InpSignalTimeframe,0,required_bars,rates)!=required_bars)
      return false;

   const double signal_close=rates[1].close;
   const double base_close=rates[1+InpReturnLookbackBars].close;
   if(signal_close<=0.0 || base_close<=0.0)
      return false;
   const double signal_return=signal_close/base_close-1.0;

   double returns[];
   ArrayResize(returns,InpQuantileBars);
   for(int index=0;index<InpQuantileBars;index++)
     {
      const int shift=2+index;
      const double close_now=rates[shift].close;
      const double close_then=rates[shift+InpReturnLookbackBars].close;
      if(close_now<=0.0 || close_then<=0.0)
         return false;
      returns[index]=close_now/close_then-1.0;
     }
   ArraySort(returns);
   const int quantile_index=(int)MathFloor(InpLowerQuantile*(InpQuantileBars-1));
   const double lower_quantile=returns[quantile_index];

   long volume_sum=0;
   for(int shift=1;shift<=InpVolumeMAPeriod;shift++)
      volume_sum+=(long)rates[shift].tick_volume;
   const double average_volume=(double)volume_sum/InpVolumeMAPeriod;
   const double volume_ratio=(average_volume>0.0 ?
                              (double)rates[1].tick_volume/average_volume : 0.0);
   return signal_return<=lower_quantile && volume_ratio>=InpMinimumVolumeRatio;
  }

bool CloseExpiredPosition(const ulong ticket)
  {
   if(!PositionSelectByTicket(ticket))
      return false;
   const datetime entry_time=(datetime)PositionGetInteger(POSITION_TIME);
   const int seconds=PeriodSeconds(InpSignalTimeframe);
   if(entry_time<=0 || seconds<=0 ||
      TimeCurrent()<entry_time+InpHoldBars*seconds)
      return false;
   if(!g_trade.PositionClose(ticket))
     {
      Print("Time exit failed: ",g_trade.ResultRetcode()," ",
            g_trade.ResultRetcodeDescription());
      return false;
     }
   return true;
  }

int OnInit()
  {
   if(InpFixedLots<=0.0 || InpHoldBars<=0)
      return INIT_PARAMETERS_INCORRECT;
   if(InpTrendFastMAPeriod<=0 || InpTrendSlowMAPeriod<=InpTrendFastMAPeriod ||
      InpMaxDailyLossPct<0.0 || InpMaxConsecutiveLosses<0 || InpCooldownBars<0)
      return INIT_PARAMETERS_INCORRECT;
   g_trade.SetExpertMagicNumber(InpMagicNumber);
   g_trade.SetDeviationInPoints(InpSlippagePoints);
   g_trend_fast_handle=iMA(_Symbol,InpTrendTimeframe,InpTrendFastMAPeriod,0,
                            MODE_EMA,PRICE_CLOSE);
   g_trend_slow_handle=iMA(_Symbol,InpTrendTimeframe,InpTrendSlowMAPeriod,0,
                            MODE_EMA,PRICE_CLOSE);
   if(g_trend_fast_handle==INVALID_HANDLE || g_trend_slow_handle==INVALID_HANDLE)
      return INIT_FAILED;
   RefreshDailyRiskState();
   return INIT_SUCCEEDED;
  }

void OnDeinit(const int reason)
  {
   if(g_trend_fast_handle!=INVALID_HANDLE)
      IndicatorRelease(g_trend_fast_handle);
   if(g_trend_slow_handle!=INVALID_HANDLE)
      IndicatorRelease(g_trend_slow_handle);
  }

void OnTradeTransaction(const MqlTradeTransaction &transaction,
                        const MqlTradeRequest &request,
                        const MqlTradeResult &result)
  {
   if(transaction.type!=TRADE_TRANSACTION_DEAL_ADD || transaction.deal==0 ||
      !HistoryDealSelect(transaction.deal))
      return;
   if(HistoryDealGetString(transaction.deal,DEAL_SYMBOL)!=_Symbol ||
      (ulong)HistoryDealGetInteger(transaction.deal,DEAL_MAGIC)!=InpMagicNumber ||
      HistoryDealGetInteger(transaction.deal,DEAL_ENTRY)!=DEAL_ENTRY_OUT)
      return;
   const double net_profit=HistoryDealGetDouble(transaction.deal,DEAL_PROFIT)+
                           HistoryDealGetDouble(transaction.deal,DEAL_SWAP)+
                           HistoryDealGetDouble(transaction.deal,DEAL_COMMISSION);
   if(net_profit<0.0)
     {
      g_consecutive_losses++;
      if(InpMaxConsecutiveLosses>0 &&
         g_consecutive_losses>=InpMaxConsecutiveLosses)
        {
         g_cooldown_until=TimeCurrent()+InpCooldownBars*PeriodSeconds(InpSignalTimeframe);
         g_consecutive_losses=0;
         Print("Loss cooldown activated until ",TimeToString(g_cooldown_until));
        }
     }
   else
      g_consecutive_losses=0;
  }

void OnTick()
  {
   if(!IsNewSignalBar())
      return;

   ulong ticket=0;
   if(HasManagedPosition(ticket))
     {
      CloseExpiredPosition(ticket);
      return;
     }
   if(!InpEnableNewEntries || HasUnmanagedNettingPosition() || !SpreadAllowed() ||
      DailyLossLockActive() || TimeCurrent()<g_cooldown_until ||
      !HigherTrendAllowed() || !IsLongSignal())
      return;

   const double volume=NormalizeVolume(InpFixedLots);
   if(volume<=0.0)
     {
      Print("Fixed volume is below the symbol minimum or invalid");
      return;
     }
   if(!g_trade.Buy(volume,_Symbol,0.0,0.0,0.0,"M5 volume reversal"))
      Print("Buy failed: ",g_trade.ResultRetcode()," ",
            g_trade.ResultRetcodeDescription());
  }
