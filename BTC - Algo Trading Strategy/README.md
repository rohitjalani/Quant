<div id="top"></div>

<!-- PROJECT LOGO -->
<br />

<!-- TABLE OF CONTENTS -->
<details>
  <summary>Table of Contents</summary>
  <ol>
    <li><a href="#about-the-project">About The Project</a></li>
    <li><a href="#setup">Setup</a></li>
    <li><a href="#codebase">Codebase</a></li>
    <li><a href="#contact">Contact</a></li>
    <li><a href="#acknowledgments">Acknowledgments</a></li>
  </ol>
</details>

<!-- ABOUT THE PROJECT -->

## About The Project

<!-- ![Screen Shot](assets/flow.png) -->
This project is focused on developing a trading strategy designed to yield profitable returns with lower associated risks via generating effective trade signals specifically for the BTC/USDT market. BTC/USDT refers to the trading pair involving Bitcoin (BTC) and Tether (USDT) on cryptocurrency exchanges. Tether is a type of stablecoin that is pegged to the value of the US dollar. This means that 1 USDT is generally intended to be equivalent to $1 USD.

Bitcoin being a highly volatile asset, we have employed a three-tier ensemble model with adaptive selection to make a robust final strategy which works effectively in all types of BTC/USDT chart patterns and market conditions.
The following strategies are used as input:
* **Chebyshev and Butterworth Filters crossover strategy (CBFCS)**
* **Guppy Multiple Moving Averages augmented Long-only strategy (GMMA-ALS)**
* **Percentage Range Consolidation augmented capital prevention (PRC-ACP)**

Along with this adaptive model selection based on market conditions, we have also employed various risk mitigation measures in each of the models, to ensure our capital remains safe and we do not take major losses.

Following are the metrics which are used to judge the performance of our strategy:
* Gross Profit
* Net Profit
* Total Closed Trades
* Win Rate (Profitability %)
* Max Drawdown
* Gross Loss
* Average Winning Trade (in USDT) 
* Average Losing Trade (in USDT)
* Buy and Hold Return of BTC
* Largest Losing Trade (in USDT)
* Largest Winning Trade (in USDT)
* Sharpe Ratio
* Sortino Ratio
* Average Holding Duration per Trade

Along with the signal generation, we have also backtested our strategy to check its performance in previous years, to know what can be expected ahead. The content following contains the code-patch working behind the scenes to generate the signals and run them on our custom backtester to get the final results.


<p align="right">(<a href="#top">back to top</a>)</p>

### Built With

Following mentioned are the major libraries used in this project.

 [python 3.11](https://www.python.org/downloads/release/python-3110/) | [pandas 2.1.4](https://pypi.org/project/pandas/) | [pandas 2.1.4](https://pypi.org/project/pandas/) | [pandas-ta 0.3.14b](https://pypi.org/project/pandas-ta/) | [numpy 1.26.2](https://pypi.org/project/numpy/) | [matplotlib 3.8.2](https://pypi.org/project/matplotlib/)


<p align="right">(<a href="#top">back to top</a>)</p>

# Setup

To get a local copy up and running follow these simple steps.

### Prerequisites

* A `data` folder containing the following three files
  * `/data/btcusdt_3m.csv`
  * `/data/btcusdt_1d.csv`
  * `/data/btcusdt_1w.csv`
* Each of the above files should contain the following columns

<div style="padding-left: 50px;">

| **datetime**     | **open**     | **high**     | **low**     | **close**     | **volume**     |
| :---: | :---: | :---: | :---: | :---: | :---: |

</div>

* Date ranges for the data
<div style="padding-left: 50px;">

| File Name      | Start Date            | End Date              |
| :---           | :---                  | :---                  |
| `btcusdt_3m.csv` | 2018-01-01 00:00:00   | 2023-11-30 23:57:00   |
| `btcusdt_1d.csv` | 2018-01-01            | 2023-11-30            |
| `btcusdt_1w.csv` | 2017-08-14            | 2023-11-27            |

</div>

### Installation

1. Update the `path` in the `config.yaml` file to the path of the data folder with three files

2. Install requirements
    ```sh
    pip install -r requirements.txt
    ```
3. Set the sample type in `config.yaml` to `full_sample` or `in_sample` or `out_sample`
4. Run main.py
    ```sh
    python main.py
    ```

<p align="right">(<a href="#top">back to top</a>)</p>


# Codebase

## File Structure

```

├── README.md
├── assets
├── output
├── requirements.txt
├── config.yaml
├── utils
│   ├── utils.py
│   ├── indicators.py
│   ├── strategies.py
│   ├── granularise.py
│   ├── align.py
│   ├── ensemble.py
│   ├── tpsl.py
│   └── backtester.py
├── main.ipynb
└── main.py

```


## config.yaml

` config.yaml` file provides a comprehensive set of parameters and settings for defining and configuring trading strategies, backtesting, and risk management. The configuration is organized into six main sections: data, strategies, and utils, stop_loss, take_profit, backtester.

  Below is a detailed breakdown of each section:

### data

* `path` - Path to the data folder
* `files` - Dictionary of file names and their respective timeframes
* `samples` - Dictonary of sample sizes and their respective start and end dates

<div style="padding-left: 50px;">

| Sample type | Period          | Start date  | End date    |
| :---:       | :---:           | :---:       | :---:       |
| `in_sample`   | Training period | 2018-01-01  | 2022-01-12  |
| `out_sample`  | Testing period  | 2022-01-13  | 2023-11-30  |
| `full_sample` | Full period     | 2018-01-01  | 2023-11-30  |

</div>

### strategies

* `strat_cheby` - Parameters for Chebyshev and Buttworth filter strategy
  * `butterworth` - Parameters for Butterworth filter
    * `order` - Order of the filter
    * `cutoff_frequency` - Cutoff frequency of the filter
  * `chebyshev` - Parameters for Chebyshev filter
    * `order` - Order of the filter
    * `ripple_factor` - Ripple of the filter
    * `cutoff_frequency` - Cutoff frequency of the filter
  * `crossover` - Parameters for crossover strategy
    * `type` - Type of crossover strategy (`long_short`, `short`)
      * `long_short` - We check crossover of both slow and fast moving EMAs with each other
        * `k_guppyshort_entry` - Determines which fast moving EMAs' line's crossover generates entry signal
        * `k_guppyshort_exit` - Determines which fast moving EMAs' line's crossover generates exit signal
        * `k_guppylong_entry` - Determines the crossover with which slow moving EMA generates entry signal
        * `k_guppylong_exit` - Determines the crossover with which slow moving EMA generates exit signal
      * `short` - We check crossover of fastest EMA with other fast moving EMAs
        * `k_guppy_entry` - Determines what should be the position of fastest EMA from top to be considered an entry signal
        * `k_guppy_exit` - Determines what should be the position of fastest EMA from top to be considered an exit signal
  * `skip_trade` - Skip trade if the price is above/below the moving average
    * `active` - Boolean value to activate/deactivate the skip trade
    * `duration` - Number of previous days to evaluate
    * `num_trades` - Number of loss making trades in the last `duration` days to skip the trade
    * `pct` - minimum percentage loss per trade to consider it as a loss making trade

* `strat_gmma` - Parameters for GMMA strategy
  * `gmma_short` - list of six ema periods for short term exponential moving averages
  * `gmma_long` - list of six ema periods for long term exponential moving averages
  * `crossover` - Parameters for crossover strategy
    * `type` - Type of crossover strategy (`long_short`, `short`)
      * `long_short` -We check crossover of both slow and fast moving EMAs with each other
        * `k_guppyshort_entry` - Determines which fast moving EMAs' line's crossover generates entry signal
        * `k_guppyshort_exit` - Determines which fast moving EMAs' line's crossover generates exit signal
        * `k_guppylong_entry` - Determines the crossover with which slow moving EMA generates entry signal
        * `k_guppylong_exit` - Determines the crossover with which slow moving EMA generates exit signal
      * `short` - We check crossover of fastest EMA with other fast moving EMAs
        * `k_guppy_entry` - Determines what should be the position of fastest EMA from top to be considered an entry signal
        * `k_guppy_exit` - Determines what should be the position of fastest EMA from top to be considered an exit signal
    

### utils

* `sample` - Specifies which sample (`out_sample`, `in_sample`, `full_sample`) to use for analysis
* `timeframes` - Specifies timeframes for each strategy
  * `strat_cheby` - Timeframe for **CBFCS** strategy
  * `strat_gmma_1` - Long Timeframe for the **GMMA-ALS** strategy
  * `strat_gmma_2` - Short Timeframe for the **GMMA-ALS** strategy
  * `granularise` - Timeframe to granularise the data to combine the signals from different strategies

* `stop_loss` - Global boolean value to activate/deactivate stop-loss functionality
* `take_profit` - Global boolean value to activate/deactivate take-profit functionality
* `trade_on` - Specifies whether to enter trades at the open or close of a candle
* `npr_consolidating_window` - Window size for consolidating noise power ratio
* `npr_multiplier` - Multiplier for noise power ratio
* `dont_take_next_cheby_trade` - Boolean value to skip the next trade if the previous trade was a Chebyshev trade

### stop_loss

* `strat_cheby` - Stop loss parameters for **CBFCS** strategy
  * `type` - Type of stop loss (`simple`, `trailing`, `null`)
  * `limit` - Maximum loss allowed in percentage ratio
  * `retrade` - Boolean value to re-enter the trade after hitting stop loss
  * `retrade_frequency` - Frequency at which to re-enter the trade ("3m" or "1d")
* `strat_gmma` - Stop loss parameters for **GMMA-ALS** strategy
  * `type` - Type of stop loss (`simple`, `trailing`, `null`)
  * `limit` - Maximum loss allowed
  * `retrade` - Boolean value to re-enter the trade after hitting stop loss
  * `retrade_frequency` - Frequency at which to re-enter the trade ("3m" or "1d")
* `retrade_after` - Number of days to wait before re-entering a trade

### take_profit

* `strat_cheby` - Take profit parameters for **CBFCS** strategy
  * `active` - Boolean Value to enable/disable take profit
  * `limit` - Maximum gain allowed in percentage ratio
* `strat_gmma` - Take profit parameters for **GMMA-ALS** strategy
  * `active` - Boolean Value to enable/disable take profit
  * `limit` - Maximum gain allowed in percentage ratio

### backtester

* `capital` - Initial capital for backtesting
* `transaction_cost` - Cost and slippage per transaction as a percentage of the transaction amount (e.g., 0.1% implies 0.05% for opening and 0.05% for closing a position)
* `print_statistics` - Boolean value to print detailed statistics after backtesting
* `compounding` - Boolean value to enable/disable compounding
* `plots` - Various plot configurations for visualizing backtest results
  * `active` - Boolean value to enable/disable creating graphs
  * `plot` - Boolean value to enable/disable plotting
  * `save` - Boolean value to save plots as JPG files
  * `drawdown` - Boolean value to enable/disable drawdown plot
  * `entry_exit` - Configuration for entry/exit plots
    * `candles` - Boolean value to show/hide candlestick plot
    * `line` - Boolean value to show/hide entry/exit line plot
  * `returns` - Boolean value to enable/disable returns plot
  * `holding_duration` - Boolean value to enable/disable holding duration plot
  * `sharpe` - Boolean value to enable/disable Sharpe ratio plot
  * `portfolio_value` - Boolean value to enable/disable portfolio value plot

## indicators.py

This file contains the ***prc_consolidating*** function, which computes prc_consolidating values for timestamps using given configurations and data.

## strategies.py


This file contains codes of all the strategies used for signal generation namely
1. **StratCheby:** Chebyshev Butterworth filters crossover strategy
2. **StratGMMA:** Guppy Multiple Moving Averages (GMMA) augmented long-only strategy
3. **MixedStratGMMA:** Takes a combination of two different StratGMMAs which are run on two different timeframes

## granularise.py

* This file contains GranulariseTrades Class for granularising trades from different strategies to the same timestamps to make an ensemble of different strategies.
* This class converts trades from daily and weekly timeframes to three minute timeframe.


## align.py
* This file contains Aligner Class for aligning trades from different strategies to the same timestamps. 
* For making an ensemble of different strategies, we need to align the trades from different strategies to the same timestamps.


## ensemble.py

* This file contains the Ensmeble Class for making an ensemble of different strategies. 
* The ensemble is made by the following method:
    1. Check if the market is consolidating or not using the PRC indicator.
    2. If the market is consolidating, then don't enter any position.
    3. If the market is not consolidating, then check if the GMMA strategy is active.
    4. If the GMMA strategy is active, then take the corresponding position.
    5. If the GMMA strategy is not active, then check if the Cheby strategy is active.
    6. If the Cheby-Butter strategy is active, then take the corresponding position.

## tpsl.py
* This file contains the TPSL class to implement the stop loss and Take profit functionality. 
* It takes the trades dataframe as input and returns the same dataframe with the stop loss and take Profit applied.

* It implements 2 types of stop loss:
  1. **Simple stop loss:** This is a simple stop which calculates the stop loss with respect to the price at which the trade is entered.
  2. **Trailing stop loss:** This is a trailing stop loss which calculates the stop loss with respect to the highest price reached after the trade is entered.


## backtester.py
* This file contains the Backtester class for backtesting the strategy

## output
* All the output files are saved in the output folder.
* Output files contain
  * signals.csv - Contains the signals generated by the ensemble strategy
  * logs.csv - Contains the logs of the trades taken by the ensemble strategy
  * stats.json - Contains the statistics of the backtest
  * results.csv - Contains an extensive list of statistics of the backtest
  * Various plots generated during the backtest are saved in this folder
<p align="right">(<a href="#top">back to top</a>)</p>

## main.ipynb
* This notebook contains the results of the backtest on the in-sample and out-sample data.

<p align="right">(<a href="#top">back to top</a>)</p>
