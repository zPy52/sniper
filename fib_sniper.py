from os import walk
from pandas import DataFrame
from pandas_ta import rsi

def main():
    timeframe = '15m'
    crypto = 'btc'

    pandas = []
    for foldername, _, filenames in walk(f'{crypto}/unzipped-{timeframe}'):
        for filename in filenames:
            with open(foldername + '/' + filename, 'r', errors='ignore', encoding='UTF-8') as file:
                for l in file.read().splitlines():
                    pandas.append(l.split(','))

    df = DataFrame(pandas,  columns=['date',
                                    'open',
                                    'high',
                                    'low',
                                    'close',
                                    'asset volume',
                                    'kline close time',
                                    'usd volume',
                                    'number of trades',
                                    'taker buy base asset volume',
                                    'taker buy quote asset volume',
                                    'ignore'])

    def format_df(df: DataFrame) -> DataFrame:
        df = df.drop(df.columns[[6, 7, 8, 9, 10, 11]], axis=1)
        
        df['open']   = df['open'].astype(float)
        df['high']   = df['high'].astype(float)
        df['low']    = df['low'].astype(float)
        df['close']  = df['close'].astype(float)
        df['asset volume']  = df['asset volume'].astype(float)

        df['RSI'] = rsi(close=df['close'])

        return df

    df = format_df(df)

    capital = 100
    eth = 0

    eth = round(capital / df.iloc[0]['close'], 8)

    capital = round(eth * df.iloc[len(df) - 1]['close'], 2)

    print(f'--- RESULTS (RSI-FIB SNIPER: {crypto.upper()} - {timeframe}) ---')

    print(f'PROFIT (holdear): {round(((capital * 100) / 100) - 100, 2)}%')
    
    def is_buy_signal(last_sessions: DataFrame) -> float:
        ## First part ##
        
        # Calculate the highest high in the last 16 candles.
        highs = {last_sessions.iloc[n]['high']: n for n in range(len(last_sessions))}
        
        # Get the highest high.
        highest_high = max(highs.keys())

        # Get the highest high's index.
        highest_high_index = highs[highest_high]

        #  Create a dictionary that will hold all the green
        # candles of the impulse.
        lows = {}

        # Iterate over candles and get the greens of the impulse.
        for n in range(highest_high_index - 1, -1, -1):
            candle = last_sessions.iloc[n]

            # If it's a red candle stop the recoil.
            if candle['close'] < candle['open']:
                break
            
            # Otherwise, add the candle's index to the list.
            lows[candle['low']] = n 

        # If there is not enough size on the impulse, don't continue.
        if len(lows) < 5:
            return -1

        # Get the lowest low in the impulse.
        lowest_low = last_sessions.iloc[lows[min(lows.keys())]]['low']

        # Get number of green candles in the impulse.
        impulse_length = len(lows) - list(lows.keys()).index(lowest_low)

        # Get the growth/time relation.
        relation = (highest_high / lowest_low) / (impulse_length + 1)

        ### HANDSHAKING TEST ###
        if relation < 0.25:
            return -1.0

        ## Second part ##
        
        #  Get the RSI of the candle with the lowest low in the impulse 
        # and the last candle of the list.
        rsi_start = last_sessions.iloc[lows[min(lows.keys())]]['RSI']
        rsi_end = last_sessions.iloc[-1]['RSI']

        # 61.8% level of retracement.
        golden_cross = highest_high - (highest_high - lowest_low) * 0.618

        # If conditions are met, then it returns the take_profit. Otherwise, it returns -1.0.
        if last_sessions.iloc[-1]['low'] <= golden_cross and rsi_start - rsi_end >= 15:
            return highest_high - (highest_high - lowest_low) * (0.236 ) 
        else:
            return -1.0
    


    check(df, is_buy_signal, timeframe)
            

def check(df, is_buy_signal, timeframe):
    size = len(df)

    print('Size:', size)

    asset = 0
    initial_investment = 100
    capital = initial_investment

    broker_commision = 0.1 / 100

    orders = 0

    last_investment = 0

    minutes = []

    elapse = -1

    wins = 0

    average_gain = []
    
    average_loss = []

    history = []

    diffs = []

    take_profit, stop_loss = 0, 0

    for i in range(16 * 2 - 1, size):
        if elapse >= 0:
            elapse += 1
        
        now = df.iloc[i]
        last_sessions = df.iloc[i-16:i]

        potential_take_profit = is_buy_signal(last_sessions)

        if capital > 0 and potential_take_profit > 0:
            last_investment = capital
            capital *= 1 - broker_commision

            asset = round(capital / now['open'], 8)
            capital = 0

            take_profit, stop_loss = potential_take_profit, now['open'] - (potential_take_profit - now['open']) * 0.8

            orders += 1

            elapse = 0
        elif asset > 0 and (take_profit <= now['high'] or stop_loss >= now['low']):
            asset *= 1 - broker_commision

            price = take_profit if take_profit <= now['high'] else stop_loss

            capital = round(asset * price, 2)
            asset = 0

            diff = (capital / last_investment) - 1

            diffs.append(diff)

            if last_investment < capital:
                wins += 1
                average_gain.append(diff)
            else:
                average_loss.append(diff)

            last_investment = 0

            minutes.append(elapse)

            elapse = -1

            take_profit, stop_loss = 0, 0

        #"""
        if capital > 0:
            history.append(capital)
        elif capital == 0:
            history.append(round(now['close'] * asset, 2))
        else: 
            history.append(round(capital + (now['close'] * asset), 2))
        #"""

    if asset > 0:
        capital = round(asset * df.iloc[-1]['close'], 2)
        asset = 0

    #"""
    print(f'PROFIT (algoritmo): {"{:,}".format(round((capital * 100) / initial_investment - 100, 2))}%')
    
    print('--- STATISTICS ---')
    try:
        print(f'Number of operations: {orders}')
        print(f'Winrate: {round((100 * wins) / orders, 2)}%')

        average_hours = ((sum(minutes) / len(minutes)) * int(timeframe[:-1])) / 60
        print('Average hours that an operation is alive:', round(average_hours, 2))
        print(f'Percentage of the time it is in: {round((100 * average_hours * orders) / (24 * 365), 2)}%')
        
        print(f'Average gain per successful operation: {round((100 * sum(average_gain)) / len(average_gain), 2)}%')
        print(f'Average loss per unfruitful operation: {round((100 * sum(average_loss)) / len(average_loss), 2)}%')

        print('Gain-loss ratio:',
            f'{round(abs((sum(average_gain) / len(average_gain)) / (sum(average_loss) / len(average_loss))), 2)}')
    except ZeroDivisionError:
        print('ZeroDivisionError')
    #"""

    return history


main()