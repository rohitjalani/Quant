class StopLoss:
    '''
    This class implements the stop loss functionality. 
    It takes the trades dataframe as input and returns the same dataframe with the stop loss applied.
    It implements 2 types of stop loss:
    1. Simple stop loss: This is a simple stop which calculates the stop loss with respect to the price at which the trade is entered.
    2. Trailing stop loss: This is a trailing stop loss which calculates the stop loss with respect to the highest price reached after the trade is entered.
    '''
    def __init__(self, config):
        self.config = config

    def run(self, trades):
        '''
        This function implements the stop loss functionality.
        This is implemented using a for loop which iterates over the rows of the dataframe.
        The stop loss is applied only if the global stop loss is active.

        1. If the global stop loss is active then we check the type and limit of stop loss and apply the stop loss accordingly.
        2. If the type of stop loss is simple, then we calculate the stop loss using the price at which the trade is entered.
        3. If the type of stop loss is trailing, then we keep track of the highest price reached after the trade is entered and calculate the stop loss using that price.
        4. If the type of stop loss is None, then we don't apply any stop loss.
        5. If the global stop loss is not active, then we don't apply any stop loss.
        6. If the retrade option is active, then we check if the retrade frequency is 3m or 1d and apply the retrade accordingly.
        7. If the retrade option is not active, then we don't apply any retrade.
        8. If the config option dont_take_next_cheby_trade is active, then we don't take the next cheby trade after a stop loss hit.
        '''
        df = trades.copy()

        # check whether stop loss is active from the config
        global_stop_loss = self.config.utils.stop_loss

        # check whether retrade is active from the config
        retrade_after = self.config.stop_loss.retrade_after

        enter_on = self.config.utils.trade_on
        exit_on = self.config.utils.trade_on

        # if stop loss is not active, then return the trades dataframe without any changes
        if not global_stop_loss:
            print("No global stop loss defined")
            return trades
        
        # check if all the strategies have stop loss defined
        if len(trades[trades["strategy_used"].isin(self.config.stop_loss.keys())]) != len(trades):
            raise Exception("Some strategies don't have stop loss defined")
        
        # create new columns in the trades dataframe for stop loss type, limit, retrade, retrade frequency and date
        trades["stop_loss_type"] = trades["strategy_used"].map(lambda x: self.config.stop_loss[x]["type"])
        trades["stop_loss_limit"] = trades["strategy_used"].map(lambda x: self.config.stop_loss[x]["limit"])
        trades["retrade"] = trades["strategy_used"].map(lambda x: self.config.stop_loss[x]["retrade"])
        trades["retrade_frequency"] = trades["strategy_used"].map(lambda x: self.config.stop_loss[x]["retrade_frequency"])
        df["date"] = df["datetime"].map(lambda x: x[:10])

        # variables to keep track of the current position and whether stop loss is applied
        stop_loss_applied = False
        current_position = 0

        # variables to keep track of the number of stop loss hits
        number_of_sl_hit = 0

        # variables to keep track of whether retrade is active and the counter for retrade
        retrade_active = False
        retrade_counter = retrade_after
        last_stop_loss_date = None

        # check if the config option dont_take_next_cheby_trade is active
        cond_dont_take_next_cheby_trade = self.config.utils.dont_take_next_cheby_trade

        # variables to keep track of whether to take the next cheby trade and the previous position
        take_next_cheby_trade = True
        cheby_previous_position = 0
        
        for i, row in trades.iterrows():

            # find the stop loss type, limit, retrade and retrade frequency for the current strategy
            stop_loss_limit = row["stop_loss_limit"]
            stop_loss_type = row["stop_loss_type"]
            retrade = row["retrade"]
            retrade_frequency = row["retrade_frequency"]

            # if retrade is active, then check if the retrade frequency is 3m or 1d and apply the retrade accordingly
            if retrade_active:
                if retrade_frequency == "3m":
                    retrade_counter -= 1
                elif retrade_frequency == "1d":
                    if last_stop_loss_date != df['date'].iloc[i]:
                        retrade_counter -= 1
                        last_stop_loss_date = df['date'].iloc[i]
                if retrade_counter == 0:
                    retrade_active = False

            # if the stop loss type is None, then don't apply any stop loss and continue to the next iteration
            if stop_loss_type == None:
                continue

            # if the stop loss is active and stop loss is already applied, then check if the signal for closing the trade is received
            if global_stop_loss and stop_loss_applied:
                if previous_position * df['signals'].iloc[i] == -1:
                    stop_loss_applied = False
                    df.at[i, 'signals'] = -1*current_position
                    current_position = 0
                    price_for_stop_loss = 0
                    previous_position = 0

                # if retrade is active and previous position is 1, then check if the retrade frequency is 3m or 1d and apply the retrade accordingly
                elif previous_position == 1 and retrade and retrade_counter == 0:
                    if retrade_frequency == "3m":
                        if df[enter_on].iloc[i] > last_stop_loss_price:
                            # open a long position
                            current_position = 1
                            price_for_stop_loss = df[enter_on].iloc[i]
                            stop_loss_applied = False
                            df.at[i, 'signals'] = 1
                            retrade_counter = retrade_after
                    if retrade_frequency == "1d":
                        # check if the current timestamp is the first timestamp of the day
                        if i>0 and df['date'].iloc[i] != df['date'].iloc[i-1]:
                            if df[enter_on].iloc[i] > last_stop_loss_price:
                                # open a long position
                                current_position = 1
                                price_for_stop_loss = df[enter_on].iloc[i]
                                stop_loss_applied = False
                                df.at[i, 'signals'] = 1
                                retrade_counter = retrade_after
                        
                # if retrade is active and previous position is -1, then check if the retrade frequency is 3m or 1d and apply the retrade accordingly
                elif previous_position == -1 and retrade and retrade_counter == 0:
                    if retrade_frequency == "3m":
                        if df[enter_on].iloc[i] < last_stop_loss_price:
                            # open a short position
                            current_position = -1
                            price_for_stop_loss = df[enter_on].iloc[i]
                            stop_loss_applied = False
                            df.at[i, 'signals'] = -1
                    if retrade_frequency == "1d":
                        # check if the current timestamp is the first timestamp of the day
                        if i>0 and df['date'].iloc[i] != df['date'].iloc[i-1]:
                            if df[enter_on].iloc[i] < last_stop_loss_price:
                                # open a short position
                                current_position = -1
                                price_for_stop_loss = df[enter_on].iloc[i]
                                stop_loss_applied = False
                                df.at[i, 'signals'] = -1
                continue

            # if the current position is 0, then check if the signal for opening a trade is received
            if current_position == 0:
                if df['signals'].iloc[i] == 1:
                    # if take_next_cheby_trade is False and previous cheby position is -1, then don't open a trade
                    if trades['strategy_used'].iloc[i] == "strat_cheby" and not take_next_cheby_trade and cheby_previous_position == -1:
                        take_next_cheby_trade = True
                        cheby_previous_position = 0
                        continue

                    # open a long position
                    current_position = 1
                    price_for_stop_loss = df[enter_on].iloc[i]
                    take_next_cheby_trade = True
                    cheby_previous_position = 0
                elif df['signals'].iloc[i] == -1:
                    # if take_next_cheby_trade is False and previous cheby position is 1, then don't open a trade
                    if trades['strategy_used'].iloc[i] == "strat_cheby" and not take_next_cheby_trade and cheby_previous_position == 1:
                        take_next_cheby_trade = True
                        cheby_previous_position = 0
                        continue

                    # open a short position
                    current_position = -1
                    price_for_stop_loss = df[enter_on].iloc[i]
                    take_next_cheby_trade = True
                    cheby_previous_position = 0

            # if the current position is 1, then check if the signal for closing the trade is received or if the stop loss is hit
            elif current_position == 1:

                # if the signal for closing the trade is received, then close the trade
                if df['signals'].iloc[i] == -1:
                    current_position = 0
                    stop_loss_applied = False
                    continue

                # if the type of stop loss is trailing, and the trades are entered and exited on close, then update the current maximum price
                if enter_on == 'close' and df["high"].iloc[i] > price_for_stop_loss and stop_loss_type == "trailing":
                    price_for_stop_loss = df["high"].iloc[i]

                # if the global stop loss is active and the stop loss is hit, then close the trade
                if df[exit_on].iloc[i] < price_for_stop_loss*(1-stop_loss_limit):
                    # close the trade
                    previous_position = current_position
                    current_position = 0
                    df.at[i, 'signals'] = -1
                    stop_loss_applied = True
                    # find the close of the current day for saving the stop loss price
                    index_for_daily_close = df[df["date"] == df["date"].iloc[i]].index[-1]
                    last_stop_loss_price = df[exit_on].iloc[index_for_daily_close]
                    price_for_stop_loss = 0
                    number_of_sl_hit += 1
                    retrade_active = retrade

                    # if retrade is active, then if stop loss is hit, restart the retrade counter and save the date of the stop loss hit
                    if retrade:
                        retrade_counter = retrade_after
                        last_stop_loss_date = df['date'].iloc[i]

                    # if the config option dont_take_next_cheby_trade is active, then don't take the next cheby trade after a stop loss hit
                    if trades['strategy_used'].iloc[i] == "strat_cheby" and cond_dont_take_next_cheby_trade:
                        take_next_cheby_trade = False
                        cheby_previous_position = 1

                # if the type of stop loss is trailing, and the trades are entered and exited on open, then update the current maximum price after checking if the stop loss is hit
                if enter_on == 'open' and df['high'].iloc[i] > price_for_stop_loss and stop_loss_type == "trailing":
                    price_for_stop_loss = df['high'].iloc[i]

            # if the current position is -1, then check if the signal for closing the trade is received or if the stop loss is hit
            elif current_position == -1:

                # if the signal for closing the trade is received, then close the trade
                if df['signals'].iloc[i] == 1:
                    current_position = 0
                    if global_stop_loss:
                        stop_loss_applied = False
                    continue

                # if the type of stop loss is trailing, and the trades are entered and exited on close, then update the current minimum price
                if enter_on == 'close' and df[exit_on].iloc[i] < price_for_stop_loss and stop_loss_type == "trailing":
                    price_for_stop_loss = df["low"].iloc[i]

                # if the global stop loss is active and the stop loss is hit, then close the trade
                if global_stop_loss and df[exit_on].iloc[i] > price_for_stop_loss*(1+stop_loss_limit):
                    # close the trade
                    previous_position = current_position
                    current_position = 0
                    df.at[i, 'signals'] = 1
                    stop_loss_applied = True
                    # find the close of the current day for saving the stop loss price
                    index_for_daily_close = df[df["date"] == df["date"].iloc[i]].index[-1]
                    last_stop_loss_price = df[exit_on].iloc[index_for_daily_close]
                    price_for_stop_loss = 0
                    number_of_sl_hit += 1
                    retrade_active = retrade

                    # if retrade is active, then if stop loss is hit, restart the retrade counter and save the date of the stop loss hit
                    if retrade:
                        retrade_counter = retrade_after
                        last_stop_loss_date = df['date'].iloc[i]
                    # check if this trade was a cheby trade and if the config option dont_take_next_cheby_trade is active, then don't take the next cheby trade after a stop loss hit
                    if trades['strategy_used'].iloc[i] == "strat_cheby" and cond_dont_take_next_cheby_trade:
                        take_next_cheby_trade = False
                        cheby_previous_position = -1

                # if the type of stop loss is trailing, and the trades are entered and exited on open, then update the current minimum price after checking if the stop loss is hit
                if enter_on == 'open' and df['low'].iloc[i] < price_for_stop_loss and stop_loss_type == "trailing":
                    price_for_stop_loss = df['low'].iloc[i]

        if "strategy_used" not in df.columns:
            df['strategy_used'] = trades['strategy_used']
        return df


class TakeProfit:
    '''
    This class implements the take profit functionality.
    It takes the trades dataframe as input and returns the same dataframe with the take profit applied.
    '''

    def __init__(self, config):
        self.config = config

    def run(self, trades):
        '''
        This function implements the take profit functionality.
        It is implemented using a for loop which iterates over the rows of the dataframe.
        The take profit is applied only if the global take profit is active.

        1. If the global take profit is active then we check whether is it active for the current strategy and limit of take profit and apply the take profit accordingly.
        2. If the take profit is active, then we check if the signal for closing the trade is received or if the take profit is hit.
        3. If the signal for closing the trade is received, then close the trade.
        4. If the take profit is hit, then close the trade.
        '''
        df = trades.copy()

        # check whether take profit is active from the config
        global_take_profit = self.config.utils.take_profit


        enter_on = self.config.utils.trade_on
        exit_on = self.config.utils.trade_on

        # if take profit is not active, then return the trades dataframe without any changes
        if not global_take_profit:
            print("No global take profit defined")
            if "strategy_used" in trades.columns:
                trades.drop(['strategy_used'], axis=1, inplace=True)
            return trades
        
        # check if all the strategies have take profit defined
        if len(trades[trades["strategy_used"].isin(self.config.take_profit.keys())]) != len(trades):
            raise Exception("Some strategies don't have take profit defined")
        
        # create new columns in the trades dataframe for take profit active, limit
        trades["take_profit_active"] = trades["strategy_used"].map(lambda x: self.config.take_profit[x]["active"])
        trades["take_profit_limit"] = trades["strategy_used"].map(lambda x: self.config.take_profit[x]["limit"])

        # create a new column in the trades dataframe for date
        df["date"] = df["datetime"].map(lambda x: x[:10])

        # variables to keep track of the current position and whether take profit is applied
        take_profit_applied = False
        current_position = 0

        # variables to keep track of the number of take profit hits
        number_of_tp_hit = 0

        for i, row in trades.iterrows():

            # find the take profit limit and whether take profit is active for the current strategy
            take_profit_limit = row["take_profit_limit"]
            take_profit_active = row["take_profit_active"]

            # if take profit is active and take profit is already applied, then check if the signal for closing the trade is received
            if take_profit_active and take_profit_applied:
                if previous_position * df['signals'].iloc[i] == -1:
                    take_profit_applied = False
                    df.at[i, 'signals'] = -1*current_position
                    current_position = 0
                    price_for_take_profit = 0
                    previous_position = 0
                continue

            # if the current position is 0, then check if the signal for opening a trade is received
            elif current_position == 0:
                if df['signals'].iloc[i] == 1:
                    current_position = 1
                    price_for_take_profit = df[enter_on].iloc[i]

                elif df['signals'].iloc[i] == -1:
                    current_position = -1
                    price_for_take_profit = df[enter_on].iloc[i]

            # if the current position is 1, then check if the signal for closing the trade is received or if the take profit is hit
            elif current_position == 1:

                # if the signal for closing the trade is received, then close the trade
                if df['signals'].iloc[i] == -1:
                    current_position = 0
                    take_profit_applied = False

                # if the global take profit is active and the take profit is hit, then close the trade
                elif take_profit_active and df[exit_on].iloc[i] > price_for_take_profit*(1+take_profit_limit):
                    # close the trade
                    previous_position = current_position
                    current_position = 0
                    df.at[i, 'signals'] = -1
                    take_profit_applied = True
                    price_for_take_profit = 0
                    number_of_tp_hit += 1

            # if the current position is -1, then check if the signal for closing the trade is received or if the take profit is hit
            elif current_position == -1:

                # if the signal for closing the trade is received, then close the trade
                if df['signals'].iloc[i] == 1:
                    current_position = 0
                    take_profit_applied = False

                # if the global take profit is active and the take profit is hit, then close the trade
                elif take_profit_active and global_take_profit and df[exit_on].iloc[i] < price_for_take_profit*(1-take_profit_limit):
                    # close the trade
                    previous_position = current_position
                    current_position = 0
                    df.at[i, 'signals'] = 1
                    take_profit_applied = True
                    price_for_take_profit = 0
                    number_of_tp_hit += 1
        return df

class TPSL:
    def __new__(cls, config):

        if not hasattr(cls, 'instance'):
            cls.instance = super(TPSL, cls).__new__(cls)
            cls.instance.config = config

        return cls.instance
    
    def __init__(self, config):
        self.config = config
        self.stoploss = StopLoss(config)
        self.takeprofit = TakeProfit(config)

    def run(self, trades):
        trades = self.stoploss.run(trades)
        trades = self.takeprofit.run(trades)
        trades = trades[['datetime', 'signals', 'open', 'high', 'low', 'close', 'volume']]

        return trades


