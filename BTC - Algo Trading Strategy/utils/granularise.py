import numpy as np
import pandas as pd

'''
This file contails the Class for granularising trades from different strategies to the same timestamps to make an ensemble of different strategies.
This class converts trades from daily and weekly timeframes to three minute timeframe.
'''
class GranulariseTrades:

    def __init__(self, config):
        self.config = config

    def run(self, strat_trades, granularise_ohlcv):
        '''
        Parameters:
            strat_trades (pd.DataFrame): DataFrame containing trades from a strategy.
            granularise_ohlcv (pd.DataFrame): DataFrame containing ohlcv data for the timeframe to which the trades need to be granularised.
        '''

        # dataframe for daily trades
        trades = strat_trades.copy()

        # dataframe for minute ohlcv
        self.granularise_ohlcv = granularise_ohlcv.copy()

        # enter or exit on open or close
        enter_on = self.config.utils.trade_on
        exit_on = self.config.utils.trade_on

        # add a column for signals
        self.granularise_ohlcv['signals'] = np.zeros(len(self.granularise_ohlcv))
        self.granularise_ohlcv.rename(columns={'open_time': 'datetime'}, inplace=True)
        self.granularise_ohlcv = self.granularise_ohlcv[['datetime', 'open', 'high', 'low', 'close', 'volume', 'signals']]
        self.granularise_ohlcv['date'] = self.granularise_ohlcv['datetime'].apply(lambda x: x[:10])

        # find the sample to be used (insample or outsample)
        sample = self.config.utils.sample
        if sample not in self.config.data.samples:
            raise Exception("Invalid sample")
        
        # slice the data drame to only include the time period we are interested in
        start_date = self.config.data.samples[sample].start_date
        end_date = self.config.data.samples[sample].end_date

        start_index = self.granularise_ohlcv[self.granularise_ohlcv["datetime"] >= start_date].index[0]
        start_index = max(0, start_index)
        end_index = self.granularise_ohlcv[self.granularise_ohlcv["datetime"] <= end_date].index[-1]
        self.granularise_ohlcv = self.granularise_ohlcv.loc[start_index:end_index]
        self.granularise_ohlcv.reset_index(drop=True, inplace=True)

        # check if the trades dataframe is weekly or daily
        current_granularity = ''
        # find difference between any 2 consecutive dates in string format
        if len(trades)<=1:
            return strat_trades
        # if the difference is 1, then the trades are daily
        if pd.to_datetime(trades['datetime'].iloc[1]) - pd.to_datetime(trades['datetime'].iloc[0]) <= pd.Timedelta('1 days'):
            current_granularity = 'daily'
        else:
            current_granularity = 'weekly'

        # variable to keep track of current position
        current_position = 0
        index_inner_loop = 0

        # iterate over the trades
        for i in range(len(trades)):
            val = trades['signals'].iloc[i]
            current_position += val

            if val == 0:
                continue

            if val!=0 and current_position != 0:
                # if positions are entered on open, then enter on the next candle
                if enter_on == 'open':
                    while index_inner_loop < len(self.granularise_ohlcv['date']) and self.granularise_ohlcv['date'].iloc[index_inner_loop] < trades['datetime'].iloc[i]:
                        index_inner_loop+=1
                    if index_inner_loop < len(self.granularise_ohlcv):
                        self.granularise_ohlcv.at[index_inner_loop, 'signals'] += val
                # if positions are entered on close, then enter on the current candle
                else:
                    if current_granularity == 'daily':
                        while index_inner_loop < len(self.granularise_ohlcv['date']) and self.granularise_ohlcv['date'].iloc[index_inner_loop] <= trades['datetime'].iloc[i]:
                            index_inner_loop+=1
                        if index_inner_loop < len(self.granularise_ohlcv):
                            self.granularise_ohlcv.at[index_inner_loop-1, 'signals'] += val
                    elif current_granularity == 'weekly':
                        # enter the trade on the last candle of the week
                        date = trades['datetime'].iloc[i]
                        # add 6 days to the date
                        date = pd.to_datetime(date) + pd.Timedelta('6 days')
                        # convert to string
                        date = str(date)[:10]
                        while index_inner_loop < len(self.granularise_ohlcv['date']) and self.granularise_ohlcv['date'].iloc[index_inner_loop] <= date:
                            index_inner_loop+=1
                        if index_inner_loop < len(self.granularise_ohlcv):
                            self.granularise_ohlcv.at[index_inner_loop-1, 'signals'] += val
            
            if val!= 0 and current_position == 0:
                # if positions are exited on open, then exit on the current candle
                if exit_on == 'open':
                    while index_inner_loop < len(self.granularise_ohlcv['date']) and self.granularise_ohlcv['date'].iloc[index_inner_loop] < trades['datetime'].iloc[i]:
                        index_inner_loop+=1
                    if index_inner_loop < len(self.granularise_ohlcv['date']):
                        self.granularise_ohlcv.at[index_inner_loop, 'signals'] += val
                # if positions are exited on close, then exit on the next candle
                else:
                    if current_granularity == 'daily':
                        while index_inner_loop < len(self.granularise_ohlcv['date']) and self.granularise_ohlcv['date'].iloc[index_inner_loop] <= trades['datetime'].iloc[i]:
                            index_inner_loop+=1
                        if index_inner_loop < len(self.granularise_ohlcv['date']):
                            self.granularise_ohlcv.at[index_inner_loop-1, 'signals'] += val
                    elif current_granularity == 'weekly':
                        # exit the trade on the last candle of the week
                        date = trades['datetime'].iloc[i]
                        # add 6 days to the date
                        date = pd.to_datetime(date) + pd.Timedelta('6 days')
                        # convert to string
                        date = str(date)[:10]
                        while index_inner_loop < len(self.granularise_ohlcv['date']) and self.granularise_ohlcv['date'].iloc[index_inner_loop] <= date:
                            index_inner_loop+=1
                        if index_inner_loop < len(self.granularise_ohlcv['date']):
                            self.granularise_ohlcv.at[index_inner_loop-1, 'signals'] += val
        
        # if the trades are closed and opened on the same timestamp, then create a duplicate row and add it to the dataframe
        new_rows = []
        for i in range(len(self.granularise_ohlcv)):
            if abs(self.granularise_ohlcv['signals'].iloc[i]) > 1:
                self.granularise_ohlcv.at[i, 'signals'] = (self.granularise_ohlcv['signals'].iloc[i])/2
                # duplicate and add this row at the next index
                new_rows.append(self.granularise_ohlcv.iloc[i].to_dict())

        # add the new rows to the dataframe
        new_rows = pd.DataFrame(new_rows)
        self.granularise_ohlcv = pd.concat([self.granularise_ohlcv, new_rows])
        self.granularise_ohlcv.sort_values(by=['datetime'], inplace=True)
        self.granularise_ohlcv.drop(['date'], axis=1, inplace=True)
        self.granularise_ohlcv.reset_index(inplace=True)
        return self.granularise_ohlcv

class Granularise:
    '''
    Wrapper class for GranulariseTrades.
    Takes in 3 dataframes containing trades from 3 different strategies and granularises them to the same timestamps.
    '''
    def __init__(self, config):
        self.config = config
        self.granulariser = GranulariseTrades(config)

    def run(self, df1, df2, df3, df_gran):
        granularised_df1 = self.granulariser.run(df1, df_gran)
        granularised_df2 = self.granulariser.run(df2, df_gran)
        granularised_df3 = self.granulariser.run(df3, df_gran)
        return granularised_df1, granularised_df2, granularised_df3
