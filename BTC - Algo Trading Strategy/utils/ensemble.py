import numpy as np
import pandas as pd
from tqdm import tqdm
from utils.indicators import *

class Ensemble:
    '''
    Class for making an ensemble of different strategies. 
    The ensemble is made by the following method:
        1. Check if the market is consolidating or not using the PRC indicator.
        2. If the market is consolidating, then don't enter any position.
        3. If the market is not consolidating, then check if the GMMA strategy is active.
        4. If the GMMA strategy is active, then take the corresponding position.
        5. If the GMMA strategy is not active, then check if the Cheby strategy is active.
        6. If the Cheby-Butter strategy is active, then take the corresponding position.
    '''
    def __init__(self, cheby_trades, gmma_trades, gmma_values, config):
        '''
        Parameters:
            cheby_trades (pd.DataFrame): DataFrame containing trades from Cheby-Butter strategy.
            gmma_trades (pd.DataFrame): DataFrame containing trades from GMMA strategy.
            gmma_values (pd.DataFrame): DataFrame containing GMMA values for each timestamp.
            config: Contains enter_on and exit_on.
        '''
        self.cheby_trades = cheby_trades.copy()
        self.gmma_trades = gmma_trades.copy()
        self.gmma_values = gmma_values.copy()
        self.config = config

    def run(self):
        # Add a column for the current position of both the strategies using cumulative sum of signals
        self.cheby_trades['position'] = self.cheby_trades['signals'].cumsum()
        self.gmma_trades['position'] = self.gmma_trades['signals'].cumsum()

        # Find the kind of crossover used in the GMMA strategy
        crossover = self.config.strategies.strat_cheby.crossover
        if crossover.type not in crossover.keys() or crossover.type == "type":
            raise Exception("Invalid crossover type")
        elif crossover.type == "long_short":
            k_guppyshort_entry = crossover.long_short.k_guppyshort_entry
            k_guppylong_entry = crossover.long_short.k_guppylong_entry
        elif self.crossover.type == "short":
            k_guppy_entry = crossover.short.k_guppy_entry

        # Get the window sizes from the config
        guppy_short_windows = self.config.strategies.strat_gmma.gmma_short
        guppy_long_windows = self.config.strategies.strat_gmma.gmma_long

        # Create the column names for the GMMA values
        guppy_short = [f"guppy_{window}" for window in guppy_short_windows]
        guppy_long = [f"guppy_{window}" for window in guppy_long_windows]

        # Create a dataframe for the ensemble trades
        ensemble_trades = self.cheby_trades[['datetime', 'open', 'high', 'low', 'close', 'volume']].copy()
        ensemble_trades['signals'] = 0

        # Add a column for the strategy used, date and prc_consolidating
        ensemble_trades['strategy_used'] = np.where((self.gmma_trades['position'] != 0) | (self.gmma_trades['signals'] != 0), 'strat_gmma', 'strat_cheby')  
        ensemble_trades['date'] = ensemble_trades['datetime'].map(lambda x: x[:10])
        ensemble_trades['prc_consolidating'] = prc_consolidating(self.config, ensemble_trades, window=self.config.utils.prc_consolidating_window, prc_multiplier = self.config.utils.prc_multiplier)['prc_consolidating']
        
        # Variable to store the current position
        current_position = 0   

        # List to store the new rows to be added to the ensemble trades
        new_rows = []    

        # Dictionary to store the index of the gmma values for each date
        date_indexes = {date: self.gmma_values[self.gmma_values['datetime'] <= date].index[-1] 
                            for date in ensemble_trades['date'].unique() 
                            if len(self.gmma_values[self.gmma_values['datetime'] <= date]) != 0}

        # Variable to keep track of whether the GMMA strategy is active or not
        is_guppy_active = False

        # Iterate over the ensemble trades
        for i in tqdm(range(len(ensemble_trades))):

            # If the current timestamp is the last timestamp, then close all positions
            if i == len(ensemble_trades)-1:
                ensemble_trades.at[i, 'signals'] = -1*current_position
                continue

            # find the index of the gmma values for the current timestamp 
            if self.config.utils.trade_on == "close":
                index = date_indexes.get(ensemble_trades['date'].iloc[i+1])
            else:
                index = date_indexes.get(ensemble_trades['date'].iloc[i])

            if index is None:
                condition_cheby = True

            else:
                if index<0 or index >= len(self.gmma_values):
                    print("ERROR: index > len(self.gmma_values)", index, len(self.gmma_values))
                    break
                
                # Find the GMMA values for the current timestamp
                guppy_short_values = self.gmma_values.loc[index, guppy_short].values

                # Find whether Cheby-Butter strategy can be used 
                sorted_guppy_short_values = sorted(guppy_short_values)
                guppy_long_values = self.gmma_values.loc[index, guppy_long].values
                sorted_guppy_long_values = sorted(guppy_long_values)
                if crossover.type == "long_short":
                    condition_cheby = sorted_guppy_long_values[-1 - k_guppylong_entry] > sorted_guppy_short_values[0 + k_guppyshort_entry]     
                elif crossover.type == "short":
                    guppy_3_value = self.gmma_values.loc[index, "guppy_3"]
                    position = sorted_guppy_short_values.index(guppy_3_value)
                    condition_cheby = position > k_guppy_entry     

            # Find the current signal given the current position is 0
            if current_position == 0:
                # If market is consolidating according to PRC, then don't enter
                if ensemble_trades.at[i, "prc_consolidating"] == 1:
                    current_position = 0
                    ensemble_trades.at[i, 'signals'] = 0

                # If market is not consolidating, then check if the GMMA strategy is active
                elif self.gmma_trades.at[i, "signals"] == 1:
                    is_guppy_active = True
                    current_position = 1
                    ensemble_trades.at[i, "signals"] = 1

                # If GMMA strategy is not active, then check if the cheby strategy is active
                elif condition_cheby:
                    # If Cheby-Butter strategy is active, then take the corresponding position
                    if self.cheby_trades.at[i, "signals"] == 1:
                        current_position = 1
                        ensemble_trades.at[i, 'signals'] = 1
                    elif self.cheby_trades.at[i, "signals"] == -1:
                        current_position = -1
                        ensemble_trades.at[i, 'signals'] = -1
                    elif self.cheby_trades.at[i, "signals"] == 0:
                        current_position = 0
                        ensemble_trades.at[i, 'signals'] = 0
                    # Cheby-Butter strategy is inactive when 1w GMMA is ON but 1d GMMA is OFF

            # Find the current signal given the current position is -1
            elif current_position == -1:
                # If market is consolidating according to PRC, then close the short position
                if ensemble_trades.at[i, "prc_consolidating"] == 1:
                    current_position = 0
                    ensemble_trades.at[i, 'signals'] = 1

                # If market is not consolidating, then check if the GMMA strategy is active
                elif self.gmma_trades.at[i, "signals"] == 1:
                    current_position = 1
                    ensemble_trades.at[i, "signals"] = 1
                    new_rows.append(ensemble_trades.iloc[i].to_dict())

                # If GMMA strategy is not active, then check if the Cheby-Butter strategy is active
                elif condition_cheby:
                    # If Cheby-Butter strategy is active, then take the corresponding position
                    if self.cheby_trades.at[i, "signals"] == 1:
                        current_position = 0
                        ensemble_trades.at[i, 'signals'] = 1
                    elif self.cheby_trades.at[i, "signals"] == -1:
                        current_position = -1
                        ensemble_trades.at[i, 'signals'] = 0
                    elif self.cheby_trades.at[i, "signals"] == 0:
                        current_position = -1
                        ensemble_trades.at[i, 'signals'] = 0
                    # Cheby-Butter strategy is inactive when 1w GMMA is ON but 1d GMMA is OFF

            # Find the current signal given the current position is 1
            elif current_position == 1:
                # Check PRC to know if market is consolidating, then close the long position
                if ensemble_trades.at[i, "prc_consolidating"] == 1:
                    current_position = 0
                    ensemble_trades.at[i, 'signals'] = -1

                # If market is not consolidating, then check if the GMMA strategy is active
                elif self.gmma_trades.at[i, "signals"] == 1:
                    current_position = 1
                    ensemble_trades.at[i, "signals"] = 0
                    is_guppy_active = True

                # If GMMA strategy is active, then retain the position
                elif is_guppy_active and self.gmma_trades.at[i, "signals"] == 0:
                    current_position = 1
                    ensemble_trades.at[i, 'signals'] = 0

                # If GMMA strategy closes the position, then close the position
                elif self.gmma_trades.at[i, "signals"] == -1:
                    current_position = 0
                    ensemble_trades.at[i, 'signals'] = -1
                    is_guppy_active = False

                # If GMMA strategy is not active, then check if the Cheby-Butter strategy is active
                elif condition_cheby:
                    # If Cheby-Butter strategy is active, then take the corresponding position
                    if self.cheby_trades.at[i, "signals"] == 1:
                        current_position = 1
                        ensemble_trades.at[i, 'signals'] = 0
                    elif self.cheby_trades.at[i, "signals"] == -1:
                        current_position = 0
                        ensemble_trades.at[i, 'signals'] = -1
                    elif self.cheby_trades.at[i, "signals"] == 0:
                        current_position = 1
                        ensemble_trades.at[i, 'signals'] = 0
                    # Cheby-Butter strategy is inactive when 1w GMMA is ON but 1d GMMA is OFF

        # Add the new rows to the dataframe
        new_rows = pd.DataFrame(new_rows)
        ensemble_trades = pd.concat([ensemble_trades, new_rows], ignore_index=True)

        # Sort the dataframe by datetime and reset the index
        ensemble_trades['Index'] = ensemble_trades.index
        ensemble_trades = ensemble_trades.sort_values(['datetime', 'Index'])
        ensemble_trades.drop(["Index"], axis=1, inplace=True)
        ensemble_trades.reset_index(drop=True, inplace=True)
        ensemble_trades.drop(["date"], axis=1, inplace=True)
        return ensemble_trades


                

    