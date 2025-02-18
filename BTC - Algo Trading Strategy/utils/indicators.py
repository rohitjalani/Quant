import numpy as np
import pandas as pd

'''
This file contains codes of all the indicators used for signal generation namely
1. prc_consolidating: Percentage Range Consolidation indicator used to find consolidating periods
'''

def prc_consolidating(config, data, window, prc_multiplier):
    """
    Calculate the prc_consolidating value for all timestamps.
    
    Method;
        Check if the current candle lies within the threshold of min and max of the previous n candles
    
    Parameters:
        data (pd.DataFrame): DataFrame containing 'Close' column.
        config: Contains prc_consolidating_window
        window: Determines how many of the previous candles to check
        prc_multiplier: Determines the threshold of High and Low of window candles within which the current candle should lie to be considered a consolidating period

    Returns:
        pd.Series: prc_consolidating values for each timestamp.
    """
    prc_series = []
    curr_min = data['low'].rolling(window=window, min_periods=window).min()
    curr_max = data['high'].rolling(window=window, min_periods=window).max()

    enter_on = config.utils.trade_on
    
    for i in range(len(data)):
        if i <= window - 1:
            prc_consolidating = 0
        else:
            if enter_on == 'open':
                if prc_multiplier * data['low'].iloc[i] >= curr_min.iloc[i-1] and data['high'].iloc[i] <= prc_multiplier * curr_max.iloc[i-1]:
                    prc_consolidating = 1
                else:
                    prc_consolidating = 0
            elif enter_on == 'close':
                if prc_multiplier * data['low'].iloc[i] >= curr_min.iloc[i] and data['high'].iloc[i] <= prc_multiplier * curr_max.iloc[i]:
                    prc_consolidating = 1
                else:
                    prc_consolidating = 0
        prc_series.append(prc_consolidating)

    prc_series = pd.Series(prc_series, name='prc_consolidating', index=data.index)
    prc_series = pd.DataFrame(prc_series)
    return prc_series
