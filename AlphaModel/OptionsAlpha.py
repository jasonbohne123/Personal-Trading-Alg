#This code is entirely original

from clr import AddReference
AddReference("QuantConnect.Common")
AddReference("QuantConnect.Algorithm")
AddReference("QuantConnect.Algorithm.Framework")
AddReference("QuantConnect.Indicators")

class alpha(AlphaModel):   
    def __init__(self,period = 75,resolution = Resolution.Daily):
      
        self.period = period
        self.resolution = resolution
        self.insightPeriod = Time.Multiply(Extensions.ToTimeSpan(resolution), period)
        self.symbolDataBySymbol ={} # this is just an dictcionary
        self.optionDataBySymbol ={}
        self.removed=[]
        
        resolutionString = Extensions.GetEnumString(resolution, Resolution)
        self.Name = '{}({},{})'.format(self.__class__.__name__, period, resolutionString)
        self.day=None
        
        
    def Update(self, algorithm, data):
   
        insights=[]
        
        if algorithm.Time.day == self.day:
            return []
        #Currently we only want to emit insights once a day
     
        
        for symbol, symbolData in self.symbolDataBySymbol.items():
            
            value = algorithm.Securities[symbol].Price
            std=symbolData.STD
            ema=symbolData.EMA
            #Initalizes our indicators and contracts
            putcontract=None
            callcontract=None
            
            
  
            
            for contract ,info in self.optionDataBySymbol.items():
          
                #Set each contract as either a put or call as we pull both
                if info.Underlying.Value==symbol.Value and info.Right=="put":
                    putcontract=contract
             
                if info.Underlying.Value==symbol.Value and info.Right=="call":
                    callcontract=contract
                  
            
                
            if value< (ema.Current.Value-std.Current.Value):
                insights.append(Insight.Price(symbol, timedelta(days=1), InsightDirection.Up, 0.0025, 1.00,"Options", .5))
                
                #If we are longing equity and have not already bought a put contract and one exists buy one
                if putcontract is not None and not algorithm.Portfolio[putcontract].Invested:
                    insights.append(Insight.Price(putcontract, timedelta(days=1), InsightDirection.Up, 0.0025, 1.00,"Options", .5))
                    algorithm.Log(str(putcontract))
                    
                   #If we are trying to buy a put and we already have a call on the equity , we should sell it
                    if callcontract is not None and algorithm.Portfolio[callcontract].Invested:
                        insights.append(Insight.Price(callcontract, timedelta(days=1), InsightDirection.Flat,0.0025, 1.00,"ReversiontotheMean", .5))
                        
             
                     
            elif value> (ema.Current.Value+std.Current.Value):
            
                insights.append(Insight.Price(symbol, timedelta(days=1), InsightDirection.Down,0.0025, 1.00,"Options", .5))
                
                #If we are shorting equity and have not already bought a put contract and one exists buy one  
                if callcontract is not None and not algorithm.Portfolio[callcontract].Invested:

                 
                    insights.append(Insight.Price(callcontract, timedelta(days=1), InsightDirection.Up, 0.0025, 1.00,"Options", .5))
                    algorithm.Log(str(callcontract))
                    
                    #If we are trying to buy a call and we already have a put on the equity , we should sell it
                    if  putcontract is not None and algorithm.Portfolio[putcontract].Invested:
                        insights.append(Insight.Price(putcontract ,timedelta(days=1), InsightDirection.Flat,0.0025, 1.00,"ReversiontotheMean", .5))
            
            else:
                insights.append(Insight.Price(symbol, timedelta(days=1), InsightDirection.Flat,0.0025, 1.00,"ReversiontotheMean", .5))
                  
        return insights
            


    def OnSecuritiesChanged(self, algorithm, changes):
      
 
                    
        for y in  changes.RemovedSecurities:
     
            #There are two ways which we can remove options
            
            #1 if an equity is no longer in our universe remove it and corresponding equity
            if y.Symbol.SecurityType ==SecurityType.Equity:   
                self.removed.clear()
                for contract ,info in self.optionDataBySymbol.items():
                    
                    
                   if info.Underlying==y.Symbol.Value:
                        self.removed.append(contract)
                       #pull all options with equity underlying it and add to self.removed
                   
               
                for x in self.removed :
                    
                    optionData=self.optionDataBySymbol.pop(x,None)
                   #if optionData:
                       # algorithm.SubscriptionManager.RemoveConsolidator(x, optionData.consolidator)
                       #liquidate and remove options all at once
                    
                symbolData = self.symbolDataBySymbol.pop(y.Symbol, None)
               
               # if symbolData:
                   # algorithm.SubscriptionManager.RemoveConsolidator(y.Symbol, symbolData.EMAconsol)
                   # algorithm.SubscriptionManager.RemoveConsolidator(y.Symbol, symbolData.STDconsol)
            
            #If the option is no longer the desired one and we also arent removing the equity remove it
            elif y.Symbol.SecurityType ==SecurityType.Option:
          
                if y.Underlying not in [x.Symbol for x in changes.RemovedSecurities]:
                   
                    optionData=self.optionDataBySymbol.pop(y.Symbol,None)
                   
                   # if optionData:
                       # algorithm.SubscriptionManager.RemoveConsolidator(y.Symbol, optionData.consolidator)#liquidate and remove options all at once
                    
      
                    
       
   
      
        addedSymbols = [ x.Symbol for x in changes.AddedSecurities if (x.Symbol not in self.symbolDataBySymbol and x.Symbol.SecurityType ==SecurityType.Equity)]
     
        #makes symbol instance for new equities in our universe
        if len(addedSymbols) == 0: return
        #if no new symbols we do not need to generate any new instances
        
        history = algorithm.History(addedSymbols, self.period, self.resolution)
        #pulls history for all new symbols
 
        for symbol in addedSymbols:

            std=algorithm.STD(symbol, self.period, self.resolution)

            ema=algorithm.EMA(symbol, self.period, self.resolution)
        
            #for each new symbol, generate an instance of the indicator std and ema
            
            if not history.empty:
                ticker = SymbolCache.GetTicker(symbol)
                #if history isnt empty set the ticker as the symbol
  
                
                for tuple in history.loc[ticker].itertuples():
                    ema.Update(tuple.Index, tuple.close)
                    std.Update(tuple.Index, tuple.close)
      
            
            self.symbolDataBySymbol[symbol] = SymbolData(symbol, ema,std)
   
            
        options= [ x.Symbol for x in changes.AddedSecurities if (x.Symbol not in self.optionDataBySymbol and x.Symbol.SecurityType ==SecurityType.Option)]
        if len(options) == 0: return

        # pulls options instances
        newhistory = algorithm.History(options, self.period, Resolution.Minute)
        #Need resolution.Minute for options to show up insights
        if  newhistory.empty: return
        #if no new symbols we do not need to generate any new instances
        
        
        for contract in options:
            # for each new option, add to algorithm, save underlying and type of contract

            underlying=contract.Underlying
           
            if contract.ID.OptionRight ==OptionRight.Call:
                right="call"
            elif contract.ID.OptionRight ==OptionRight.Put:
                right="put"
          
            self.optionDataBySymbol[contract] = OptionData(contract,underlying,right)
       #Records Option Data instance of each contract underlying symbol along with it being a put or call
  
class SymbolData:
    '''Contains data specific to a symbol required by this model'''
    def __init__(self, symbol, ema ,std):
        self.Symbol = symbol
        self.EMA  = ema
        self.STD=std
        
class OptionData:
    '''Contains data specific to a symbol required by this model'''
    def __init__(self,contract, underlying,right):
        self.Contract=contract
        self.Underlying=underlying
        self.Right=right
