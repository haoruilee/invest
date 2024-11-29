import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# Define debug log function
def debug_log(message):
    print(f"[DEBUG] {message}")

# Download data
symbols = ['^GSPC', '^DJI', 'QQQ', 'BTC-USD',  'GLD', 'TLT', '000001.SS', 'SPY', 'VTI', 'VNQ', 'DBC', 'XLY']  # Add selected assets
prices = {}

debug_log("Starting to download data...")
for symbol in symbols:
    debug_log(f"Downloading data for {symbol}...")
    data = yf.download(symbol, start='2007-01-01', end='2024-10-31')
    prices[symbol] = data['Adj Close']  # Only take adjusted close prices
    debug_log(f"{symbol} data download complete, length of data: {len(data)}")

# Get the last trading day of each month
last_trading_days = prices['^GSPC'].resample('M').last().index  # Get the last trading day of each month

# Initialize the DataFrame for monthly closing prices
monthly_investment_df = pd.DataFrame(index=last_trading_days)

debug_log("Starting to calculate the last trading day close prices for each month...")
for symbol in symbols:
    try:
        debug_log(f"Calculating the monthly last trading day close price for {symbol}...")
        monthly_close = prices[symbol].resample('M').last()
        monthly_investment_df[symbol + ' Monthly Close'] = monthly_close
        debug_log(f"{symbol} monthly last trading day close price calculation complete, first 5 rows:\n{monthly_close.head()}")
    except Exception as e:
        debug_log(f"Error processing {symbol}: {e}")

# Calculate portfolio value
investment_ratios = {
    '^GSPC': 0.10,    # S&P 500
    '^DJI': 0.10,     # Dow Jones
    'QQQ': 0.10,      # Nasdaq 100
    'BTC-USD': 0.05,  # Bitcoin
    'GLD': 0.05,      # Gold
    'TLT': 0.05,      # US Long-Term Treasuries
    '000001.SS': 0.10, # Shanghai Composite Index
    'SPY': 0.10,      # SPDR S&P 500 ETF
    'VTI': 0.05,      # Vanguard Total Stock Market ETF
    'VNQ': 0.10,      # Vanguard Real Estate ETF
    'DBC': 0.05,      # Invesco DB Commodity Index Tracking Fund (Commodities)
    'XLY': 0.05,      # Consumer discretionary sector (used as a representative for tech and consumer goods ETFs)
}

debug_log("Starting to calculate portfolio value...")

# Set initial capital
portfolio_value = pd.Series(index=last_trading_days, dtype=np.float64)
portfolio_value.iloc[0] = 1  # Initial investment is 1 (can be replaced with another initial amount)

# Calculate portfolio value at the last trading day of each month
for i in range(1, len(last_trading_days)):
    value = 0
    for symbol, ratio in investment_ratios.items():
        monthly_close = monthly_investment_df[symbol + ' Monthly Close'].iloc[i]
        if pd.notna(monthly_close):
            value += ratio * monthly_close
    portfolio_value.iloc[i] = value
    debug_log(f"Portfolio value on {last_trading_days[i]}: {portfolio_value.iloc[i]}")

# Plot and save the portfolio value graph
debug_log("Plotting portfolio value graph...")
plt.figure(figsize=(10, 6))
portfolio_value.plot()
plt.title('Portfolio Value (Last Trading Day of Each Month)')
plt.xlabel('Date')
plt.ylabel('Portfolio Value')
plt.grid(True)
plt.savefig('portfolio_value.png')
debug_log("Portfolio value graph saved as 'portfolio_value.png'")

# Calculate performance metrics
debug_log("Calculating performance metrics...")

# Total return
total_return = (portfolio_value[-1] / portfolio_value[0]) - 1

# Annualized return
annualized_return = (1 + total_return) ** (1 / len(portfolio_value)) - 1

# Maximum drawdown
drawdown = portfolio_value / portfolio_value.cummax() - 1
max_drawdown = drawdown.min()

# Sharpe ratio calculation
risk_free_rate = 0.03  # Assume the risk-free rate is 0.03
daily_returns = portfolio_value.pct_change().dropna()  # Daily returns
annualized_volatility = daily_returns.std() * np.sqrt(252)  # Annualized volatility
sharpe_ratio = (annualized_return - risk_free_rate) / annualized_volatility  # Sharpe ratio

# Find the start and end dates of the maximum drawdown
drawdown_start = drawdown.idxmax()  # Start date of the maximum drawdown
# Calculate drawdown recovery time
drawdown_end = drawdown.idxmin()  # End date of the maximum drawdown
# Find the highest point before the maximum drawdown
pre_drawdown_peak = portfolio_value[:drawdown_end].max()
# Find when the portfolio value recovered to the previous peak after the drawdown
recovery_start = portfolio_value[drawdown_end:].loc[portfolio_value[drawdown_end:] >= pre_drawdown_peak].index[0]

# Calculate recovery time
drawdown_recovery_time = recovery_start - drawdown_end  # Recovery time

debug_log(f"Total return: {total_return:.2%}")
debug_log(f"Annualized return: {annualized_return:.2%}")
debug_log(f"Maximum drawdown: {max_drawdown:.2%}")
debug_log(f"Sharpe ratio: {sharpe_ratio:.2f}")
debug_log(f"Drawdown recovery time: {drawdown_recovery_time.days} days")

# Output the specific dates for the maximum drawdown
debug_log(f"Maximum drawdown start date: {drawdown_start}")
debug_log(f"Maximum drawdown end date: {drawdown_end}")
debug_log(f"Recovery start date: {recovery_start}")
