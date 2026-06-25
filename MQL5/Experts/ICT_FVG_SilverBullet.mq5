//+------------------------------------------------------------------+
//| ICT_FVG_SilverBullet.mq5                                         |
//| ICT Fair Value Gap suite - Strategy 1: Silver Bullet              |
//| Built step by step per spec: day range, liquidity sweep, market   |
//| structure shift, FVG detection/activation/invalidation, decayed   |
//| risk sizing with unified take-profit, safety sweeps.               |
//+------------------------------------------------------------------+
#property copyright "ICT FVG Suite"
#property version   "1.10"
#property strict

#include <Trade\Trade.mqh>
#include <Trade\PositionInfo.mqh>
#include <Trade\OrderInfo.mqh>

CTrade        trade;
CPositionInfo posInfo;
COrderInfo    ordInfo;

//------------------------------------------------------------------
// Strategy selector (8 ICT FVG strategies will live in this one EA;
// only Silver Bullet is implemented so far - the rest are reserved).
//------------------------------------------------------------------
enum ENUM_FVG_STRATEGY
{
   STRAT_SILVER_BULLET   = 0, // 1. Silver Bullet
   STRAT_RESERVED_2       = 1, // 2. Reserved
   STRAT_RESERVED_3       = 2, // 3. Reserved
   STRAT_RESERVED_4       = 3, // 4. Reserved
   STRAT_RESERVED_5       = 4, // 5. Reserved
   STRAT_RESERVED_6       = 5, // 6. Reserved
   STRAT_RESERVED_7       = 6, // 7. Reserved
   STRAT_RESERVED_8       = 7  // 8. Reserved
};

enum ENUM_FVG_STATE
{
   FVG_PENDING      = 0,
   FVG_ACTIVE       = 1,
   FVG_TRIGGERED    = 2,
   FVG_INVALIDATED  = 3,
   FVG_EXPIRED      = 4
};

//------------------------------------------------------------------
// Inputs
//------------------------------------------------------------------
input group "=== General ==="
input ENUM_FVG_STRATEGY InpStrategy        = STRAT_SILVER_BULLET;
input ulong             InpMagic           = 990011;
input int               InpSlippage        = 5;

input group "=== Day Range ==="
input string  InpCutoffTime        = "10:00"; // HH:MM broker time - day high/low locks here
input string  InpClosingTime       = "00:00"; // HH:MM broker time, 00:00 = end of day
input bool    InpCloseAtClosing    = true;    // close open positions at closing time
input bool    InpShowDayHighLow    = true;
input color   InpDayLineColor      = clrGold;

input group "=== Liquidity Sweep ==="
input int     InpMaxSweepCandles   = 10; // max candles allowed for price to sweep back into range

input group "=== Market Structure Shift ==="
input int     InpFractalStrength       = 2;  // candles left/right to confirm a fractal
input int     InpMSSLookbackCandles    = 30; // max candles to look back for the fractal
input int     InpMSSConfirmMaxCandles  = 0;  // 0 = no expiry, MSS must confirm within this many candles

input group "=== Fair Value Gap ==="
input int     InpATRPeriod          = 100;
input double  InpFVGMinSizeATRMult  = 0.5;  // 0 = no minimum filter
input double  InpFVGMaxSizeATRMult  = 0.0;  // 0 = no maximum filter
input bool    InpKeepHistory        = true; // keep historical chart objects visible
input color   InpBullishFVGColor    = clrLime;
input color   InpBearishFVGColor    = clrHotPink;
input color   InpMSSLineColor       = clrDodgerBlue;

input group "=== Risk Management ==="
input double  InpRiskPercent        = 1.0;  // % account risk for the first FVG of the day
input double  InpRiskDecayFactor    = 0.5;  // multiplier applied to each subsequent FVG's risk
input double  InpSLBufferWidthMult  = 1.0;  // SL buffer below/above FVG = FVG width * this multiplier
input double  InpRiskRewardRatio    = 2.0;
input int     InpMaxTradesPerSymbol = 3;
input int     InpMaxTradesPerEA     = 3;

input group "=== Chart Style ==="
input bool    InpRecolorCandles     = true;
input color   InpBullCandleColor    = clrLime;
input color   InpBearCandleColor    = clrCrimson;

//------------------------------------------------------------------
// FVG record
//------------------------------------------------------------------
struct FVG
{
   bool      isBullish;
   double    upper;
   double    lower;
   double    midpoint;
   datetime  createdTime;
   ENUM_FVG_STATE state;
   int       sequence;      // creation order this day -> drives risk decay
   ulong     orderTicket;
   ulong     positionTicket;
   double    lotSize;
   double    riskMoney;
   double    slPrice;
   string    objName;
};

struct SweepInfo
{
   bool      found;
   bool      isSellSetup;   // true: swept day high -> looking to sell
   int       sweepShift;
   datetime  sweepTime;
};

struct MSSInfo
{
   bool      found;
   double    level;
   datetime  fractalTime;
   bool      confirmed;
   bool      invalidated;
   string    lineObj;
   string    labelObj;
};

//------------------------------------------------------------------
// Daily state
//------------------------------------------------------------------
datetime  g_dayStart        = 0;
double    g_dayHigh         = 0;
double    g_dayLow          = 0;
bool      g_dayRangeLocked  = false;
bool      g_cutoffHit       = false;

SweepInfo g_sweep;
MSSInfo   g_mss;
FVG       g_fvgList[];
int       g_fvgSeqCounter   = 0;
bool      g_fvgSearchClosed = false; // stop searching for new FVGs once MSS invalidated/closing reached
double    g_unifiedTP       = 0;
bool      g_inputsValid     = true;

int       g_atrHandle = INVALID_HANDLE;
datetime  g_lastBarTime = 0;

#define OBJ_PREFIX "SB_"

//+------------------------------------------------------------------+
int OnInit()
{
   g_inputsValid = ValidateInputs();
   if(!g_inputsValid)
   {
      Comment("ICT SILVER BULLET: INVALID TIME INPUT FORMAT - USE HH:MM");
      return(INIT_SUCCEEDED);
   }

   trade.SetExpertMagicNumber(InpMagic);
   trade.SetDeviationInPoints(InpSlippage);

   g_atrHandle = iATR(_Symbol, PERIOD_CURRENT, InpATRPeriod);
   if(g_atrHandle == INVALID_HANDLE)
   {
      Print("Failed to create ATR handle");
      return(INIT_FAILED);
   }

   if(!IsOptimizationOrTester())
      ApplyChartStyle();

   ArrayResize(g_fvgList, 0);
   ResetDailyState(TimeCurrent());

   return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   Comment("");
   IndicatorRelease(g_atrHandle);
}

//+------------------------------------------------------------------+
bool IsOptimizationOrTester()
{
   return(MQLInfoInteger(MQL_OPTIMIZATION) || (MQLInfoInteger(MQL_TESTER) && !MQLInfoInteger(MQL_VISUAL_MODE)));
}

//+------------------------------------------------------------------+
// Input validation - all time inputs must be HH:MM
//+------------------------------------------------------------------+
bool ParseHHMM(const string s, int &h, int &m)
{
   string parts[];
   int n = StringSplit(s, ':', parts);
   if(n != 2) return(false);
   if(StringLen(parts[0]) != 2 || StringLen(parts[1]) != 2) return(false);
   if(!IsDigitsOnly(parts[0]) || !IsDigitsOnly(parts[1])) return(false);
   h = (int)StringToInteger(parts[0]);
   m = (int)StringToInteger(parts[1]);
   if(h < 0 || h > 23) return(false);
   if(m < 0 || m > 59) return(false);
   return(true);
}

bool IsDigitsOnly(const string s)
{
   for(int i = 0; i < StringLen(s); i++)
   {
      ushort c = StringGetCharacter(s, i);
      if(c < '0' || c > '9') return(false);
   }
   return(true);
}

bool ValidateInputs()
{
   int h, m;
   bool ok = true;
   if(!ParseHHMM(InpCutoffTime, h, m))  ok = false;
   if(!ParseHHMM(InpClosingTime, h, m)) ok = false;
   return(ok);
}

//+------------------------------------------------------------------+
datetime TodayAt(const string hhmm)
{
   int h, m;
   ParseHHMM(hhmm, h, m);
   MqlDateTime dt;
   TimeToStruct(TimeCurrent(), dt);
   dt.hour = h; dt.min = m; dt.sec = 0;
   return(StructToTime(dt));
}

datetime DayStartOf(datetime t)
{
   MqlDateTime dt;
   TimeToStruct(t, dt);
   dt.hour = 0; dt.min = 0; dt.sec = 0;
   return(StructToTime(dt));
}

//+------------------------------------------------------------------+
void OnTick()
{
   if(!g_inputsValid)
   {
      Comment("ICT SILVER BULLET: INVALID TIME INPUT FORMAT - USE HH:MM");
      return;
   }

   //--- every-tick section ---------------------------------------
   CheckFVGActivationAndOrders();
   ManageUnifiedTP();
   if(InpCloseAtClosing) CheckClosingTimeFlat();

   //--- once-per-new-candle section --------------------------------
   datetime curBarTime = iTime(_Symbol, PERIOD_CURRENT, 0);
   if(curBarTime == g_lastBarTime) return;
   g_lastBarTime = curBarTime;

   OnNewCandle();
}

//+------------------------------------------------------------------+
void OnNewCandle()
{
   datetime barTime = iTime(_Symbol, PERIOD_CURRENT, 1);
   datetime todayStart = DayStartOf(barTime);

   if(todayStart != g_dayStart)
      ResetDailyState(barTime);

   datetime cutoffDT = TodayAt(InpCutoffTime);
   if(!g_dayRangeLocked)
   {
      UpdateDayHighLow(barTime);
      if(barTime >= cutoffDT)
      {
         g_dayRangeLocked = true;
         g_cutoffHit = true;
      }
   }

   if(InpShowDayHighLow && !IsOptimizationOrTester())
      DrawDayLines();

   // Safety sweep: cancel any pending orders left over from a previous
   // day that survived broker-side cancellation at session close.
   SafetySweepStaleOrders();
   RecoverOrphanPositions();

   if(!g_dayRangeLocked) return; // nothing else until cutoff has locked the range

   if(!g_sweep.found)
      DetectLiquiditySweep();

   if(g_sweep.found && !g_mss.found)
      DetectMarketStructure();

   if(g_mss.found && !g_mss.confirmed && !g_mss.invalidated)
      CheckMSSConfirmation();

   if(g_mss.confirmed && !g_fvgSearchClosed)
      DetectFVGs();

   ExtendOpenFVGBoxes(barTime);
   CheckFVGInvalidation();

   CheckExpiry(barTime);
}

//+------------------------------------------------------------------+
void ResetDailyState(datetime t)
{
   g_dayStart = DayStartOf(t);
   g_dayHigh = -DBL_MAX;
   g_dayLow  = DBL_MAX;
   g_dayRangeLocked = false;
   g_cutoffHit = false;

   ZeroMemory(g_sweep);
   ZeroMemory(g_mss);

   ArrayResize(g_fvgList, 0);
   g_fvgSeqCounter = 0;
   g_fvgSearchClosed = false;
   g_unifiedTP = 0;
}

//+------------------------------------------------------------------+
void UpdateDayHighLow(datetime barTime)
{
   int shift = iBarShift(_Symbol, PERIOD_CURRENT, barTime);
   double h = iHigh(_Symbol, PERIOD_CURRENT, shift);
   double l = iLow(_Symbol, PERIOD_CURRENT, shift);
   if(h > g_dayHigh) g_dayHigh = h;
   if(l < g_dayLow)  g_dayLow  = l;
}

//+------------------------------------------------------------------+
void DrawDayLines()
{
   datetime cutoffDT = TodayAt(InpCutoffTime);
   string dayTag = TimeToString(g_dayStart, TIME_DATE);

   string hName = OBJ_PREFIX + "DayHigh_" + dayTag;
   string lName = OBJ_PREFIX + "DayLow_"  + dayTag;
   string vName = OBJ_PREFIX + "Cutoff_"  + dayTag;

   datetime endTime = g_dayStart + 86400 - 1;

   DrawHLineSeg(hName, g_dayStart, endTime, g_dayHigh, InpDayLineColor);
   DrawHLineSeg(lName, g_dayStart, endTime, g_dayLow,  InpDayLineColor);

   if(ObjectFind(0, vName) < 0)
   {
      ObjectCreate(0, vName, OBJ_TREND, 0, cutoffDT, g_dayLow, cutoffDT, g_dayHigh);
      ObjectSetInteger(0, vName, OBJPROP_COLOR, InpDayLineColor);
      ObjectSetInteger(0, vName, OBJPROP_STYLE, STYLE_DASH);
      ObjectSetInteger(0, vName, OBJPROP_WIDTH, 1);
      ObjectSetInteger(0, vName, OBJPROP_RAY, false);
      ObjectSetInteger(0, vName, OBJPROP_BACK, true);
      ObjectSetInteger(0, vName, OBJPROP_SELECTABLE, false);
   }
   else
   {
      ObjectMove(0, vName, 0, cutoffDT, g_dayLow);
      ObjectMove(0, vName, 1, cutoffDT, g_dayHigh);
   }
}

void DrawHLineSeg(string name, datetime t1, datetime t2, double price, color clr)
{
   if(ObjectFind(0, name) < 0)
   {
      ObjectCreate(0, name, OBJ_TREND, 0, t1, price, t2, price);
      ObjectSetInteger(0, name, OBJPROP_COLOR, clr);
      ObjectSetInteger(0, name, OBJPROP_STYLE, STYLE_DASH);
      ObjectSetInteger(0, name, OBJPROP_WIDTH, 1);
      ObjectSetInteger(0, name, OBJPROP_RAY, false);
      ObjectSetInteger(0, name, OBJPROP_BACK, true);
      ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
   }
   else
   {
      ObjectMove(0, name, 0, t1, price);
      ObjectMove(0, name, 1, t2, price);
   }
}

//+------------------------------------------------------------------+
// Step 2: Liquidity sweep - first valid sweep of the day only.
//+------------------------------------------------------------------+
void DetectLiquiditySweep()
{
   // shift 1 = last closed bar
   for(int shift = 1; shift <= InpMaxSweepCandles; shift++)
   {
      datetime t = iTime(_Symbol, PERIOD_CURRENT, shift);
      if(t < g_dayStart) break;

      double h = iHigh(_Symbol, PERIOD_CURRENT, shift);
      double l = iLow(_Symbol, PERIOD_CURRENT, shift);
      double c = iClose(_Symbol, PERIOD_CURRENT, shift);

      bool sweptHigh = (h > g_dayHigh) && (c <= g_dayHigh) && (c >= g_dayLow);
      bool sweptLow  = (l < g_dayLow)  && (c >= g_dayLow)  && (c <= g_dayHigh);

      if(sweptHigh)
      {
         g_sweep.found = true;
         g_sweep.isSellSetup = true;
         g_sweep.sweepShift = shift;
         g_sweep.sweepTime = t;
         DrawSweepArrow(t, h, true);
         return;
      }
      if(sweptLow)
      {
         g_sweep.found = true;
         g_sweep.isSellSetup = false;
         g_sweep.sweepShift = shift;
         g_sweep.sweepTime = t;
         DrawSweepArrow(t, l, false);
         return;
      }
   }
}

void DrawSweepArrow(datetime t, double price, bool isHighSweep)
{
   if(IsOptimizationOrTester()) return;
   string name = OBJ_PREFIX + "Sweep_" + TimeToString(t, TIME_DATE | TIME_MINUTES);
   double atr[];
   ArraySetAsSeries(atr, true);
   CopyBuffer(g_atrHandle, 0, 0, 1, atr);
   double buf = (ArraySize(atr) > 0 ? atr[0] : (g_dayHigh - g_dayLow) * 0.05) * 0.5;

   double y = isHighSweep ? price + buf : price - buf;
   ENUM_OBJECT type = isHighSweep ? OBJ_ARROW_DOWN : OBJ_ARROW_UP;
   color clr = isHighSweep ? clrRed : clrLime;

   ObjectCreate(0, name, type, 0, t, y);
   ObjectSetInteger(0, name, OBJPROP_COLOR, clr);
   ObjectSetInteger(0, name, OBJPROP_WIDTH, 3);
   ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
}

//+------------------------------------------------------------------+
// Step 3: Market structure - most recent fractal before the sweep,
// within the day's range, within InpMSSLookbackCandles.
//+------------------------------------------------------------------+
void DetectMarketStructure()
{
   int k = InpFractalStrength;
   int startShift = g_sweep.sweepShift + 1;
   int endShift = g_sweep.sweepShift + InpMSSLookbackCandles;

   for(int s = startShift; s <= endShift; s++)
   {
      datetime t = iTime(_Symbol, PERIOD_CURRENT, s + k);
      if(t < g_dayStart) break; // stay within today
      if(!IsFractalBarAvailable(s, k)) continue;

      double level;
      bool isFractal = g_sweep.isSellSetup
                        ? IsFractalHigh(s, k, level)
                        : IsFractalLow(s, k, level);

      if(!isFractal) continue;
      if(level > g_dayHigh || level < g_dayLow) continue; // must be inside day range

      g_mss.found = true;
      g_mss.level = level;
      g_mss.fractalTime = iTime(_Symbol, PERIOD_CURRENT, s);
      g_mss.confirmed = false;
      g_mss.invalidated = false;
      DrawMSSLine();
      return;
   }
}

bool IsFractalBarAvailable(int shift, int k)
{
   int oldest = shift + k;
   return(oldest < Bars(_Symbol, PERIOD_CURRENT));
}

bool IsFractalHigh(int shift, int k, double &level)
{
   double h = iHigh(_Symbol, PERIOD_CURRENT, shift);
   for(int i = 1; i <= k; i++)
   {
      if(iHigh(_Symbol, PERIOD_CURRENT, shift - i) >= h && shift - i >= 0) return(false); // newer side
      if(iHigh(_Symbol, PERIOD_CURRENT, shift + i) >= h) return(false); // older side
   }
   level = h;
   return(true);
}

bool IsFractalLow(int shift, int k, double &level)
{
   double l = iLow(_Symbol, PERIOD_CURRENT, shift);
   for(int i = 1; i <= k; i++)
   {
      if(shift - i >= 0 && iLow(_Symbol, PERIOD_CURRENT, shift - i) <= l) return(false);
      if(iLow(_Symbol, PERIOD_CURRENT, shift + i) <= l) return(false);
   }
   level = l;
   return(true);
}

void DrawMSSLine()
{
   if(IsOptimizationOrTester()) return;
   string tag = TimeToString(g_dayStart, TIME_DATE);
   g_mss.lineObj  = OBJ_PREFIX + "MSS_" + tag;
   g_mss.labelObj = OBJ_PREFIX + "MSSLbl_" + tag;

   datetime endTime = g_dayStart + 86400 - 1;
   DrawHLineSeg(g_mss.lineObj, g_mss.fractalTime, endTime, g_mss.level, InpMSSLineColor);
   ObjectSetInteger(0, g_mss.lineObj, OBJPROP_STYLE, STYLE_DASH);

   UpdateMSSLabel();
}

void UpdateMSSLabel()
{
   if(IsOptimizationOrTester()) return;
   string side = g_sweep.isSellSetup ? "MSS Sell" : "MSS Buy";
   string status = g_mss.confirmed ? "Confirmed" : "Unconfirmed";
   string text = side + " " + status;

   if(ObjectFind(0, g_mss.labelObj) < 0)
   {
      ObjectCreate(0, g_mss.labelObj, OBJ_TEXT, 0, g_mss.fractalTime, g_mss.level);
      ObjectSetInteger(0, g_mss.labelObj, OBJPROP_COLOR, InpMSSLineColor);
      ObjectSetInteger(0, g_mss.labelObj, OBJPROP_SELECTABLE, false);
   }
   ObjectSetString(0, g_mss.labelObj, OBJPROP_TEXT, text);
}

//+------------------------------------------------------------------+
// Step 4: MSS confirmation - candle must CLOSE through the level.
//+------------------------------------------------------------------+
void CheckMSSConfirmation()
{
   double c = iClose(_Symbol, PERIOD_CURRENT, 1);
   bool closedThrough = g_sweep.isSellSetup ? (c < g_mss.level) : (c > g_mss.level);

   if(closedThrough)
   {
      g_mss.confirmed = true;
      UpdateMSSLabel();
      return;
   }

   if(InpMSSConfirmMaxCandles > 0)
   {
      int barsFromSweep = iBarShift(_Symbol, PERIOD_CURRENT, g_sweep.sweepTime)
                           - iBarShift(_Symbol, PERIOD_CURRENT, iTime(_Symbol, PERIOD_CURRENT, 1)) + 1;
      if(barsFromSweep > InpMSSConfirmMaxCandles)
      {
         g_mss.invalidated = true;
         g_fvgSearchClosed = true;
      }
   }
}

//+------------------------------------------------------------------+
// Step 5: FVG detection - 3-candle gap, scanned from the sweep candle
// onward, filtered by ATR size and day-range overlap.
//+------------------------------------------------------------------+
void DetectFVGs()
{
   int sweepShift = g_sweep.sweepShift;
   double atr[];
   ArraySetAsSeries(atr, true);
   CopyBuffer(g_atrHandle, 0, 0, 1, atr);
   double atrVal = (ArraySize(atr) > 0) ? atr[0] : 0;
   double minSize = InpFVGMinSizeATRMult > 0 ? atrVal * InpFVGMinSizeATRMult : 0;
   double maxSize = InpFVGMaxSizeATRMult > 0 ? atrVal * InpFVGMaxSizeATRMult : DBL_MAX;

   bool wantBullish = !g_sweep.isSellSetup;

   for(int shift = sweepShift; shift >= 1; shift--)
   {
      // 3-candle pattern uses shift+2 (oldest), shift+1 (middle), shift (newest)
      int i2 = shift + 2, i1 = shift + 1, i0 = shift;
      if(i2 >= Bars(_Symbol, PERIOD_CURRENT)) continue;

      double upper, lower;
      bool isBull;

      double h2 = iHigh(_Symbol, PERIOD_CURRENT, i2);
      double l2 = iLow(_Symbol, PERIOD_CURRENT, i2);
      double h0 = iHigh(_Symbol, PERIOD_CURRENT, i0);
      double l0 = iLow(_Symbol, PERIOD_CURRENT, i0);

      bool foundGap = false;
      if(wantBullish && h2 < l0)
      {
         upper = l0; lower = h2; isBull = true; foundGap = true;
      }
      else if(!wantBullish && l2 > h0)
      {
         upper = l2; lower = h0; isBull = false; foundGap = true;
      }

      if(!foundGap) continue;

      double width = upper - lower;
      if(width < minSize) continue;
      if(width > maxSize) continue;
      if(lower > g_dayHigh || upper < g_dayLow) continue; // must overlap day range

      datetime gapTime = iTime(_Symbol, PERIOD_CURRENT, i1);
      if(FVGAlreadyTracked(gapTime)) continue;

      AddFVG(isBull, upper, lower, gapTime);
   }
}

bool FVGAlreadyTracked(datetime t)
{
   for(int i = 0; i < ArraySize(g_fvgList); i++)
      if(g_fvgList[i].createdTime == t) return(true);
   return(false);
}

void AddFVG(bool isBull, double upper, double lower, datetime t)
{
   int n = ArraySize(g_fvgList);
   ArrayResize(g_fvgList, n + 1);
   g_fvgList[n].isBullish = isBull;
   g_fvgList[n].upper = upper;
   g_fvgList[n].lower = lower;
   g_fvgList[n].midpoint = (upper + lower) / 2.0;
   g_fvgList[n].createdTime = t;
   g_fvgList[n].state = FVG_PENDING;
   g_fvgList[n].sequence = g_fvgSeqCounter++;
   g_fvgList[n].orderTicket = 0;
   g_fvgList[n].positionTicket = 0;
   g_fvgList[n].lotSize = 0;
   g_fvgList[n].riskMoney = 0;
   g_fvgList[n].slPrice = 0;
   g_fvgList[n].objName = OBJ_PREFIX + "FVG_" + TimeToString(t, TIME_DATE | TIME_MINUTES) + "_" + IntegerToString(n);

   DrawFVGBox(g_fvgList[n]);
}

void DrawFVGBox(FVG &f)
{
   if(IsOptimizationOrTester()) return;
   datetime t1 = f.createdTime;
   datetime t2 = t1 + PeriodSeconds(PERIOD_CURRENT); // grown each candle via ExtendOpenFVGBoxes

   ObjectCreate(0, f.objName, OBJ_RECTANGLE, 0, t1, f.upper, t2, f.lower);
   color clr = GetFVGColor(f);
   ObjectSetInteger(0, f.objName, OBJPROP_COLOR, clr);
   ObjectSetInteger(0, f.objName, OBJPROP_FILL, true);
   ObjectSetInteger(0, f.objName, OBJPROP_BACK, true);
   ObjectSetInteger(0, f.objName, OBJPROP_SELECTABLE, false);
}

color GetFVGColor(FVG &f)
{
   if(f.state == FVG_INVALIDATED) return(clrGray);
   return(f.isBullish ? InpBullishFVGColor : InpBearishFVGColor);
}

void RedrawFVG(FVG &f)
{
   if(IsOptimizationOrTester()) return;
   if(ObjectFind(0, f.objName) < 0) return;
   ObjectSetInteger(0, f.objName, OBJPROP_COLOR, GetFVGColor(f));
}

// Extend the box's right edge to the current bar while still pending or
// active; freeze it in place once triggered, invalidated, or expired.
void ExtendOpenFVGBoxes(datetime barTime)
{
   if(IsOptimizationOrTester()) return;
   for(int i = 0; i < ArraySize(g_fvgList); i++)
   {
      if(g_fvgList[i].state != FVG_PENDING && g_fvgList[i].state != FVG_ACTIVE) continue;
      if(ObjectFind(0, g_fvgList[i].objName) < 0) continue;
      ObjectMove(0, g_fvgList[i].objName, 1, barTime, g_fvgList[i].lower);
   }
}

//+------------------------------------------------------------------+
// Step 6-9: activation, pending order placement, invalidation,
// risk-decayed sizing, unified TP.
//+------------------------------------------------------------------+
void CheckFVGActivationAndOrders()
{
   if(!g_mss.confirmed) return;
   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);

   for(int i = 0; i < ArraySize(g_fvgList); i++)
   {
      if(g_fvgList[i].state != FVG_PENDING) continue;

      bool midHit = g_fvgList[i].isBullish ? (bid <= g_fvgList[i].midpoint)
                                            : (ask >= g_fvgList[i].midpoint);
      if(!midHit) continue;

      if(CountOpenOrPendingTrades() >= InpMaxTradesPerEA) continue;
      if(CountOpenOrPendingTradesForSymbol() >= InpMaxTradesPerSymbol) continue;

      PlacePendingOrderForFVG(g_fvgList[i]);
   }
}

int CountOpenOrPendingTrades()
{
   int n = 0;
   for(int i = 0; i < ArraySize(g_fvgList); i++)
      if(g_fvgList[i].state == FVG_ACTIVE || g_fvgList[i].state == FVG_TRIGGERED) n++;
   return(n);
}

int CountOpenOrPendingTradesForSymbol()
{
   return(CountOpenOrPendingTrades()); // single-symbol EA instance
}

void PlacePendingOrderForFVG(FVG &f)
{
   double width = f.upper - f.lower;
   double buffer = width * InpSLBufferWidthMult;

   double riskPct = InpRiskPercent * MathPow(InpRiskDecayFactor, f.sequence);
   double riskMoney = AccountInfoDouble(ACCOUNT_BALANCE) * riskPct / 100.0;

   double entryPrice, slPrice;
   ENUM_ORDER_TYPE orderType;

   if(f.isBullish)
   {
      entryPrice = f.upper;
      slPrice = f.lower - buffer;
      orderType = ORDER_TYPE_BUY_STOP;
   }
   else
   {
      entryPrice = f.lower;
      slPrice = f.upper + buffer;
      orderType = ORDER_TYPE_SELL_STOP;
   }

   double slDistance = MathAbs(entryPrice - slPrice);
   double lot = CalcLotSize(riskMoney, slDistance);
   if(lot <= 0) return;

   double tpPrice = f.isBullish ? entryPrice + slDistance * InpRiskRewardRatio
                                 : entryPrice - slDistance * InpRiskRewardRatio;

   string comment = "SB_FVG_" + IntegerToString(f.sequence);
   bool ok = trade.OrderOpen(_Symbol, orderType, lot, 0, NormalizePrice(entryPrice),
                              NormalizePrice(slPrice), NormalizePrice(tpPrice),
                              ORDER_TIME_GTC, 0, comment);
   if(!ok)
   {
      Print("FVG order failed: ", trade.ResultRetcodeDescription());
      return;
   }

   f.state = FVG_ACTIVE;
   f.orderTicket = trade.ResultOrder();
   f.lotSize = lot;
   f.riskMoney = riskMoney;
   f.slPrice = slPrice;
}

double NormalizePrice(double price)
{
   int digits = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);
   return(NormalizeDouble(price, digits));
}

double CalcLotSize(double riskMoney, double slDistance)
{
   double tickValue = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE);
   double tickSize  = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   if(tickSize <= 0 || tickValue <= 0 || slDistance <= 0) return(0);

   double lossPerLot = (slDistance / tickSize) * tickValue;
   if(lossPerLot <= 0) return(0);

   double lot = riskMoney / lossPerLot;

   double minLot  = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double maxLot  = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
   double lotStep = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);

   lot = MathFloor(lot / lotStep) * lotStep;
   lot = MathMax(minLot, MathMin(maxLot, lot));
   return(lot);
}

//+------------------------------------------------------------------+
// Invalidation: price activated the FVG, then closed beyond the far
// boundary -> cancel the order, mark gray, stop trading that FVG.
//+------------------------------------------------------------------+
void CheckFVGInvalidation()
{
   double c = iClose(_Symbol, PERIOD_CURRENT, 1);

   for(int i = 0; i < ArraySize(g_fvgList); i++)
   {
      if(g_fvgList[i].state != FVG_ACTIVE) continue;

      bool broken = g_fvgList[i].isBullish ? (c < g_fvgList[i].lower)
                                            : (c > g_fvgList[i].upper);
      if(!broken) continue;

      if(g_fvgList[i].orderTicket != 0 && ordInfo.Select(g_fvgList[i].orderTicket))
         trade.OrderDelete(g_fvgList[i].orderTicket);

      g_fvgList[i].state = FVG_INVALIDATED;
      RedrawFVG(g_fvgList[i]);
   }
}

//+------------------------------------------------------------------+
// Mark FVGs whose pending order has been filled (becomes a position).
//+------------------------------------------------------------------+
void OnTradeTransaction(const MqlTradeTransaction &trans,
                         const MqlTradeRequest &request,
                         const MqlTradeResult &result)
{
   if(trans.type != TRADE_TRANSACTION_DEAL_ADD) return;

   for(int i = 0; i < ArraySize(g_fvgList); i++)
   {
      if(g_fvgList[i].state != FVG_ACTIVE) continue;
      if(g_fvgList[i].orderTicket == 0) continue;
      if(trans.order != g_fvgList[i].orderTicket) continue;

      g_fvgList[i].state = FVG_TRIGGERED;
      g_fvgList[i].positionTicket = trans.position;
   }
}

//+------------------------------------------------------------------+
// Unified TP across all triggered positions for the day's setup,
// re-targeted to the combined dollar risk * risk:reward ratio.
//+------------------------------------------------------------------+
void ManageUnifiedTP()
{
   double totalRisk = 0, sumEntryLot = 0, sumLot = 0;
   bool isBuy = !g_sweep.isSellSetup;
   int count = 0;

   for(int i = 0; i < ArraySize(g_fvgList); i++)
   {
      if(g_fvgList[i].state != FVG_TRIGGERED) continue;
      if(!posInfo.SelectByTicket(g_fvgList[i].positionTicket)) continue;

      totalRisk += g_fvgList[i].riskMoney;
      sumEntryLot += posInfo.PriceOpen() * posInfo.Volume();
      sumLot += posInfo.Volume();
      count++;
   }

   if(count == 0 || sumLot <= 0) return;

   double tickValue = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE);
   double tickSize  = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   if(tickSize <= 0 || tickValue <= 0) return;
   double k = tickValue / tickSize; // $ per unit price per lot

   double targetProfit = totalRisk * InpRiskRewardRatio;
   double newTP;
   if(isBuy)
      newTP = (sumEntryLot + targetProfit / k) / sumLot;
   else
      newTP = (sumEntryLot - targetProfit / k) / sumLot;

   newTP = NormalizePrice(newTP);
   if(MathAbs(newTP - g_unifiedTP) < SymbolInfoDouble(_Symbol, SYMBOL_POINT)) return;
   g_unifiedTP = newTP;

   for(int i = 0; i < ArraySize(g_fvgList); i++)
   {
      if(g_fvgList[i].state != FVG_TRIGGERED) continue;
      if(!posInfo.SelectByTicket(g_fvgList[i].positionTicket)) continue;
      trade.PositionModify(g_fvgList[i].positionTicket, posInfo.StopLoss(), newTP);
   }
}

//+------------------------------------------------------------------+
// 9.1: safety sweep - cancel pending orders that survived from a
// previous day (e.g. broker was closed when our EOD cancel was sent).
// Runs every candle from day start until the cutoff as a grace period.
//+------------------------------------------------------------------+
void SafetySweepStaleOrders()
{
   if(g_cutoffHit) return;

   for(int i = OrdersTotal() - 1; i >= 0; i--)
   {
      ulong ticket = OrderGetTicket(i);
      if(ticket == 0 || !ordInfo.Select(ticket)) continue;
      if(ordInfo.Magic() != InpMagic) continue;
      if(ordInfo.Symbol() != _Symbol) continue;
      if(ordInfo.Time() >= g_dayStart) continue; // belongs to today, leave it
      trade.OrderDelete(ticket);
   }
}

//+------------------------------------------------------------------+
// 9.2: if a position survived without our internal tracking (e.g. the
// EA believed it cancelled the order before the fill), give it a TP.
//+------------------------------------------------------------------+
void RecoverOrphanPositions()
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0 || !posInfo.SelectByTicket(ticket)) continue;
      if(posInfo.Magic() != InpMagic) continue;
      if(posInfo.Symbol() != _Symbol) continue;
      if(posInfo.TakeProfit() > 0) continue; // already has a TP

      bool tracked = false;
      for(int j = 0; j < ArraySize(g_fvgList); j++)
         if(g_fvgList[j].positionTicket == ticket) { tracked = true; break; }
      if(tracked) continue;

      double entry = posInfo.PriceOpen();
      double sl = posInfo.StopLoss();
      if(sl == 0) continue;
      double slDist = MathAbs(entry - sl);
      double tp = (posInfo.PositionType() == POSITION_TYPE_BUY)
                  ? entry + slDist * InpRiskRewardRatio
                  : entry - slDist * InpRiskRewardRatio;
      trade.PositionModify(ticket, sl, NormalizePrice(tp));
   }
}

//+------------------------------------------------------------------+
void CheckExpiry(datetime barTime)
{
   datetime closingDT = TodayAt(InpClosingTime);
   bool isMidnightDefault = (InpClosingTime == "00:00");
   datetime expiryDT = isMidnightDefault ? (g_dayStart + 86400) : closingDT;

   if(barTime < expiryDT) return;

   for(int i = 0; i < ArraySize(g_fvgList); i++)
   {
      if(g_fvgList[i].state != FVG_PENDING && g_fvgList[i].state != FVG_ACTIVE) continue;
      if(g_fvgList[i].orderTicket != 0 && ordInfo.Select(g_fvgList[i].orderTicket))
         trade.OrderDelete(g_fvgList[i].orderTicket);
      g_fvgList[i].state = FVG_EXPIRED;
   }
}

void CheckClosingTimeFlat()
{
   bool isMidnightDefault = (InpClosingTime == "00:00");
   if(isMidnightDefault) return; // end-of-day handled naturally by new-day reset

   datetime closingDT = TodayAt(InpClosingTime);
   if(TimeCurrent() < closingDT) return;

   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0 || !posInfo.SelectByTicket(ticket)) continue;
      if(posInfo.Magic() != InpMagic || posInfo.Symbol() != _Symbol) continue;
      trade.PositionClose(ticket);
   }
}

//+------------------------------------------------------------------+
// Chart styling: no grid, custom candle colors, gradient background.
//+------------------------------------------------------------------+
void ApplyChartStyle()
{
   ChartSetInteger(0, CHART_SHOW_GRID, false);

   if(InpRecolorCandles)
   {
      ChartSetInteger(0, CHART_COLOR_CANDLE_BULL, InpBullCandleColor);
      ChartSetInteger(0, CHART_COLOR_CANDLE_BEAR, InpBearCandleColor);
      ChartSetInteger(0, CHART_COLOR_CHART_UP, InpBullCandleColor);
      ChartSetInteger(0, CHART_COLOR_CHART_DOWN, InpBearCandleColor);
      ChartSetInteger(0, CHART_COLOR_CHART_LINE, InpBullCandleColor);
   }

   DrawGradientBackground();
}

void DrawGradientBackground()
{
   int bands = 24;
   long height = ChartGetInteger(0, CHART_HEIGHT_IN_PIXELS);
   if(height <= 0) height = 600;
   int bandHeight = (int)(height / bands) + 1;

   for(int i = 0; i < bands; i++)
   {
      string name = OBJ_PREFIX + "GradBand_" + IntegerToString(i);
      double t = (double)i / (bands - 1);
      color c = LerpColor(clrBlack, C'10,20,60', t); // black to deep blue, mirrors prior EA's gradient

      if(ObjectFind(0, name) < 0)
      {
         ObjectCreate(0, name, OBJ_RECTANGLE_LABEL, 0, 0, 0);
         ObjectSetInteger(0, name, OBJPROP_XDISTANCE, 0);
         ObjectSetInteger(0, name, OBJPROP_XSIZE, 4000);
         ObjectSetInteger(0, name, OBJPROP_BACK, true);
         ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
         ObjectSetInteger(0, name, OBJPROP_CORNER, CORNER_LEFT_UPPER);
         ObjectSetInteger(0, name, OBJPROP_ZORDER, -100);
      }
      ObjectSetInteger(0, name, OBJPROP_YDISTANCE, i * bandHeight);
      ObjectSetInteger(0, name, OBJPROP_YSIZE, bandHeight + 1);
      ObjectSetInteger(0, name, OBJPROP_BGCOLOR, c);
      ObjectSetInteger(0, name, OBJPROP_COLOR, c);
   }
   ChartRedraw(0);
}

color LerpColor(color c1, color c2, double t)
{
   int r1 = (int)(c1 & 0xFF), g1 = (int)((c1 >> 8) & 0xFF), b1 = (int)((c1 >> 16) & 0xFF);
   int r2 = (int)(c2 & 0xFF), g2 = (int)((c2 >> 8) & 0xFF), b2 = (int)((c2 >> 16) & 0xFF);
   int r = (int)(r1 + (r2 - r1) * t);
   int g = (int)(g1 + (g2 - g1) * t);
   int b = (int)(b1 + (b2 - b1) * t);
   return((color)(r | (g << 8) | (b << 16)));
}

void OnChartEvent(const int id, const long &lparam, const double &dparam, const string &sparam)
{
   if(id == CHARTEVENT_CHART_CHANGE && !IsOptimizationOrTester())
      DrawGradientBackground();
}
//+------------------------------------------------------------------+
