import os
import numpy as np
import pandas as pd
from pylab import mpl, plt
from alpaca.trading.client import TradingClient
from alpaca.data.historical import CryptoHistoricalDataClient
from alpaca.data.requests import CryptoBarsRequest
from alpaca.data.timeframe import TimeFrame
from alpaca.data.live import CryptoDataStream

# Define your API keys directly at the top
API_KEY = 'your_api_key_here'
SECRET_KEY = 'your_secret_key_here'

# Initialize the TradingClient with your API keys
trading_client = TradingClient(API_KEY, SECRET_KEY)

# Initialize the CryptoDataStream with your API keys
crypto_stream = CryptoDataStream(API_KEY, SECRET_KEY)

# Initialize the CryptoHistoricalDataClient
client = CryptoHistoricalDataClient()

# Get account information
try:
    account = trading_client.get_account()
except Exception as e:
    print(f'Error fetching account information: {e}')
    account = None

if account:
    # Check if the account is restricted from trading
    if account.trading_blocked:
        print('Account is currently restricted from trading.')

    # Check how much money is available for opening new positions
    print(f'${account.buying_power} is available as buying power.')

# Define request parameters for fetching historical data
request_params = CryptoBarsRequest(
    symbol_or_symbols=["BTC/USD"],
    timeframe=TimeFrame.Minute,
)

# Fetch historical data and convert to DataFrame
try:
    CryptoBarData = client.get_crypto_bars(request_params)
    data = CryptoBarData.df
except Exception as e:
    print(f'Error fetching historical data: {e}')
    data = pd.DataFrame()

if not data.empty:
    # Convert the index to datetime
    data.index = pd.to_datetime(data.index.get_level_values('timestamp'))

    # Calculate 42-period Simple Moving Average (SMA1)
    data['SMA1'] = data['close'].rolling(42).mean()

    # Calculate 252-period Simple Moving Average (SMA2)
    data['SMA2'] = data['close'].rolling(252).mean()

    # Determine market position based on SMA crossover
    data['position'] = np.where(data['SMA1'] > data['SMA2'], 1, -1)

    # Remove rows with NaN values (resulting from rolling mean calculations)
    data.dropna(inplace=True)

    # Print the cleaned DataFrame
    print(data)

    # Backtest the strategy
    def backtest(data, initial_capital=10000):
        capital = initial_capital
        position = 0
        trades = []

        for i in range(1, len(data)):
            if data['SMA1'].iloc[i] > data['SMA2'].iloc[i] and position == 0:
                # Enter a trade (buy)
                position = capital / data['close'].iloc[i]
                capital = 0
                trades.append((data.index[i], 'buy', data['close'].iloc[i]))
                print(f'Buy at {data.index[i]}: {data["close"].iloc[i]:.2f}')
            elif data['SMA1'].iloc[i] < data['SMA2'].iloc[i] and position > 0:
                # Exit a trade (sell)
                capital = position * data['close'].iloc[i]
                position = 0
                trades.append((data.index[i], 'sell', data['close'].iloc[i]))
                print(f'Sell at {data.index[i]}: {data["close"].iloc[i]:.2f}')

        # Calculate final portfolio value
        final_value = capital + position * data['close'].iloc[-1] if position > 0 else capital

        # Calculate return
        total_return = (final_value - initial_capital) / initial_capital * 100

        return total_return, trades

    # Perform backtest and print results
    total_return, trades = backtest(data)
    print(f'Total Return: {total_return:.2f}%')

    # Create the subplots
    plt.figure(figsize=(14, 14))

    # First subplot: Position indicator
    plt.subplot(2, 1, 1)
    data['position'].plot(title='Market Positioning Based on Dual 42/252 SMA (1m bars)')
    plt.xlabel('Date')
    plt.ylabel('Position')

    # Second subplot: Price and trades
    plt.subplot(2, 1, 2)
    plt.plot(data.index, data['close'], label='Price')
    plt.plot(data.index, data['SMA1'], label='42-period SMA')
    plt.plot(data.index, data['SMA2'], label='252-period SMA')
    for trade in trades:
        plt.scatter(trade[0], trade[2], marker='^' if trade[1] == 'buy' else 'v', color='g' if trade[1] == 'buy' else 'r')
    plt.title('SMA Crossover Strategy Backtest')
    plt.xlabel('Date')
    plt.ylabel('Price')
    plt.legend()

    # Show the plots
    plt.tight_layout()
    plt.show()
