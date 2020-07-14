#This file is equivalent to stable universe when selecting equities except we also pull the corresponding option to hedge our position 
#at a given strike price and expiration date out

from QuantConnect.Data.UniverseSelection import * 
from Selection.FundamentalUniverseSelectionModel import FundamentalUniverseSelectionModel 
from QuantConnect.Data.Custom.SEC import *
from Selection.OptionUniverseSelectionModel import OptionUniverseSelectionModel

from datetime import timedelta, datetime
from math import ceil
from itertools import chain
import numpy as np
#imports necessary packages

class universe(FundamentalUniverseSelectionModel):

    def __init__(self, filterFineData = True, universeSettings = None, securityInitializer = None):
        super().__init__(filterFineData, universeSettings, securityInitializer)

        # Number of stocks in Coarse Universe
        self.NumberOfSymbolsCoarse = 2500
        # Number of sorted stocks in the fine selection subset using the valuation ratio, EV to EBITDA (EV/EBITDA)
        self.NumberOfSymbolsFine =  250
        # Final number of stocks in security list, after sorted by the valuation ratio, Return on Assets (ROA)
        self.NumberOfSymbolsInPortfolio =5
       
        self.lastmonth = -1
        self.dollarVolumeBySymbol = {}
        
 

    def SelectCoarse(self, algorithm, coarse):
      
        month= algorithm.Time.month
        if month == self.lastmonth:
            return Universe.Unchanged
        self.lastmonth= month

        # sort the stocks by dollar volume and take the top 2000
        top = sorted([x for x in coarse if x.HasFundamentalData],
                    key=lambda x: x.DollarVolume, reverse=True)[:self.NumberOfSymbolsCoarse]
        
        #assigns all the stocks from price to dollarVolumeBySymbol
        self.dollarVolumeBySymbol = { i.Symbol: i.DollarVolume for i in top }

        return list(self.dollarVolumeBySymbol.keys())
    

    def SelectFine(self, algorithm, fine):
        
        
       
        self.debttoequityMaxAllowance =  0.8
        self.priceAllowance = 30

        # QC500:
        ## The company's headquarter must in the U.S. 
        ## The stock must be traded on either the NYSE or NASDAQ 
        ## At least half a year since its initial public offering 
        ## The stock's market cap must be greater than 500 million 
        ## We want the stock's debt to equity ratio to be relatively low to enssure we are investing in stable companies
    
        filteredFine = [x for x in fine if x.CompanyReference.CountryId == "USA"
                                        and x.Price > self.priceAllowance
                                        and (x.CompanyReference.PrimaryExchangeID == "NYS" or x.CompanyReference.PrimaryExchangeID == "NAS")
                                        and (algorithm.Time - x.SecurityReference.IPODate).days > 180
                                        #and x.FinancialStatements.CashFlowStatement.ProvisionandWriteOffofAssets.ThreeMonths != 0
                                        and (x.EarningReports.BasicAverageShares.ThreeMonths * x.EarningReports.BasicEPS.TwelveMonths * x.ValuationRatios.PERatio > 5e8)
                                        and 0 <= (x.OperationRatios.TotalDebtEquityRatioGrowth.OneYear) <= self.debttoequityMaxAllowance #this value will change in accordance to S&P Momentum
                                        and x.FinancialStatements.BalanceSheet.AllowanceForDoubtfulAccountsReceivable.ThreeMonths <= 2.0 * x.FinancialStatements.CashFlowStatement.ProvisionandWriteOffofAssets.ThreeMonths
                                        and (x.FinancialStatements.IncomeStatement.ProvisionForDoubtfulAccounts.TwoMonths <= 1.0*x.FinancialStatements.CashFlowStatement.ProvisionandWriteOffofAssets.ThreeMonths)
                
                                    ]
       
            
      
        count = len(filteredFine)
        if count == 0: return []

        myDict = dict()
        percent = self.NumberOfSymbolsFine / count

        # select stocks with top dollar volume in every single sector
        # N=Normal (Manufacturing), M=Mining, U=Utility, T=Transportation, B=Bank, I=Insurance
        
        
        for key in ["N", "M", "U", "T", "B", "I"]:
            value1 = [x for x in filteredFine if x.CompanyReference.IndustryTemplateCode == key]
            value2 = []
            
            #Write if statements for all the parameter Checks
            if key == "N":
                
                value2 = [i for i in value1 if (1.0 <= i.OperationRatios.InventoryTurnover.ThreeMonths <= 2.0)]
                
            if key == "M":
                
                value2 = [i for i in value1 if i.OperationRatios.QuickRatio.ThreeMonths >= 1.0]
                
            if key == "U":
                
                value2 = [i for i in value1 if i.OperationRatios.InterestCoverage.ThreeMonths >= 2.0]
                
            if key == "T":
                
                value2 = [i for i in value1 if i.OperationRatios.ROA.ThreeMonths >= 0.04]
            
            if key == "B":
                
                value2 = [i for i in value1 if (i.FinancialStatements.IncomeStatement.OtherNonInterestExpense.ThreeMonths / i.FinancialStatements.IncomeStatement.TotalRevenue.ThreeMonths) < 0.60]
            
            if key == "I":
                
                value2 = [i for i in value1 if i.OperationRatios.LossRatio.ThreeMonths < 1.0]
                
            if key != "N" or "M" or "U" or "T" or "B" or "I":
                value2 = value1
                
            value3 = sorted(value2, key=lambda x: self.dollarVolumeBySymbol[x.Symbol], reverse = True)
            myDict[key] = value3[:ceil(len(value3) * percent)]

        # stocks in QC500 universe
        topFine = chain.from_iterable(myDict.values())

     

        # sort stocks in the security universe of QC500 based on Enterprise Value to EBITDA valuation ratio
        sortedByEVToEBITDA = sorted(topFine, key=lambda x: x.ValuationRatios.EVToEBITDA , reverse=True)

        # sort subset of stocks that have been sorted by Enterprise Value to EBITDA, based on the valuation ratio Return on Assets (ROA)
        sortedByROA = sorted(sortedByEVToEBITDA[:self.NumberOfSymbolsFine], key=lambda x: x.ValuationRatios.ForwardROA, reverse=False)

        # retrieve list of securites in portfolio
        self.stocks = sortedByROA[:self.NumberOfSymbolsInPortfolio]
        
        
        #for options we can pull some options but not all
        self.contract=[]
  
        #creates an empty space in contract list for number of stocks we have
        for x in self.stocks:
            self.contract.append(None)
           

        for x in self.stocks:
            #sets the current symbol being looped through (will be used when calling other methods)
            self.currentSymbol = x.Symbol
            self.currentstock = x
       
            #sets the index specific to each ticker in self.ticker. Indexes between ticker and options should always match
                    #need to write code that checks that option and ticker index is the same
                    
            self.currentIndex = self.stocks.index(x)
            
            if self.contract[self.currentIndex] is None :
                self.contract[self.currentIndex] = self.GetContract(algorithm)
                #Generate a contract from the method GetContract and store in contract array which index corresponds to its ticker
       
      
        #Following block of code combines both the symbols of equities and options
        res = [i for i in self.contract if i] 
        self.result=[]
        for t in res: 
            for x in t: 
                self.result.append(x)
        self.newstocks= [x.Symbol for x in self.stocks]
        
       # algorithm.Log(str ([x for x in self.newstocks + self.result]))
        #Logs our returns each month
        #algorithm.Debug(str([x.Value for x in self.newstocks + self.result ]))
        return [x for x in self.newstocks + self.result]




    
    def GetContract(self, algorithm):
        
        #set target strike 20% away, can create bounds for future use
        self.bound=0.2
        lowertargetStrike = (self.currentstock.Price * (1-self.bound)) 
        uppertargetStrike=(self.currentstock.Price * (1+self.bound)) 
   
        #pulls contract data for select equity at current time
        contracts=algorithm.OptionChainProvider.GetOptionContractList(self.currentSymbol, algorithm.Time)
   
        #selects the type of option to be Put contract
        puts = [x for x in contracts if x.ID.OptionRight == OptionRight.Put]

        #sorts contracts by closet expiring date date and closest strike price (sorts in ascending order)
        puts = sorted(sorted(puts, key = lambda x: x.ID.Date), 
            key = lambda x: x.ID.StrikePrice)
            
        puts = [x for x in puts if x.ID.StrikePrice < lowertargetStrike]
        
        
        #then selects all contracts that meet our expiration criteria
        #We want between 30 and 60 days as we do not want to hold our options close to expiration
        puts = [x for x in puts if 30<(x.ID.Date - algorithm.Time).days <= 60]
     
        if not puts:
            return
        
          #selects the type of option to be Put contract
        call = [x for x in contracts if x.ID.OptionRight ==OptionRight.Call]
        
        #sorts contracts by closet expiring date date and closest strike price (sorts in ascending order)
        call = sorted(sorted(call, key = lambda x: x.ID.Date), 
            key = lambda x: x.ID.StrikePrice)
            
        call = [x for x in call if x.ID.StrikePrice > uppertargetStrike]
        
        #then selects all contracts that meet our expiration criteria
        call = [x for x in call if  30<(x.ID.Date - algorithm.Time).days <= 60]

        if not call:
           return
        
        #will eventually return array of optimal puts and calls
        return (puts[0],call[0])
