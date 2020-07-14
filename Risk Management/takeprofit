#This code is entirely original
class takeprofitmodel(RiskManagementModel):
   
    
    def __init__(self):

        self.liquidated = set()
        self.lastmonth=-1
        
    def ManageRisk(self, algorithm, targets):
       
        month= algorithm.Time.month
        if month!= self.lastmonth:
            self.liquidated.clear()
            self.lastmonth= month
        #if different month clear all liquidations
        
        riskAdjustedTargets = list()

        for asset in algorithm.Securities:
            symbol = asset.Key
            security = asset.Value
            #For each of our current securities if the unrealized profit percent is above 8% or below -6%, liquidate
            
            if security.Holdings.UnrealizedProfitPercent>0.08 or security.Holdings.UnrealizedProfitPercent<-0.06 or security.Symbol in self.liquidated:
                riskAdjustedTargets.append(PortfolioTarget(symbol, 0))
                if algorithm.Securities[security.Symbol].Invested:
                    #We do not want an automatic rebuying so wait until the end of the current month before we reenter into a new position
                    self.liquidated.add(security.Symbol)
        return riskAdjustedTargets
