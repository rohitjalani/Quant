import pandas as pd
import numpy as np
from utils.indicators import *
from scipy.signal import butter, filtfilt, cheby1
from utils.granularise import GranulariseTrades
import pandas_ta as ta

'''
This file contains codes of all the strategies used for signal generation namely
1. StratCheby: Chebyshev Butterworth filters crossover strategy
2. StratGMMA: Guppy Multiple Moving Averages (GMMA) augmented long-only strategy
3. MixedStratGMMA: Takes a combination of two different StratGMMAs which are run on two different timeframes
'''

class StratCheby:
    '''
    This class implements the Chebyshev filter strategy.
    The strategy is implemented as follows:
    1. Apply butterworth and chebyshev filters to the close price.
    2. Convert the 1d closing prices to frequency domain by applying DFT
    3. If chebyshev < butterworth, then take a long position.
    4. If chebyshev > butterworth, then take a short position.
    '''
    def __init__(self, df_ohlcv, df_gran, config):
        '''
        Parameters:
            df (pd.DataFrame): DataFrame containing 1 day OHLCV data to generate chebyshev butterworth signals.
            df_gran (pd.DataFrame): DataFrame containing 3 minute OHLCV data to generate granularised trades (basically converting a higher timeframe data like 1w to lower timeframe data like 3m).
            config: Contains the configuration for the strategy.
        '''
        self.df = df_ohlcv.copy()
        self.df_gran = df_gran.copy()
        self.config = config
        self.granulariser = GranulariseTrades(config)

    def butterworth(self, data):
        '''
        Parameters:
            data (pd.DataFrame): DataFrame containing 1 day OHLCV data
        Method:
            Apply butterworth filter to the close column of the data.
        Returns:
            pd.Series: Series containing the filtered values.
        '''
        order = self.config.strategies.strat_cheby.butterworth.order
        cutoff_freq = self.config.strategies.strat_cheby.butterworth.cutoff_frequency
        b, a = butter(N = order, Wn = cutoff_freq, btype='low', analog=False, output='ba')
        smooth_data = filtfilt(b, a, data['close'], padlen=0)
        return smooth_data

    def chebyshev(self, data):
        '''
        Parameters:
            data (pd.DataFrame): DataFrame containing 1 day OHLCV data
        Method:
            Apply chebyshev filter to the close column of the data.
        Returns:
            pd.Series: Series containing the filtered values.
        '''
        cutoff_freq = self.config.strategies.strat_cheby.chebyshev.cutoff_frequency
        rp = self.config.strategies.strat_cheby.chebyshev.ripple_factor
        order = self.config.strategies.strat_cheby.chebyshev.order
        b, a = cheby1(N = order, rp = rp, Wn = cutoff_freq, btype='low', analog=False, output='ba')
        smooth_data = filtfilt(b, a, data['close'], padlen=0)
        return smooth_data
    
    def generate_chebyshev_butterworth_values(self):
        '''
        Method:
            Generate the chebyshev and butterworth values for the dataframe.
        '''
        self.df["butter"] = 0.0
        self.df["cheby"] = 0.0
        for i in (range(1, len(self.df)+1)):
            df_temp = self.df[:i].copy()
            self.df.at[i-1, "butter"] = self.butterworth(df_temp)[-1]
            self.df.at[i-1, "cheby"] = self.chebyshev(df_temp)[-1]
        return None
    
    def cond_take_trade(self, trades, date):
        '''
        This function decides whether to take a trade or not. This is used as a risk mitigation method to reduce drawdowns
        Parameters:
            trades (pd.DataFrame): DataFrame containing the previous trades.
            date (str): Date of the current candle.
        Method:
            Check if the trade should be taken or not. If the previous n trades are negative and taken in the specified duration, then don'current_position take the trade.
        Returns:
            bool: True if the trade should be taken, False otherwise.
        '''

        # check if skip_trade is active
        if self.config.strategies.strat_cheby.skip_trade.active == False:
            return True
        
        # find the duration and number of trades from the config
        duration = self.config.strategies.strat_cheby.skip_trade.duration
        num_trades = self.config.strategies.strat_cheby.skip_trade.num_trades

        # check if the number of trades is less than the specified number of trades
        if len(trades) <= num_trades:
            return True
            
        # check the date of the first trade
        last_trade_date = trades["entry_time"].iloc[-num_trades-1]

        # compare both dates in string format and check
        if (pd.to_datetime(date) - pd.to_datetime(last_trade_date)).days > duration:
            return True

        # check if the previous n trades are negative
        for i in range(2, num_trades+2):
            threshold = self.config.strategies.strat_cheby.skip_trade.pct
            # print(trades['pnl'].iloc[-i], trades["entry_time"].iloc[-i], trades["exit_time"].iloc[-i])
            if trades["pnl"].iloc[-i] > threshold:
                return True
        
        return False

    
    def generate_trades(self):
        '''
        Method:
            Generate the trades for the dataframe using the chebyshev and butterworth values. The signals are generated as follows:
            1. If chebyshev < butterworth, then buy.
            2. If chebyshev > butterworth, then sell.
        Returns:
            pd.DataFrame: DataFrame containing the trades.
        '''

        # check if the data is insample or outsample
        sample = self.config.utils.sample

        # check if the sample is valid
        if sample not in self.config.data.samples:
            raise Exception("Invalid sample")
        
        # get the start and end dates for the sample
        start_date = self.config.data.samples[sample].start_date
        end_date = self.config.data.samples[sample].end_date

        # get the start and end indexes for the sample
        start_index = self.df[self.df["datetime"] >= start_date].index[0]
        start_index = max(0, start_index)
        end_index = self.df[self.df["datetime"] <= end_date].index[-1]
        self.df = self.df.loc[start_index:end_index]
        self.df.reset_index(drop=True, inplace=True)


        trades = []

        # create a dataframe to store the hypothetical trades
        hypothetical_trades = pd.DataFrame(columns = ["entry_time", "entry_price", "exit_time", "exit_price", "profit", "pnl", "long/short"])

        # variable to keep track of current position and hypothetical position
        current_position = 0
        hypothetical_position = 0
        enter_on = self.config.utils.trade_on

        # if positions are entered on open, then enter on the next candle
        if enter_on == "open":
            # add a row to trades with signals = 0
            row = {"signals": 0, "datetime": self.df["datetime"][0], "close": self.df["close"][0], "open": self.df["open"][0], "high": self.df["high"][0], "low": self.df["low"][0], "volume": self.df["volume"][0]}
            trades.append(row)

            for i in range(0, len(self.df)-1):
                # check if the butterworth value is less than chebyshev value
                if self.df['butter'][i] < self.df['cheby'][i]:
                    row = {"signals": 1, "datetime": self.df["datetime"][i+1], "close": self.df["close"][i+1], "open": self.df["open"][i+1], "high": self.df["high"][i+1], "low": self.df["low"][i+1], "volume": self.df["volume"][i+1]}

                    # if the hypothetical position is 0 and butterworth value is less than chebyshev value, then enter a long position in the hypothetical trades
                    if hypothetical_position == 0:
                        hypothetical_trades.at[0, "entry_time"] = self.df["datetime"][i+1]
                        hypothetical_trades.at[0, "entry_price"] = self.df[enter_on][i+1]
                        hypothetical_trades.at[0, "long/short"] = "long"
                        hypothetical_position = 1

                    # if the hypothetical position is 1 and butterworth value is less than chebyshev value, then exit the short position and enter a long position in the hypothetical trades
                    elif hypothetical_position == -1:
                        hypothetical_trades.at[len(hypothetical_trades)-1, "exit_time"] = self.df["datetime"][i+1]
                        hypothetical_trades.at[len(hypothetical_trades)-1, "exit_price"] = self.df[enter_on][i+1]
                        hypothetical_trades.at[len(hypothetical_trades)-1, "profit"] = hypothetical_trades.at[len(hypothetical_trades)-1, "entry_price"] - hypothetical_trades.at[len(hypothetical_trades)-1, "exit_price"]
                        hypothetical_trades.at[len(hypothetical_trades)-1, "pnl"] = 100*hypothetical_trades.at[len(hypothetical_trades)-1, "profit"] / hypothetical_trades.at[len(hypothetical_trades)-1, "entry_price"]
                        hypothetical_position = 0
                        hypothetical_trades.loc[len(hypothetical_trades), ["entry_time", "entry_price", "long/short"]] = [self.df["datetime"][i+1], self.df[enter_on][i+1], "long"]
                        hypothetical_position = 1

                    # if currently in a neutral position, then check if a trade should be taken
                    if current_position == 0:
                        # if the last n trades are not negative and it is a crossover, then enter a long position
                        if self.cond_take_trade(hypothetical_trades, row["datetime"]):
                            if i==0 or self.df["butter"][i-1] > self.df["cheby"][i-1]:
                                trades.append(row)
                                current_position = 1
                        else:
                            row["signals"] = 0
                            trades.append(row)
                            current_position = 0
                    # if currently in a long position, then no trade should be taken
                    elif current_position == 1:
                        row["signals"] = 0
                        trades.append(row)

                    # if currently in a short position, then exit the short position
                    elif current_position == -1:
                        row["signals"] = 1
                        trades.append(row)
                        current_position = 0

                        # if the last n trades are not negative and it is a crossover, then enter a long position
                        if self.cond_take_trade(hypothetical_trades, row["datetime"]):
                            if i==0 or self.df["butter"][i-1] > self.df["cheby"][i-1]:
                                trades.append(row)
                                current_position = 1 

                # check if the butterworth value is greater than chebyshev value
                if self.df["butter"][i] > self.df["cheby"][i]:
                    row = {"signals": -1, "datetime": self.df["datetime"][i+1], "close": self.df["close"][i+1], "open": self.df["open"][i+1], "high": self.df["high"][i+1], "low": self.df["low"][i+1], "volume": self.df["volume"][i+1]}

                    # if the hypothetical position is 0 and butterworth value is greater than chebyshev value, then enter a short position in the hypothetical trades
                    if hypothetical_position == 0:
                        hypothetical_trades.at[0, "entry_time"] = self.df["datetime"][i+1]
                        hypothetical_trades.at[0, "entry_price"] = self.df[enter_on][i+1]
                        hypothetical_trades.at[0, "long/short"] = "short"
                        hypothetical_position = -1

                    # if the hypothetical position is 1 and butterworth value is greater than chebyshev value, then exit the long position and enter a short position in the hypothetical trades
                    elif hypothetical_position == 1:
                        hypothetical_trades.at[len(hypothetical_trades)-1, "exit_time"] = self.df["datetime"][i+1]
                        hypothetical_trades.at[len(hypothetical_trades)-1, "exit_price"] = self.df[enter_on][i+1]
                        hypothetical_trades.at[len(hypothetical_trades)-1, "profit"] = hypothetical_trades.at[len(hypothetical_trades)-1, "exit_price"] - hypothetical_trades.at[len(hypothetical_trades)-1, "entry_price"]
                        hypothetical_trades.at[len(hypothetical_trades)-1, "pnl"] = 100*hypothetical_trades.at[len(hypothetical_trades)-1, "profit"] / hypothetical_trades.at[len(hypothetical_trades)-1, "entry_price"]
                        hypothetical_position = 0
                        hypothetical_trades.loc[len(hypothetical_trades), ["entry_time", "entry_price", "long/short"]] = [self.df["datetime"][i+1], self.df[enter_on][i+1], "short"]
                        hypothetical_position = -1

                    # if currently in a neutral position, then check if a trade should be taken
                    if current_position == 0:
                        # if the last n trades are not negative and it is a crossover, then enter a short position
                        if self.cond_take_trade(hypothetical_trades, row["datetime"]):
                            if i==0 or self.df["butter"][i-1] < self.df["cheby"][i-1]:
                                trades.append(row)
                                current_position = -1
                        else:
                            row["signals"] = 0
                            trades.append(row)
                            current_position = 0

                    # if currently in a long position, then exit the long position
                    elif current_position == 1:
                        row["signals"] = -1
                        trades.append(row)
                        current_position = 0

                        # if the last n trades are not negative and it is a crossover, then enter a short position
                        if self.cond_take_trade(hypothetical_trades, row["datetime"]):
                            if i==0 or self.df["butter"][i-1] < self.df["cheby"][i-1]:
                                trades.append(row)
                                current_position = -1

                    # if currently in a short position, then no trade should be taken
                    elif current_position == -1:
                        row["signals"] = 0
                        trades.append(row)

        # if positions are entered on close, then enter on the current candle
        else:
            for i in range(0, len(self.df)):
                # check if the butterworth value is less than chebyshev value
                if self.df['butter'][i] < self.df['cheby'][i]:
                    row = {"signals": 1, "datetime": self.df["datetime"][i], "close": self.df["close"][i], "open": self.df["open"][i], "high": self.df["high"][i], "low": self.df["low"][i], "volume": self.df["volume"][i]}
                    
                    # if the hypothetical position is 0 and butterworth value is less than chebyshev value, then enter a long position in the hypothetical trades
                    if hypothetical_position == 0:
                        hypothetical_trades.at[0, "entry_time"] = self.df["datetime"][i]
                        hypothetical_trades.at[0, "entry_price"] = self.df[enter_on][i]
                        hypothetical_trades.at[0, "long/short"] = "long"
                        hypothetical_position = 1

                    # if the hypothetical position is 1 and butterworth value is less than chebyshev value, then exit the short position and enter a long position in the hypothetical trades
                    elif hypothetical_position == -1:
                        hypothetical_trades.at[len(hypothetical_trades)-1, "exit_time"] = self.df["datetime"][i]
                        hypothetical_trades.at[len(hypothetical_trades)-1, "exit_price"] = self.df[enter_on][i]
                        hypothetical_trades.at[len(hypothetical_trades)-1, "profit"] = hypothetical_trades.at[len(hypothetical_trades)-1, "entry_price"] - hypothetical_trades.at[len(hypothetical_trades)-1, "exit_price"]
                        hypothetical_trades.at[len(hypothetical_trades)-1, "pnl"] = 100*hypothetical_trades.at[len(hypothetical_trades)-1, "profit"] / hypothetical_trades.at[len(hypothetical_trades)-1, "entry_price"]
                        hypothetical_position = 0
                        hypothetical_trades.loc[len(hypothetical_trades), ["entry_time", "entry_price", "long/short"]] = [self.df["datetime"][i], self.df[enter_on][i], "long"]
                        hypothetical_position = 1

                    # if currently in a neutral position, then check if a trade should be taken
                    if current_position == 0:
                        # if the last n trades are not negative and it is a crossover, then enter a long position
                        if self.cond_take_trade(hypothetical_trades, row["datetime"]):
                            if i==0 or self.df["butter"][i-1] > self.df["cheby"][i-1]:
                                trades.append(row)
                                current_position = 1
                        else:
                            row["signals"] = 0
                            trades.append(row)
                            current_position = 0

                    # if currently in a long position, then no trade should be taken
                    elif current_position == 1:
                        row["signals"] = 0
                        trades.append(row)

                    # if currently in a short position, then exit the short position
                    elif current_position == -1:
                        row["signals"] = 1
                        trades.append(row)
                        current_position = 0

                        # if the last n trades are not negative and it is a crossover, then enter a long position
                        if self.cond_take_trade(hypothetical_trades, row["datetime"]):
                            # check if this is a crossover
                            if i==0 or self.df["butter"][i-1] > self.df["cheby"][i-1]:
                                trades.append(row)
                                current_position = 1 

                # check if the butterworth value is greater than chebyshev value
                if self.df["butter"][i] > self.df["cheby"][i]:
                    row = {"signals": -1, "datetime": self.df["datetime"][i], "close": self.df["close"][i], "open": self.df["open"][i], "high": self.df["high"][i], "low": self.df["low"][i], "volume": self.df["volume"][i]}

                    # if the hypothetical position is 0 and butterworth value is greater than chebyshev value, then enter a short position in the hypothetical trades
                    if hypothetical_position == 0:
                        hypothetical_trades.at[0, "entry_time"] = self.df["datetime"][i]
                        hypothetical_trades.at[0, "entry_price"] = self.df[enter_on][i]
                        hypothetical_trades.at[0, "long/short"] = "short"
                        hypothetical_position = -1

                    # if the hypothetical position is 1 and butterworth value is greater than chebyshev value, then exit the long position and enter a short position in the hypothetical trades
                    elif hypothetical_position == 1:
                        hypothetical_trades.at[len(hypothetical_trades)-1, "exit_time"] = self.df["datetime"][i]
                        hypothetical_trades.at[len(hypothetical_trades)-1, "exit_price"] = self.df[enter_on][i]
                        hypothetical_trades.at[len(hypothetical_trades)-1, "profit"] = hypothetical_trades.at[len(hypothetical_trades)-1, "exit_price"] - hypothetical_trades.at[len(hypothetical_trades)-1, "entry_price"]
                        hypothetical_trades.at[len(hypothetical_trades)-1, "pnl"] = 100*hypothetical_trades.at[len(hypothetical_trades)-1, "profit"] / hypothetical_trades.at[len(hypothetical_trades)-1, "entry_price"]
                        hypothetical_position = 0
                        hypothetical_trades.loc[len(hypothetical_trades), ["entry_time", "entry_price", "long/short"]] = [self.df["datetime"][i], self.df[enter_on][i], "short"]
                        hypothetical_position = -1

                    # if currently in a neutral position, then check if a trade should be taken
                    if current_position == 0:
                        # if the last n trades are not negative and it is a crossover, then enter a short position
                        if self.cond_take_trade(hypothetical_trades, row["datetime"]):
                            if i==0 or self.df["butter"][i-1] < self.df["cheby"][i-1]:
                                trades.append(row)
                                current_position = -1
                        else:
                            row["signals"] = 0
                            trades.append(row)
                            current_position = 0

                    # if currently in a long position, then exit the long position
                    elif current_position == 1:
                        row["signals"] = -1
                        trades.append(row)
                        current_position = 0

                        # if the last n trades are not negative and it is a crossover, then enter a short position
                        if self.cond_take_trade(hypothetical_trades, row["datetime"]):
                            if i==0 or self.df["butter"][i-1] < self.df["cheby"][i-1]:
                                trades.append(row)
                                current_position = -1

                    # if currently in a short position, then no trade should be taken
                    elif current_position == -1:
                        row["signals"] = 0
                        trades.append(row)

        # convert the trades list to a dataframe
        trades_df = pd.DataFrame(trades)
        return trades_df

    def run(self):
        self.generate_chebyshev_butterworth_values()
        trades = self.generate_trades()
        granularised_trades = self.granulariser.run(trades, self.df_gran)
        return granularised_trades

class StratGMMA:
    '''
    This class implements the Guppy Multiple Moving Average strategy. The strategy is implemented as follows:
    1. Calculate the exponential moving averages of the close price for the specified windows.
    2. If the short term exponential moving averages are above the long term exponential moving averages, then buy.
    3. If the short term exponential moving averages are below the long term exponential moving averages, then sell.
    '''
    def __init__(self, df, config):
        '''
        Parameters:
            df (pd.DataFrame): DataFrame containing 1 day or 1 week OHLCV data to generate guppy values.
            config: Contains the configuration for the strategy.
        '''
        self.df = df.copy()
        self.config = config

    def generate_guppy_values(self):
        '''
        Method:
            Generate the guppy values for the dataframe. Guppy values are the exponential moving averages of the close price for the specified windows. 
        '''

        # get the window sizes from the config
        guppy_short = self.config.strategies.strat_gmma.gmma_short
        guppy_long = self.config.strategies.strat_gmma.gmma_long

        # use the ta.ema function to calculate the exponential moving averages for the specified windows
        for window in guppy_short:
            self.df[f"guppy_{window}"] = ta.ema(self.df["close"], window)
        for window in guppy_long:
            self.df[f"guppy_{window}"] = ta.ema(self.df["close"], window)
        
        self.df = self.df.dropna()
        self.df.reset_index(drop=True, inplace=True)
        return self.df
    
    def generate_trades(self):
        # get the window sizes from the config
        guppy_short_windows = self.config.strategies.strat_gmma.gmma_short
        guppy_long_windows = self.config.strategies.strat_gmma.gmma_long

        guppy_short = [f"guppy_{window}" for window in guppy_short_windows]
        guppy_long = [f"guppy_{window}" for window in guppy_long_windows]   

        trades = self.df[["datetime", "open", "high", "low", "close", "volume"]].copy()

        # check if the data is insample or outsample
        sample = self.config.utils.sample

        # check if the sample is valid
        if sample not in self.config.data.samples:
            raise Exception("Invalid sample")
        
        # get the start and end dates for the sample
        start_date = self.config.data.samples[sample].start_date
        end_date = self.config.data.samples[sample].end_date

        # get the start and end indexes for the sample
        start_index = trades[trades["datetime"] >= start_date].index[0]
        end_index = trades[trades["datetime"] <= end_date].index[-1]
        trades = trades.loc[start_index:end_index]
        trades.reset_index(drop=True, inplace=True)

        # check if the crossover type is valid
        crossover = self.config.strategies.strat_gmma.crossover
        if crossover.type not in crossover.keys() or crossover.type == "type":
            raise Exception("Invalid crossover type")
        
        # get the k values for the crossover
        elif crossover.type == "long_short":
            k_guppyshort_entry = crossover.long_short.k_guppyshort_entry
            k_guppylong_entry = crossover.long_short.k_guppylong_entry
            k_guppyshort_exit = crossover.long_short.k_guppyshort_exit
            k_guppylong_exit = crossover.long_short.k_guppylong_exit
        elif crossover.type == "short":
            k_guppy_entry = crossover.short.k_guppy_entry  
            k_guppy_exit = crossover.short.k_guppy_exit

        # add a column to store the signals
        trades["signals"] = 0

        # variable to keep track of current position
        current_position = 0

        # check if positions are entered on open or close
        enter_on = self.config.utils.trade_on

        # if positions are entered on open, then enter on the next candle
        if enter_on == "open":
            trades.at[0, "signals"] = 0
            for i in range(0, len(trades)-1):

                # find the guppy values for the current candle
                guppy_short_values = self.df.loc[i, guppy_short].values
                guppy_long_values = self.df.loc[i, guppy_long].values
                
                # find the condition for entering and exiting positions
                if crossover.type == "long_short":
                    sorted_guppy_short_values = sorted(guppy_short_values)
                    sorted_guppy_long_values = sorted(guppy_long_values)
                    condition_long_entry = sorted_guppy_long_values[-1 - k_guppylong_entry] < sorted_guppy_short_values[0 + k_guppyshort_entry]
                    condition_long_exit = sorted_guppy_long_values[-1 - k_guppylong_exit] > sorted_guppy_short_values[0 + k_guppyshort_exit]
                elif crossover.type == "short":
                    reverse_sorted_guppy_short_values = sorted(guppy_short_values, reverse=True)
                    guppy_3_value = self.df.loc[i, "guppy_3"]
                    position = reverse_sorted_guppy_short_values.index(guppy_3_value)
                    condition_long_entry = position <= k_guppy_entry
                    condition_long_exit = position > k_guppy_exit

                # if currently in a neutral position, then take the trade if the condition is satisfied
                if current_position == 0:
                    if condition_long_entry:
                        trades.at[i+1, "signals"] = 1
                        current_position = 1

                # if currently in a long position, then exit the position if the condition is satisfied
                elif current_position == 1:
                    if condition_long_exit:
                        trades.at[i+1, "signals"] = -1
                        current_position = 0

        # if positions are entered on close, then enter on the current candle
        else:
            for i in range(0, len(trades)):

                # find the guppy values for the current candle
                guppy_short_values = self.df.loc[i, guppy_short].values
                guppy_long_values = self.df.loc[i, guppy_long].values
                
                # find the condition for entering and exiting positions
                if crossover.type == "long_short":
                    sorted_guppy_short_values = sorted(guppy_short_values)
                    sorted_guppy_long_values = sorted(guppy_long_values)
                    condition_long_entry = sorted_guppy_long_values[-1 - k_guppylong_entry] < sorted_guppy_short_values[0 + k_guppyshort_entry]
                    condition_long_exit = sorted_guppy_long_values[-1 - k_guppylong_exit] > sorted_guppy_short_values[0 + k_guppyshort_exit]
                elif crossover.type == "short":
                    reverse_sorted_guppy_short_values = sorted(guppy_short_values, reverse=True)
                    guppy_3_value = self.df.loc[i, "guppy_3"]
                    position = reverse_sorted_guppy_short_values.index(guppy_3_value)
                    condition_long_entry = position <= k_guppy_entry
                    condition_long_exit = position > k_guppy_exit

                # if currently in a neutral position, then take the trade if the condition is satisfied
                if current_position == 0:
                    if condition_long_entry:
                        trades.at[i, "signals"] = 1
                        current_position = 1

                # if currently in a long position, then exit the position if the condition is satisfied
                elif current_position == 1:
                    if condition_long_exit:
                        trades.at[i, "signals"] = -1
                        current_position = 0

        return trades
    
    def run(self):
        gmma_values = self.generate_guppy_values()
        trades = self.generate_trades()
        return trades, gmma_values

class MixedStratGMMA:
    '''
    This class implements the Guppy Multiple Moving Average strategy. The strategy is implemented as follows:
    1. Calculate the position for the 1w and 1d GMMA strategies.
    2. If both the positions are positive, then take the position.
    3. Else don't take the position.
    '''
    def __init__(self, df_1, df_2, df_gran, config):
        '''
        Parameters:
            df_1 (pd.DataFrame): DataFrame containing 1 day OHLCV data to generate guppy values.
            df_2 (pd.DataFrame): DataFrame containing 1 week OHLCV data to generate guppy values.
            df_gran (pd.DataFrame): DataFrame containing 3 minute OHLCV data to generate granularised trades.
            config: Contains the configuration for the strategy.
        '''
        self.df_1 = df_1.copy()
        self.df_2 = df_2.copy()
        self.df_gran = df_gran.copy()
        self.config = config
        self.strat_gmma_df_1 = StratGMMA(df_1, config)
        self.strat_gmma_df_2 = StratGMMA(df_2, config)
        self.granulariser = GranulariseTrades(config)

    def combine_gmma_trades(self, gmma_trades_1, gmma_trades_2):
        '''
        Parameters:
            gmma_trades_1 (pd.DataFrame): DataFrame containing the trades for the 1 day GMMA strategy.
            gmma_trades_2 (pd.DataFrame): DataFrame containing the trades for the 1 week GMMA strategy.
        Method:
            Combine the trades from the 1 day and 1 week GMMA strategies. The combined trades are generated as follows:
            1. Find the positions for the 1 day and 1 week GMMA strategies.
            2. Take the and of the positions.
            3. Find the signals from the positions.
        Returns:
            pd.DataFrame: DataFrame containing the combined trades.
        '''
        # find gmma 1w positions
        gmma_trades_1['position'] = gmma_trades_1['signals'].cumsum()
        # find gmma 1d positions
        gmma_trades_2['position'] = gmma_trades_2['signals'].cumsum()

        # take and of gmma 1w and 1d positions
        gmma_trades = gmma_trades_1.copy()
        gmma_trades['position'] = gmma_trades_1['position'] * gmma_trades_2['position']

        # find gmma signals from positions
        gmma_trades['signals'] = gmma_trades['position'] - gmma_trades['position'].shift(1)

        # fill nan with 0
        gmma_trades['signals'].fillna(0, inplace=True)

        # drop position column
        gmma_trades.drop(columns=['position'], inplace=True)

        return gmma_trades

    def run(self):
        trades_df_1, gmma_values_df_1 = self.strat_gmma_df_1.run()
        trades_df_2, _ = self.strat_gmma_df_2.run()
        granularised_trades_df_1 = self.granulariser.run(trades_df_1, self.df_gran)
        granularised_trades_df_2 = self.granulariser.run(trades_df_2, self.df_gran)
        gmma_trades = self.combine_gmma_trades(granularised_trades_df_1, granularised_trades_df_2)
        return gmma_trades, gmma_values_df_1
    
