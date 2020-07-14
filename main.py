#The following is the main file of my live trading algorithm built through QuantConnect's IDE

from CustomUniverse import  StableUniverse
from CustomAlpha import ReversiontotheMean,VolatilityAlpha1
from RiskManagement import takeprofit

class ReversionAlg1Live(QCAlgorithm):



    def Initialize(self):
        self.SetStartDate(2019,4,1)  
        self.SetEndDate(2020,4,3)
        self.SetCash(100000)  # Set Strategy Cash
        self.SetTimeZone(TimeZones.Chicago)

        #self.SetBrokerageModel(BrokerageName.InteractiveBrokersBrokerage, AccountType.Margin)
        self.AddUniverseSelection(StableUniverse.Stable(self)) 
        #Calls Universe class
    
        self.UniverseSettings.Resolution = Resolution.Minute #Resolution of data being analyzed by universe selection (Later need to switch to hour/minute)
        self.UniverseSettings.DataNormalizationMode=DataNormalizationMode.Raw #how data goes into alg
        self.UniverseSettings.FillForward = True #Fill in empty data will next price
        self.UniverseSettings.ExtendedMarketHours = False #Takes in account after hours data
        self.UniverseSettings.MinimumTimeInUniverse = 1 # each equity has to spend at least 1 hour in universe selection process
        self.UniverseSettings.Leverage=2
       
        self.Settings.FreePortfolioValuePercentage = .5
        
       
        #In the below code we add spy index and bond to use as a means of comparison  at minute resolution
        spy="SPY"
        self.spy=self.AddEquity(spy,Resolution.Minute)
        self.spy.SetDataNormalizationMode(DataNormalizationMode.Raw)
        
        bnd="BND"
        self.bnd=self.AddEquity(bnd, Resolution.Minute)
        self.bnd.SetDataNormalizationMode(DataNormalizationMode.Raw)
        self.SetBenchmark(spy)
        
      
        self.AddAlpha( ReversiontotheMean.example())
 
       
         # we do not want to rebalance on insight changes
        self.Settings.RebalancePortfolioOnInsightChanges = False;
        # we want to rebalance only on security changes
        self.Settings.RebalancePortfolioOnSecurityChanges = True;
        
        #Remaining Modules below 
        
        #The Portfolio Construction Module is one of QC's default models
        self.SetPortfolioConstruction(EqualWeightingPortfolioConstructionModel())
  
        self.SetRiskManagement(takeprofit.TrailingStopRiskManagementModel())
    
        #The execution model was extended from one of QC's default model
        self.SetExecution(ImmediateExecutionModel())

      
        self.Schedule.On(self.DateRules.Every(DayOfWeek.Monday, DayOfWeek.Tuesday,DayOfWeek.Wednesday,DayOfWeek.Thursday,DayOfWeek.Friday) ,self.TimeRules.At(15,0), self.SpecificTime)
        self.Schedule.On(self.DateRules.Every(DayOfWeek.Monday, DayOfWeek.Tuesday,DayOfWeek.Wednesday,DayOfWeek.Thursday,DayOfWeek.Friday) ,self.TimeRules.At(15, 0), self.SpecificTimeone)
        self.Schedule.On(self.DateRules.Every(DayOfWeek.Monday, DayOfWeek.Tuesday,DayOfWeek.Wednesday,DayOfWeek.Thursday,DayOfWeek.Friday) ,self.TimeRules.At(8, 30), self.SpecificTimetwo)
        self.Schedule.On(self.DateRules.Every(DayOfWeek.Monday, DayOfWeek.Tuesday,DayOfWeek.Wednesday,DayOfWeek.Thursday,DayOfWeek.Friday) ,self.TimeRules.At(8, 30), self.SpecificTimethree)
    
    def OnData(self, slice):
        if self.IsWarmingUp: return 
    def SpecificTime(self):
        self.Notify.Sms("+16303838754","Cash: $"+str(round(self.Portfolio.Cash,2))+ " Total Portfolio Value:  $"+ str(round(self.Portfolio.TotalPortfolioValue,2 ))+ "Total Profit: $"+ str(round(self.Portfolio.TotalProfit,2))+"Total Unrealized Profit: $"+str(round(self.Portfolio.TotalUnrealizedProfit,2)))
        return
    def SpecificTimeone(self):
      self.Notify.Sms("+17735103304","Cash: $"+str(round(self.Portfolio.Cash,2))+ " Total Portfolio Value:  $"+ str(round(self.Portfolio.TotalPortfolioValue,2 ))+ "Total Profit: $"+ str(round(self.Portfolio.TotalProfit,2))+"Total Unrealized Profit: $"+str(round(self.Portfolio.TotalUnrealizedProfit,2)))
      return
    def SpecificTimetwo(self):
        self.Notify.Sms("+16303838754","Alg is Running")
        return
    def SpecificTimethree(self):
        self.Notify.Sms("+17735103304","Alg is Running")
        return
