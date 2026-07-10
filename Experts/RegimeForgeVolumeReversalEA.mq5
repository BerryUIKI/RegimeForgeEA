#property copyright "Berry Wahlberg"
#property version   "1.00"
#property strict
#property description "M5 volume-confirmed reversal research candidate"

#include <Trade/Trade.mqh>

input group "General"
input ENUM_TIMEFRAMES InpSignalTimeframe=PERIOD_M5;
input ulong           InpMagicNumber=26071002;
input bool            InpEnableNewEntries=false;
input double          InpFixedLots=0.10;
input int             InpMaxSpreadPoints=80;
input int             InpSlippagePoints=30;

input group "Volume-Confirmed Reversal"
input int             InpReturnLookbackBars=3;
input int             InpQuantileBars=5760;
input double          InpLowerQuantile=0.20;
input int             InpVolumeMAPeriod=60;
input double          InpMinimumVolumeRatio=1.50;
input int             InpHoldBars=24;

CTrade   g_trade;
datetime g_last_bar_time=0;

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
   g_trade.SetExpertMagicNumber(InpMagicNumber);
   g_trade.SetDeviationInPoints(InpSlippagePoints);
   return INIT_SUCCEEDED;
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
      !IsLongSignal())
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
