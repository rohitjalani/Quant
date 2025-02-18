import pandas as pd

'''
Class for aligning trades from different strategies to the same timestamps. 
For making an ensemble of different strategies, we need to align the trades from different strategies to the same timestamps.
'''

class Aligner:
    def __init__(self, cheby_trades, gmma_trades, config):
        '''
        Parameters:
            cheby_trades (pd.DataFrame): DataFrame containing trades from Chebyshev-Butterworth strategy.
            gmma_trades (pd.DataFrame): DataFrame containing trades from GMMA strategy.
        '''
        self.cheby_trades = cheby_trades.copy()
        self.gmma_trades = gmma_trades.copy()
        self.config = config

    def run(self):
        # index for iterating over trades from different strategies
        index_cheby = 0
        index_gmma = 0

        # lists to store the new rows to be added to the trades
        new_cheby_trades = []
        new_gmma_trades = []

        # iterate over the trades from different strategies
        while index_cheby < len(self.cheby_trades) or index_gmma < len(self.gmma_trades):

            # if cheby_trades is exhausted, add the rows from the remaining gmma trades to the cheby trades list
            if index_cheby == len(self.cheby_trades):
                temp_row = self.gmma_trades.iloc[index_gmma].copy()
                temp_row['signals'] = 0
                new_cheby_trades.append(temp_row.to_dict())
                index_gmma+=1
            
            # if gmma_trades is exhausted, add the rows from the remaining cheby trades to the gmma trades list
            elif index_gmma == len(self.gmma_trades):
                temp_row = self.cheby_trades.iloc[index_cheby].copy()
                temp_row['signals'] = 0
                new_gmma_trades.append(temp_row.to_dict())
                index_cheby+=1

            # if the timestamps are equal, then increment both the indices
            elif self.cheby_trades['datetime'].iloc[index_cheby] == self.gmma_trades['datetime'].iloc[index_gmma]:
                index_cheby+=1
                index_gmma+=1

            # if the timestamps are not equal, then add the row with the lower timestamp to the list of trades of the other strategy
            elif self.cheby_trades['datetime'].iloc[index_cheby] < self.gmma_trades['datetime'].iloc[index_gmma]:
                temp_row = self.cheby_trades.iloc[index_cheby].copy()
                temp_row['signals'] = 0
                new_gmma_trades.append(temp_row.to_dict())
                index_cheby+=1

            elif self.cheby_trades['datetime'].iloc[index_cheby] > self.gmma_trades['datetime'].iloc[index_gmma]:
                temp_row = self.gmma_trades.iloc[index_gmma].copy()
                temp_row['signals'] = 0
                new_cheby_trades.append(temp_row.to_dict())
                index_gmma+=1

        # concatenate the new trades to the original trades
        new_cheby_trades = pd.DataFrame(new_cheby_trades)
        new_gmma_trades = pd.DataFrame(new_gmma_trades)

        self.cheby_trades = pd.concat([self.cheby_trades, new_cheby_trades])
        self.gmma_trades = pd.concat([self.gmma_trades, new_gmma_trades])

        self.cheby_trades.sort_values(by=['datetime'], inplace=True)
        self.gmma_trades.sort_values(by=['datetime'], inplace=True)

        self.cheby_trades.reset_index(inplace=True, drop=True)
        self.gmma_trades.reset_index(inplace=True, drop=True)

        return self.cheby_trades, self.gmma_trades

