import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import json
from numpy_financial import irr
import re
# Load portfolio configuration from JSON file
with open('config.json', 'r') as file:
    portfolio_config = json.load(file)

# Define debug log function
def debug_log(message):
    print(f"[DEBUG] {message}")


# Download data
def download_data(symbols, start_date, end_date):
    prices = {}
    for symbol in symbols:
        data = yf.download(symbol, start=start_date, end=end_date)
        prices[symbol] = data['Adj Close']
        
        # 打印每个资产的最早交易日期
        earliest_date = data.index.min()
        debug_log(f"Asset: {symbol} - Earliest Trading Date: {earliest_date}")
    
    return prices


# 计算总投入和总回报
def calculate_total_investment_and_return(portfolio_value, monthly_investment):
    # 计算投资的月份数
    investment_months = len(portfolio_value)
    
    # 总投入 = 每月投资额 * 投资的月份数
    total_investment = monthly_investment * investment_months
    
    # 总回报 = 最终组合的价值 - 总投入
    total_value = portfolio_value.iloc[-1]  # 最终组合的资产总值
    total_return = total_value - total_investment  # 总回报
    
    return total_investment, total_return

# Calculate money-weighted return (MWR)
def calculate_money_weighted_return(portfolio_value, investment_amounts, investment_dates):
    cash_flows = [-amount for amount in investment_amounts]  # Cash flows are negative for investments
    cash_flows.append(portfolio_value[-1])  # Final cash flow is the portfolio value
    # 将最后一个日期转换为 DatetimeIndex，然后追加
    cash_flow_dates = investment_dates.append(pd.to_datetime([portfolio_value.index[-1]]))  # 使用列表包裹最后一个日期

    return irr(cash_flows)

# Calculate time-weighted return (TWR)
def calculate_time_weighted_return(portfolio_value):
    time_weighted_return = 1.0
    for i in range(1, len(portfolio_value)):
        period_return = portfolio_value.iloc[i] / portfolio_value.iloc[i-1] - 1
        time_weighted_return *= (1 + period_return)
    return time_weighted_return - 1

# Calculate monthly close
def calculate_monthly_close(prices, symbols):
    last_trading_days = prices[symbols[0]].resample('M').last().index
    monthly_investment_df = pd.DataFrame(index=last_trading_days)
    for symbol in symbols:
        monthly_close = prices[symbol].resample('M').last()
        monthly_investment_df[symbol + ' Monthly Close'] = monthly_close
    return monthly_investment_df

# Calculate portfolio value with monthly investment
def calculate_portfolio_value_with_monthly_investment(monthly_investment_df, investment_ratios, last_trading_days, monthly_investment):
    portfolio_value = pd.Series(index=last_trading_days, dtype=np.float64)
    portfolio_value.iloc[0] = 1  # Initial investment is 1 (can be replaced with another initial amount)
    
    # Track the holdings of each asset
    holdings = {symbol: 0 for symbol in investment_ratios}

    for i in range(1, len(last_trading_days)):
        # Monthly investment contribution
        monthly_contribution = monthly_investment
        
        # Distribute the monthly investment according to the asset ratios
        for symbol, ratio in investment_ratios.items():
            monthly_close = monthly_investment_df[symbol + ' Monthly Close'].iloc[i]
            if pd.notna(monthly_close):
                contribution = monthly_contribution * ratio  # Amount to invest in this asset
                holdings[symbol] += contribution / monthly_close  # Update the holdings

        # Calculate total portfolio value
        total_value = sum(holdings[symbol] * monthly_investment_df[symbol + ' Monthly Close'].iloc[i] for symbol in investment_ratios)
        portfolio_value.iloc[i] = total_value

    return portfolio_value, holdings  # Return portfolio value and holdings
    


# Performance metrics calculations
def calculate_performance_metrics(portfolio_value, risk_free_rate):
    debug_log(f"Risk-Free Rate: {risk_free_rate * 100}%")
    total_return = (portfolio_value[-1] / portfolio_value[0]) - 1
    annualized_return = (1 + total_return) ** (1 / len(portfolio_value)) - 1
    drawdown = portfolio_value / portfolio_value.cummax() - 1
    max_drawdown = drawdown.min()

    daily_returns = portfolio_value.pct_change().dropna()
    annualized_volatility = daily_returns.std() * np.sqrt(252)
    debug_log(f"Annualized volatility: {annualized_volatility}")
    debug_log(f"annualized return: {annualized_return}")
    debug_log(f"risk_free_rate: {risk_free_rate}")
    sharpe_ratio = (annualized_return - risk_free_rate) / annualized_volatility

    drawdown_start = drawdown.idxmax()
    drawdown_end = drawdown.idxmin()
    pre_drawdown_peak = portfolio_value[:drawdown_end].max()
    recovery_candidates = portfolio_value[drawdown_end:][portfolio_value[drawdown_end:] >= pre_drawdown_peak]
    if not recovery_candidates.empty:
        recovery_start = recovery_candidates.index[0]
    else:
        # 处理没有恢复的情况，例如设为NaT
        recovery_start = pd.NaT

    drawdown_recovery_time = recovery_start - drawdown_end

    debug_log(f"Total return: {total_return:.2%}")
    debug_log(f"Annualized return: {annualized_return:.2%}")
    debug_log(f"Maximum drawdown: {max_drawdown:.2%}")
    debug_log(f"Sharpe ratio: {sharpe_ratio:.2f}")
    debug_log(f"Drawdown recovery time: {drawdown_recovery_time.days} days")
    debug_log(f"Maximum drawdown start date: {drawdown_start}")
    debug_log(f"Maximum drawdown end date: {drawdown_end}")
    debug_log(f"Recovery start date: {recovery_start}")

    return total_return, annualized_return, max_drawdown, sharpe_ratio, drawdown_recovery_time


def generate_safe_filename(config):
    assets_str = '_'.join(config['assets'].keys())  # Join asset symbols with '_'
    risk_free_str = f"rf{int(config['risk_free_rate'] * 100)}"  # Risk-free rate as percentage
    # Create a filename string with assets and risk-free rate
    filename = f"portfolio_{assets_str}_{risk_free_str}.png"
    # Sanitize the filename to remove any invalid characters for OS
    safe_filename = re.sub(r'[\\/*?:"<>|]', '_', filename)
    return safe_filename

# Use the function to generate a filename
plot_filename = generate_safe_filename(portfolio_config)

# Main execution
symbols = list(portfolio_config['assets'].keys())
prices = download_data(symbols, portfolio_config['start_date'], portfolio_config['end_date'])
monthly_investment_df = calculate_monthly_close(prices, symbols)

# Calculate portfolio value with monthly investment
portfolio_value, holdings = calculate_portfolio_value_with_monthly_investment(
    monthly_investment_df, 
    portfolio_config['assets'], 
    monthly_investment_df.index, 
    portfolio_config['total_investment']  # Monthly investment from config file
)

# Calculate total investment and return
total_investment, total_return = calculate_total_investment_and_return(portfolio_value, portfolio_config['total_investment'])
debug_log(f"Total Investment: ${total_investment:.2f}")
debug_log(f"Total Return: ${total_return:.2f}")

# Calculate money-weighted return (MWR)
investment_amounts = [portfolio_config['total_investment'] * ratio for ratio in portfolio_config['assets'].values()]
investment_dates = monthly_investment_df.index
mwr = calculate_money_weighted_return(portfolio_value, investment_amounts, investment_dates)
debug_log(f"Money-Weighted Return (MWR): {mwr:.2%}")

# Calculate time-weighted return (TWR)
twr = calculate_time_weighted_return(portfolio_value)
debug_log(f"Time-Weighted Return (TWR): {twr:.2%}")

# Calculate Sharpe Ratio
sharpe_ratio = calculate_performance_metrics(portfolio_value, portfolio_config['risk_free_rate'])[3]
debug_log(f"Sharpe Ratio: {sharpe_ratio:.2f}")

# Output final holdings (shares)
debug_log("Final Asset Holdings (Shares):")
for symbol, shares in holdings.items():
    debug_log(f"Asset: {symbol} - Shares: {shares:.2f}")

# Plotting and saving the portfolio value
plt.figure(figsize=(10, 6))
portfolio_value.plot()
plt.title('Portfolio Value (Last Trading Day of Each Month)')
plt.xlabel('Date')
plt.ylabel('Portfolio Value')
plt.grid(True)

# Config text content
# Config text content (continued)
config_text = f"""
Assets:
{json.dumps(portfolio_config['assets'], indent=2)}

Start Date: {portfolio_config['start_date']}
End Date: {portfolio_config['end_date']}
Risk-Free Rate: {portfolio_config['risk_free_rate']*100}%

Total Investment: ${total_investment:.2f}
Total Return: ${total_return:.2f}

Money-Weighted Return (MWR): {mwr:.2%}
Time-Weighted Return (TWR): {twr:.2%}
Sharpe Ratio: {sharpe_ratio:.2f}
"""

# Adding config text to the chart
plt.text(0.02, 0.02, config_text, ha='left', va='bottom', fontsize=10, transform=plt.gca().transAxes, 
         bbox=dict(facecolor='white', alpha=0.7, edgecolor='black', boxstyle='round,pad=0.5'))

# Save the plot
plt.savefig(plot_filename)
debug_log("Portfolio value graph with configuration saved as 'portfolio_value_with_config.png'")

# Display the plot
plt.show()

# Saving final report to a file
with open('final_report.txt', 'w') as report_file:
    report_file.write("Final Portfolio Report\n")
    report_file.write("=====================\n\n")
    report_file.write(f"Start Date: {portfolio_config['start_date']}\n")
    report_file.write(f"End Date: {portfolio_config['end_date']}\n")
    report_file.write(f"Risk-Free Rate: {portfolio_config['risk_free_rate']*100}%\n\n")
    report_file.write(f"Total Investment: ${total_investment:.2f}\n")
    report_file.write(f"Total Return: ${total_return:.2f}\n")
    report_file.write(f"Money-Weighted Return (MWR): {mwr:.2%}\n")
    report_file.write(f"Time-Weighted Return (TWR): {twr:.2%}\n")
    report_file.write(f"Sharpe Ratio: {sharpe_ratio:.2f}\n\n")
    report_file.write("Final Asset Holdings (Shares):\n")
    for symbol, shares in holdings.items():
        report_file.write(f"{symbol}: {shares:.2f} shares\n")

debug_log("Final report saved as 'final_report.txt'")
