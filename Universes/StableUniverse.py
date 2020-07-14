#Some of the parameters in coarse selection and the idea to rank stocks based on EVtoEBITA ratio  was extended from an example in QuantConenct however the code is original

from clr import AddReference
AddReference("System")
AddReference("QuantConnect.Common")
AddReference("QuantConnect.Indicators")
AddReference("QuantConnect.Algorithm.Framework")

from QuantConnect.Data.UniverseSelection import * 
from Selection.FundamentalUniverseSelectionModel import FundamentalUniverseSelectionModel 
from QuantConnect.Data.Custom.SEC import *
from CustomAlpha import ReversiontotheMean
from datetime import timedelta, datetime
from math import ceil
from itertools import chain
#imports necessary packages

class Stable(FundamentalUniverseSelectionModel):
 

    def __init__(self,algorithm, filterFineData = True, universeSettings = None, securityInitializer = None):
        
      
        super().__init__(filterFineData, universeSettings, securityInitializer)
        self.algorithm=algorithm
       
        # Number of stocks in Coarse Universe
        self.NumberOfSymbolsCoarse = 2500
       
       # Number of sorted stocks in the fine selection subset using the valuation ratio, EV to EBITDA (EV/EBITDA)
        self.NumberOfSymbolsFine =  250
        
        # Final number of stocks in security list, after sorted by the valuation ratio, Return on Assets (ROA)
        self.NumberOfSymbolsInPortfolio =25

        self.lastmonth = -1
        self.dollarVolumeBySymbol = {}
        
        
        self.debttoequityMaxAllowance = 2
        self.priceAllowance = 25
        
    
    
        

    def SelectCoarse(self, algorithm, coarse):
        #We only want to pull a new universe once a month
        month= algorithm.Time.month
        if month== self.lastmonth:
            return Universe.Unchanged
        self.lastmonth= month
        
        
        # sort the stocks by dollar volume and take the top 2000
        top = sorted([x for x in coarse if x.HasFundamentalData],
                    key=lambda x: x.DollarVolume, reverse=True)[:self.NumberOfSymbolsCoarse]
        
        #assigns all the stocks from price to dollarVolumeBySymbol
        self.dollarVolumeBySymbol = { i.Symbol: i.DollarVolume for i in top }
        return list(self.dollarVolumeBySymbol.keys())
    

    def SelectFine(self, algorithm, fine):
        #Set's our debit to equity max allowance and price allowance
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
                '''The Inventory Turnover or the Inventory Ratio is a measurment of how many times a company has sold and replaced inventory within 
                a specified period. It is calculated by dividing Cost of Goods Sold by Aveerage Inventory
                A stable inventory turnover is between 1.0 and 2.0'''
                # !!! The values 1.0 and 2.0 may be wrong if Quant Connect uses quantity rather than dollar amount for Average Inventory !!!
                value2 = [i for i in value1 if (1.0 <= i.OperationRatios.InventoryTurnover.ThreeMonths <= 2.0)]
                
            if key == "M":
                '''The Quick Ratio or The Acid Test Ratio is a basic metric of liquidity and financial solvency. It represents a company's ability to 
                quickly handle its current short term financial obligations with liquid assets. The Quick Ratio is considered a fundamental ratio to quickly
                determine the financial health of a company'''
                ''' The quick ratio is calculated by dividing the total current assets minus inventory by the company's total short-term obligations.'''
                # A healthy quick ratio or the minimum quick ratio that investors will consider is a ratio greater than or equal to 1.0
                value2 = [i for i in value1 if i.OperationRatios.QuickRatio.ThreeMonths >= 1.0]
                
            if key == "U":
                '''The Interest Coverage Ratio is a debt a profability ratio used to determine how easily a company can pay interest on its outstanding debt.
                The number outputed is the numnber of times a cpompany can cover its current interest payment with its earnings. In other words its a measure of saftey.
                The Interest Coverage Ratio can be calculated by dividing EBIT by Interest Expense'''
                # An acceptable Coverage Ratio varies per industry but investors use 2.0 as an acceptable ratio for the Utilities Industry.
                value2 = [i for i in value1 if i.OperationRatios.InterestCoverage.ThreeMonths >= 2.0]
                
            if key == "T":
                '''Return on Assets is an indicator for how profitable a companyt is relative to its total assets.
                In essence, it is an indicator of how well a company utilizes its assets.
                It can be calculated by dividing Net Income by Total Assets
                '''
                # Investors consider a ROA of over 0.05 good. However, most transporation companies are currently underperforming and have an average of 0.024
                # Analyzing the transportation industry is tricky because industries such as the airline industry are considered commodities, not goods or services
                # I will revisit the criteria for the industry in the later future. For now this metric just checks if the tranport company is utilizing its assets
                value2 = [i for i in value1 if i.OperationRatios.ROA.ThreeMonths >= 0.04]
            
            if key == "B":
                '''The Efficiency Ratio assesses the efficiency of a bank’s operation by dividing non-interest expenses by revenue'''
                '''The Efficiency Ratio does not include interest expenses, as the latter is naturally occurring when the deposits within a bank grow. 
                However, non-interest expenses, such as marketing or operational expenses, can be controlled by the bank. 
                A lower Efficiency Ratio shows that there is less non-interest expense per dollar of revenue.'''
                # An efficiency ratio of 50% or less is considered optimal
                value2 = [i for i in value1 if (i.FinancialStatements.IncomeStatement.OtherNonInterestExpense.ThreeMonths / i.FinancialStatements.IncomeStatement.TotalRevenue.ThreeMonths) < 0.60]
            
            if key == "I":
                '''The Loss Ratio is a measurment of total incurred losses in relation to total insurance premiums collected. 
                The Loss Ratio can be calculated by dividing (Incurrend Losses or Paid out in Claims) by Insurance Premiums Collected.
                The loser the ratio, the more profitable the company is. If greater than 1.0, then company is paying more claims than collecting premiums'''
                # A ratio less than 1 indicates that an insurer is in sound financial health
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
    
        return [f.Symbol for f in sortedByROA[:self.NumberOfSymbolsInPortfolio]]
