import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

'''
This file contains the whole Backtester code.
'''

class BacktesterCore:
    '''
    Core backtester class that takes in a dataframe of trades and backtests it
    '''
    def __init__(self, capital, transaction_cost, enter_on, exit_on):
        '''
        Initialize the backtester with the capital, transaction cost, enter_on and exit_on
        capital: the initial capital to start with
        transaction_cost: the transaction cost(as multiplier, not as percentage) of the trade value which is applied to both buy and sell
        enter_on: whether to enter on open or close
        exit_on: whether to exit on open or close
        '''
        self.capital = capital
        self.percent_transaction_cost = transaction_cost
        self.enter_on = enter_on
        self.exit_on = exit_on
        self.results = []

    def backtest(self, df_trades, compound):
        '''
        df_trades.columns = ['datetime', 'signals', 'open', 'high', 'low', 'close', 'signals']
        df_trades['signals'] = 1 means buy, -1 means sell, 0 means hold
        df_trades['datetime'] = datetime object or can pass integer index
        compound: if True, then the capital is compounded, else the capital is reset to initial capital after each trade
        '''
        current_position = 0 # 0 means not trading, 1 means long, -1 means short
        capital = self.capital
        current_volume = 0
        transaction_cost = 0.0
        starting_time = 0
        max_drawdown = 0
        runup = 0
        buy_price = 0
        sell_price = 0
        max_runup = 0
        trades_closed = 0
        win_trades = 0
        losing_trades = 0
        gross_profit = 0
        gross_loss = 0
        drawdown = 0
        runup = 0
        max_value = capital
        min_value = capital
        drawdown_percentage = 0
        runup_percentage = 0
        initial_capital = capital
        current_portfolio_value = self.capital

        for index, trade in df_trades.iterrows():
            # different cases depending on whether we are currently not trading, long or short
            if current_position == 0:
                drawdown = 0
                runup = 0
                max_value = capital
                min_value = capital
                profit = 0
                pnl_percentage = 0
                drawdown_percentage = 0
                runup_percentage = 0
                current_portfolio_value = capital
                if trade['signals'] == 0 or index == len(df_trades) - 1:
                    # if no signal is given, or if it is the last timestamp, then do nothing
                    transaction_cost = 0
                elif trade['signals'] == 1:
                    # enter a long position
                    # starting_time = trade['datetime']
                    starting_time = index
                    initial_capital = capital
                    # if we have $1000, and are paying say 10 percent of the trade value as 
                    # transaction cost, then naively we would assume 100 is the transaction cost
                    # but 10 percent of 900 is just 90. instead we can buy 1000/(1+0.1) = 909.09 worth of stock
                    # and pay the transaction cost of 90.909
                    transaction_cost = self.percent_transaction_cost * capital/(1+self.percent_transaction_cost)
                    current_volume = (capital-transaction_cost)/(trade[self.enter_on])
                    current_position = 1
                    buy_price = capital
                    capital = 0
                elif trade['signals'] == -1:
                    # enter a short position
                    # starting_time = trade['datetime']
                    starting_time = index
                    initial_capital = capital
                    transaction_cost = self.percent_transaction_cost * capital/(1+self.percent_transaction_cost)
                    current_volume = (capital-transaction_cost)/(trade[self.enter_on])
                    current_position = -1
                    # deduct transaction cost from the capital now, and on closing the trade we will use this capital to buy back the stock
                    capital = capital - transaction_cost
                    sell_price = capital
                if self.enter_on=='open' and current_position != 0:
                    # if we are entering the trade on day open, then drawdown should include the price fluctuations of the current day
                    if current_position == 1:
                        current_portfolio_value = current_volume * trade['close']
                        max_value = max(max_value, current_volume*trade['high'])
                        min_value = min(min_value, current_volume*trade['low'])
                    elif current_position == -1:
                        current_portfolio_value = capital + sell_price - current_volume*trade['close']
                        max_value = max(max_value, capital + sell_price - current_volume*trade['low'])
                        min_value = min(min_value, capital + sell_price - current_volume*trade['high'])
                    drawdown = max_value - current_portfolio_value
                    runup = current_portfolio_value - min_value
                    drawdown = max(drawdown, 0)
                    runup = max(runup, 0)
                    max_drawdown = max(max_drawdown, drawdown)
                    max_runup = max(max_runup, runup)
                    drawdown_percentage = drawdown / max_value * 100 if max_value != 0 else 0
                    runup_percentage = runup / min_value * 100 if min_value != 0 else 0
                
                result = [profit, gross_profit, gross_loss, 0, trades_closed, win_trades, losing_trades, drawdown, max_drawdown, runup, max_runup, 0, current_volume, transaction_cost, current_position, capital, drawdown_percentage, runup_percentage, current_portfolio_value]

            elif current_position == 1:
                # if we are exiting the trade on day end, then drawdown should include the price fluctuations of the current day
                if self.exit_on == 'close' or trade['signals'] != -1:
                    max_value = max(max_value, current_volume*trade['high'])
                    min_value = min(min_value, current_volume*trade['low'])
                profit = 0
                current_portfolio_value = current_volume * trade[self.exit_on]
                drawdown = max_value - current_portfolio_value
                drawdown = max(drawdown, 0)
                runup = current_portfolio_value - min_value
                runup = max(runup, 0)
                max_drawdown = max(max_drawdown, drawdown)
                max_runup = max(max_runup, runup)
                drawdown_percentage = drawdown / max_value * 100 if max_value != 0 else 0
                runup_percentage = runup / min_value * 100 if min_value != 0 else 0
                # if exit is on day open, then update the max_value and min_value after drawdown and runup calculation
                # this is then automatically taken care of when calculating drawdown and runup for the next timestamp
                if self.exit_on == 'open':
                    max_value = max(max_value, current_volume*trade['high'])
                    min_value = min(min_value, current_volume*trade['low'])

                if trade['signals'] == 1:
                    # raise error
                    raise Exception("Error: already long, index: ", index)
                elif trade['signals'] == -1 or index == len(df_trades) - 1:
                    # close the long position
                    # end_time = trade['datetime']
                    end_time = index
                    transaction_cost = self.percent_transaction_cost * current_portfolio_value
                    profit_for_current_trade = current_portfolio_value - initial_capital
                    capital = current_portfolio_value - transaction_cost
                    if capital < 0:
                        raise Exception("Error: negative capital")
                    current_position = 0
                    trades_closed += 1
                    if profit_for_current_trade > 0:
                        gross_profit += profit_for_current_trade
                    else:
                        gross_loss += profit_for_current_trade
                    profit = capital - initial_capital  # profit is the overall profit, including the transaction cost
                    if profit>0:
                        win_trades += 1 # win trades is the number of trades that are profitable
                        # this should obviously have the transaction cost deducted from it
                    else:
                        losing_trades += 1
                    current_volume = 0
                    pnl_percentage = profit_for_current_trade / buy_price * 100
                    result = [profit, gross_profit, gross_loss, pnl_percentage, trades_closed, win_trades, losing_trades, drawdown, max_drawdown, runup, max_runup, end_time - starting_time, current_volume, transaction_cost, current_position, capital, drawdown_percentage, runup_percentage, current_portfolio_value]
                    # if we are not compounding, then reset the capital to initial capital
                    if not compound:
                        capital = self.capital
                    max_value = capital
                    min_value = capital

                elif trade['signals'] == 0:
                    transaction_cost = 0
                    result = [profit, gross_profit, gross_loss, 0, trades_closed, win_trades, losing_trades, drawdown, max_drawdown, runup, max_runup, 0, current_volume, transaction_cost, current_position, capital, drawdown_percentage, runup_percentage, current_portfolio_value]
            elif current_position == -1:
                current_portfolio_value = capital + sell_price - current_volume*trade[self.exit_on]
                # if current portfolio value is negative, raise error
                if current_portfolio_value <= 0:
                    raise Exception("Error: negative portfolio value")
                # if we are exiting the trade on day end, then drawdown should include the price fluctuations of the current day
                if self.exit_on == 'close' or trade['signals'] != 1:
                    max_value = max(max_value, capital + sell_price - current_volume*trade['low'])
                    min_value = min(min_value, capital + sell_price - current_volume*trade['high'])
                profit = 0
                profit_for_current_trade = 0
                # calculate the drawdown and runup
                drawdown = max_value-current_portfolio_value
                drawdown = max(drawdown, 0)
                runup = current_portfolio_value - min_value
                runup = max(runup, 0)
                max_drawdown = max(max_drawdown, drawdown)
                max_runup = max(max_runup, runup)
                drawdown_percentage = drawdown / max_value * 100 if max_value != 0 else 0
                runup_percentage = runup / min_value * 100 if min_value != 0 else 0
                # if exit is on day open, then update the max_value and min_value after drawdown and runup calculation
                if self.exit_on == 'open':
                    max_value = max(max_value, capital + sell_price - current_volume*trade['low'])
                    min_value = min(min_value, capital + sell_price - current_volume*trade['high'])

                if trade['signals'] == 1 or index == len(df_trades) - 1:
                    # close the short position if we get the signal or if it is the last timestamp
                    # end_time = trade['datetime']
                    end_time = index
                    transaction_cost = self.percent_transaction_cost * current_volume * trade[self.exit_on]
                    capital = capital + sell_price - (current_volume * trade[self.exit_on]) - transaction_cost
                    profit_for_current_trade = capital - initial_capital + transaction_cost
                    if capital < 0:
                        raise Exception("Error: negative capital")

                    current_position = 0
                    current_volume = 0
                    trades_closed += 1
                    if profit_for_current_trade > 0:
                        gross_profit += profit_for_current_trade
                    else:
                        gross_loss += profit_for_current_trade

                    profit = capital - initial_capital
                    if profit>0:
                        win_trades += 1
                    else:
                        losing_trades += 1
                    pnl_percentage = profit_for_current_trade / sell_price * 100
                    result = [profit, gross_profit, gross_loss, pnl_percentage, trades_closed, win_trades, losing_trades, drawdown, max_drawdown, runup, max_runup, end_time - starting_time, current_volume, transaction_cost, current_position, capital, drawdown_percentage, runup_percentage, current_portfolio_value]

                    if not compound:
                        capital = self.capital
                    max_value = capital
                    min_value = capital
                    runup = 0
                    drawdown = 0
                    runup_percentage = 0
                    drawdown_percentage = 0

                elif trade['signals'] == -1:
                    # raise error
                    raise Exception("Error: already short, index: ", index)
                elif trade['signals'] == 0:
                    transaction_cost = 0
                    result = [profit, gross_profit, gross_loss, 0, trades_closed, win_trades, losing_trades, drawdown, max_drawdown, runup, max_runup, 0, current_volume, transaction_cost, current_position, capital, drawdown_percentage, runup_percentage, current_portfolio_value]
            self.results.append(result)
        # append everything to a dataframe and return it for bookkeeping
        df_results = pd.DataFrame(self.results, columns=['Trade_Profit', 'Gross_profit', 'Gross_loss', 'PnL %', 'Trades_closed', 'Win_trades', 'Losing_trades', 'Drawdown', 'Max_Drawdown', 'Runup', 'Max_Runup', 'Holding time', 'Volume', 'Transaction_cost', 'Currently_holding', 'Capital', 'Drawdown_percentage', 'Runup_percentage', 'Current_value_of_portfolio'])
        return df_results

    def max_drawdown(self, df_results):
        ret = df_results.copy()
        ret['curr_max_portfolio_val'] = ret['Current_value_of_portfolio'].cummax()
        ret['drawdown'] = ret['Current_value_of_portfolio'] - ret['curr_max_portfolio_val']
        ret['drawdown_pct'] = ret['drawdown'] / ret['curr_max_portfolio_val']*100
        return ret['drawdown_pct'].min()

    def gross_profit(self, df_results):
        # Gross profit is the gross profit of last row as it is cumulative
        return df_results.iloc[-1]['Gross_profit']

    def net_profit(self, df_results):
        # Net profit is sum of all the trade profits. this includes the transaction cost
        return df_results['Trade_Profit'].sum()
    
    def total_closed_trades(self, df_results):
        return df_results.iloc[-1]['Trades_closed']

    def win_rate(self, df_results):
        return df_results.iloc[-1]['Win_trades'] / df_results.iloc[-1]['Trades_closed'] if df_results.iloc[-1]['Trades_closed'] > 0 else 0

    def max_dip(self, df_results):
        return df_results['Drawdown_percentage'].max()

    def max_runup(self, df_results):
        return df_results['Runup_percentage'].max()

    def gross_loss(self, df_results):
        return df_results.iloc[-1]['Gross_loss']

    def average_winning_trade(self, df_results):
        return df_results[df_results['Trade_Profit']>0]['Trade_Profit'].mean()

    def average_losing_trade(self, df_results):
        return df_results[df_results['Trade_Profit']<0]['Trade_Profit'].mean()

    def buy_and_hold_return_of_btc(self, df_trades):
        # Assume we buy on open price of first day and sell on close price of last day
        trade_volume = self.capital / (df_trades.iloc[0]['open']*(1+self.percent_transaction_cost))
        buy_and_hold_return = trade_volume * df_trades.iloc[-1]['close']*(1-self.percent_transaction_cost) - self.capital
        return buy_and_hold_return

    def largest_losing_trade(self, df_results):
        return df_results['Trade_Profit'].min()

    def largest_winning_trade(self, df_results):
        return df_results['Trade_Profit'].max()

    def average_holding_duration(self, trade_logs):
        # convert the entry and exit times to datetime objects and then find the difference
        durations = pd.to_datetime(trade_logs['Exit_time']) - pd.to_datetime(trade_logs['Entry_time'])
        return durations.mean()

    def sharpe_ratio(self, df_results):
        # We annualise the pnl percentage by multiplying it by the annualisation factor
        returns = df_results['PnL %']
        returns = returns[returns!=0]
        sharpe_ratio = np.sqrt(365) * returns.mean()/ returns.std() if returns.std() != 0 else np.nan    #TODO: change 365 to accomodate different timeframes insteadnof day
        return sharpe_ratio

    def sortino_ratio(self, df_results):
        # Sortino considers the standard deviation of only the negative returns
        returns = df_results['PnL %']
        downside_returns = -returns[returns < 0]
        returns = returns[returns!=0]
        sortino_ratio = (np.sqrt(365) * returns.mean()) / downside_returns.std() if downside_returns.std() != 0 else np.nan
        return sortino_ratio

    def get_statistics(self, df_results, df_trades, trade_logs):
        gross_profit = self.gross_profit(df_results)
        net_profit = self.net_profit(df_results)
        total_closed_trades = self.total_closed_trades(df_results)
        win_rate = self.win_rate(df_results)
        max_drawdown = self.max_drawdown(df_results)
        max_dip = self.max_dip(df_results)
        max_runup = self.max_runup(df_results)
        gross_loss = self.gross_loss(df_results)
        average_winning_trade = self.average_winning_trade(df_results)
        average_losing_trade = self.average_losing_trade(df_results)
        largest_losing_trade = self.largest_losing_trade(df_results)
        largest_winning_trade = self.largest_winning_trade(df_results)
        average_holding_duration = self.average_holding_duration(trade_logs)
        sharpe_ratio = self.sharpe_ratio(df_results)
        sortino_ratio = self.sortino_ratio(df_results)
        buy_and_hold_return = self.buy_and_hold_return_of_btc(df_trades)
        return [gross_profit, net_profit, total_closed_trades, win_rate, max_dip, max_runup, gross_loss, average_winning_trade, average_losing_trade, largest_losing_trade, largest_winning_trade, average_holding_duration, sharpe_ratio, sortino_ratio, buy_and_hold_return, max_drawdown]

    def print_statistics(self, df_results, df_trades, trade_logs):
        statistics = self.get_statistics(df_results, df_trades, trade_logs)
        # Print the statistics in a nice format
        print(f"Gross profit: {statistics[0]}")
        print(f"Net profit: {statistics[1]}")
        print(f"Total closed trades: {statistics[2]}")
        print(f"Win rate: {statistics[3]*100} %")
        print(f"Max dip: {statistics[4]} %")
        print(f"Max runup: {statistics[5]} %")
        print(f"Gross loss: {-statistics[6]}")
        print(f"Average winning trade: {statistics[7]}")
        print(f"Average losing trade: {statistics[8]}")
        print(f"Buy and hold return of BTC: {statistics[14]}")
        print(f"Largest winning trade: {statistics[10]}")
        print(f"Largest losing trade: {statistics[9]}")
        print(f"Sharpe ratio: {statistics[12]}")
        print(f"Sortino ratio: {statistics[13]}")
        print(f"Average holding duration: {statistics[11]}")
        print(f"Max drawdown: {statistics[15]}")

    def generate_tradelogs(self, df_results, df_trades):
        # For all trades, we generate a log
        trade_logs = pd.DataFrame(columns=['Entry_time', 'Entry_price', 'Exit_time', 'Exit_price', 'Long/Short', 'Volume', 'Profit', 'PnL %', 'Capital', 'Max_Drawdown'])
        in_trade = False
        max_drawdown = 0
        for index, trade in df_results.iterrows():
            max_drawdown = max(max_drawdown, trade['Drawdown_percentage'])
            if(df_trades['signals'].iloc[index]==0):
                continue
            if not in_trade:
                # We are entering a trade
                max_drawdown = 0
                in_trade = True
                entry_time = df_trades.iloc[index]['datetime']
                entry_price = df_trades.iloc[index][self.enter_on]
                volume = trade['Volume']
                long_short = ''
                if(df_trades['signals'].iloc[index]==1):
                    long_short = 'Long'
                else:
                    long_short = 'Short'
                trade_logs.loc[len(trade_logs), ['Entry_time', 'Entry_price', 'Long/Short', 'Volume']] = [entry_time, entry_price, long_short, volume]
            else:
                # We are exiting a trade
                in_trade = False
                trade_logs.at[len(trade_logs)-1, "Exit_time"] = df_trades.iloc[index]['datetime']
                trade_logs.at[len(trade_logs)-1, "Exit_price"] = df_trades.iloc[index][self.exit_on]
                trade_logs.at[len(trade_logs)-1, "Profit"] = trade['Trade_Profit']
                trade_logs.at[len(trade_logs)-1, "PnL %"] = trade['PnL %']
                trade_logs.at[len(trade_logs)-1, "Capital"] = trade['Capital']
                trade_logs.at[len(trade_logs)-1, "Max_Drawdown"] = max_drawdown
        
        if df_trades['signals'].sum()!=0:
            # if we are still in a trade, then we have to exit it at the last timestamp
            trade_logs.at[len(trade_logs)-1, "Exit_time"] = df_trades.iloc[-1]['datetime']
            trade_logs.at[len(trade_logs)-1, "Exit_price"] = df_trades.iloc[-1][self.exit_on]
            trade_logs.at[len(trade_logs)-1, "Profit"] = df_results.iloc[-1]['Trade_Profit']
            trade_logs.at[len(trade_logs)-1, "PnL %"] = df_results.iloc[-1]['PnL %']
            trade_logs.at[len(trade_logs)-1, "Capital"] = df_results.iloc[-1]['Capital']
            trade_logs.at[len(trade_logs)-1, "Max_Drawdown"] = max_drawdown



        return trade_logs
    

    def plot_returns(self, df_results, plot = True, save = False):
        # Create a line plot of the returns with the trade_logs['Exit_time'] as the x axis and cumulative trade_logs['Profit'] as the y axis
        plt.figure(figsize=(40,20))
        plt.plot(df_results.index, df_results['Trade_Profit'].cumsum(), color='black', lw=1)
        plt.xlabel('Time')
        plt.ylabel('Cumulative returns')
        # title
        plt.title('Cumulative returns')
        if save:
            plt.savefig('./output/returns.png')
        if plot:
            plt.show()

    def plot_drawdown(self, trade_logs, plot = True, save = False):
        # Create a line plot of the drawdown with the trade_logs['Exit_time'] as the x axis and trade_logs['Max_Drawdown'] as the y axis
        plt.figure(figsize=(40,20))
        plt.plot(trade_logs.index, trade_logs['Max_Drawdown'], color='black', lw=1)
        plt.xlabel('Trades')
        plt.ylabel('Drawdown')
        # title
        plt.title('Drawdown')
        if save:
            plt.savefig('./output/drawdown.png')    
        if plot:
            plt.show()
    
    def plot_entry_exit_with_candlesticks(self, df_trades, entry_on='close', save = False, plot = True):
        # create candlestick plot with entry and exit points
        # use open high low and close from df_trades and entry and exit from df_trades['signals']
        # create figure of maximum size
        plt.figure(figsize=(40,20))
        up = df_trades[df_trades['close']>=df_trades['open']]
        down = df_trades[df_trades['close']<df_trades['open']]
        col1 = 'green'
        col2 = 'red'
        width = 0.9
        width2 = 0.09
        plt.bar(up.index, up.close-up.open, width, bottom=up.open, color=col1) 
        plt.bar(up.index, up.high-up.close, width2, bottom=up.close, color=col1) 
        plt.bar(up.index, up.low-up.open, width2, bottom=up.open, color=col1) 
        
        # Plotting down prices of the stock 
        plt.bar(down.index, down.close-down.open, width, bottom=down.open, color=col2) 
        plt.bar(down.index, down.high-down.open, width2, bottom=down.open, color=col2) 
        plt.bar(down.index, down.low-down.close, width2, bottom=down.close, color=col2) 
        # add a green arrow at entry points and red arrow at exit points
        plt.scatter(df_trades[df_trades['signals']==1].index, df_trades[df_trades['signals']==1][entry_on], marker='^', color='green', s = 100)
        plt.scatter(df_trades[df_trades['signals']==-1].index, df_trades[df_trades['signals']==-1][entry_on], marker='v', color='red', s = 100)
            
        # rotating the x-axis tick labels at 30degree  
        # towards right 
        plt.xticks(rotation=30, ha='right') 
        # title
        plt.title('Candlestick chart')

        if save:
            plt.savefig('./output/candlestick.png')
        if plot:
            plt.show()
        
        
    def plot_entry_exit_with_line(self, df_trades, entry_exit_on='close', save = False, plot = True):
        # create line plot with entry and exit points
        # use open high low and close from df_trades and entry and exit from df_trades['signals']
        plt.figure(figsize=(40,20))
        # thick black line
        plt.plot(df_trades.index, df_trades[entry_exit_on], color='black', lw=0.5)

        plt.scatter(df_trades[df_trades['signals']==1].index, df_trades[df_trades['signals']==1][entry_exit_on], marker='^', color='green', s=100)
        plt.scatter(df_trades[df_trades['signals']==-1].index, df_trades[df_trades['signals']==-1][entry_exit_on], marker='v', color='red', s=100)
        plt.xlabel('Date')
        plt.xticks(rotation=30, ha='right') 
        # title
        plt.title('Entry and exit points')
        if save:
            plt.savefig('./output/entry_exit.png')
        if plot:
            plt.show()

    def plot_rolling_sharpe_ratio(self, trade_logs, save = False, plot = True):
        # take pnl % from trade_logs and plot the rolling sharpe ratio
        returns = trade_logs['PnL %']
        means = np.empty(len(returns))
        stds = np.empty(len(returns))
        # find cumulative values of returns.mean() and returns.std()
        for i in range(1,len(returns)):
            means[i] = returns[:i].mean()
            stds[i] = returns[:i].std()
        # plot the rolling sharpe ratio

        epsilon = 1e-8  # small constant
        sharpe_ratio = np.sqrt(365) * means / (stds + epsilon)
        plt.figure(figsize=(40,20))
        plt.plot(trade_logs.index, sharpe_ratio, color='black', lw=1)
        # add x and y axis
        
        plt.xlabel('Trades')
        plt.ylabel('Sharpe ratio')
        # title
        plt.title('Rolling Sharpe ratio')
        if save:
            plt.savefig('./output/sharpe.png')
        if plot:
            plt.show()

    def plot_holding_duration(self, trade_logs, save = False, plot = True):
        trade_logs['Exit_time'] = pd.to_datetime(trade_logs['Exit_time'])
        trade_logs['Entry_time'] = pd.to_datetime(trade_logs['Entry_time'])
        holding_duration = trade_logs['Exit_time'] - trade_logs['Entry_time']
        # holding_duration = trade_logs['Exit_time'] - trade_logs['Entry_time']
        plt.figure(figsize=(40,20))
        plt.plot(trade_logs.index, holding_duration, color='black', lw=1)
        plt.xlabel('Time')
        plt.ylabel('Holding duration')
        # title
        plt.title('Holding duration')
        if save:
            plt.savefig('./output/holding_duration.png')
        if plot:
            plt.show()

    def plot_portfolio_value(self, df_results, save = False, plot = True):
        plt.figure(figsize=(40,20))
        plt.plot(df_results.index, df_results['Current_value_of_portfolio'], color='black', lw=1)
        plt.xlabel('Time')
        plt.ylabel('Portfolio value')
        # title
        plt.title('Portfolio value')
        if save:
            plt.savefig('./output/portfolio_value.png')
        if plot:
            plt.show()
    



            
    

# Use the wrapper design pattern that calls and runs the BacktesterCore
class Backtester:
    '''
    Wrapper class for the BacktesterCore
    '''
    def __new__(cls, config):
        '''
        Singleton design pattern. We only want one instance of the backtester to exist and then use it throughout the program
        '''
        if not hasattr(cls, 'instance'):
            cls.instance = super(Backtester, cls).__new__(cls)
            cls.instance.config = config
        return cls.instance
    
    def __init__(self, config):
        self.config = config
        self.capital = self.config.backtester.capital
        self.transaction_cost = self.config.backtester.transaction_cost
        self.print_statistics = self.config.backtester.print_statistics
        self.compounding = self.config.backtester.compounding
        self.plots = self.config.backtester.plots

        self.enter_on = self.config.utils.trade_on
        self.exit_on = self.config.utils.trade_on
        
    def getBacktestingResults(self, df_trades):
        '''
        df_trades: dataframe of trades with columns = ['datetime', 'signals', 'open', 'high', 'low', 'close', 'signals']
        capital: the initial capital we start with
        transaction_cost: (default=1000000) the transaction cost(as multiplier, not as percentage) of the trade value which is applied to both buy and sell
        enter_on: (default='close') whether to enter on open or close
        exit_on: (default='close') whether to exit on open or close
        print_statistics: (default=True) whether to print the statistics or not
        compounding: (default=True) whether to compound the capital or not
        '''

        if self.enter_on not in ['open', 'close']:
            raise Exception("Error: enter_on should be either 'open' or 'close'")
        if self.exit_on not in ['open', 'close']:
            raise Exception("Error: exit_on should be either 'open' or 'close'")
        # We pass half the transaction cost to the backtester core as the transaction cost is split between the buy and sell
        bt = BacktesterCore(self.capital, self.transaction_cost/2, self.enter_on, self.exit_on)
        results = bt.backtest(df_trades, compound = self.compounding)
        trade_logs = bt.generate_tradelogs(results, df_trades)

        statistics = bt.get_statistics(results, df_trades, trade_logs)
        statistics_dict = {
            'Gross profit': statistics[0],
            'Net profit': statistics[1],
            'Total closed trades': statistics[2],
            'Win rate': statistics[3],
            'Max drawdown': statistics[4],
            'Max runup': statistics[5],
            'Gross loss': statistics[6],
            'Average winning trade': statistics[7],
            'Average losing trade': statistics[8],
            'Buy and hold return of BTC': statistics[14],
            'Largest winning trade': statistics[10],
            'Largest losing trade': statistics[9],
            'Sharpe ratio': statistics[12],
            'Sortino ratio': statistics[13],
            'Average holding duration': str(statistics[11])
        }
        
        if self.print_statistics:
            bt.print_statistics(results, df_trades, trade_logs)
        
        if self.plots.active:
            if self.plots.returns:
                bt.plot_returns(results, save = self.plots.save, plot = self.plots.plot)

            if self.plots.drawdown:
                bt.plot_drawdown(trade_logs, save = self.plots.save, plot = self.plots.plot)
            
            if self.plots.entry_exit.candles:
                bt.plot_entry_exit_with_candlesticks(df_trades, entry_on=self.enter_on, save = self.plots.save, plot = self.plots.plot)
            
            if self.plots.entry_exit.line:
                bt.plot_entry_exit_with_line(df_trades, entry_exit_on=self.enter_on, save = self.plots.save, plot = self.plots.plot)
            
            if self.plots.sharpe:
                bt.plot_rolling_sharpe_ratio(trade_logs, save = self.plots.save, plot = self.plots.plot)

            if self.plots.holding_duration:
                bt.plot_holding_duration(trade_logs, save = self.plots.save, plot = self.plots.plot)

            if self.plots.portfolio_value:
                bt.plot_portfolio_value(results, save = self.plots.save, plot = self.plots.plot)
        return results, statistics_dict, trade_logs

    
            
