import json
import yfinance as yf

# 从配置文件加载投资组合配置
def load_portfolio_config(file_path):
    with open(file_path, 'r') as file:
        return json.load(file)

# 获取当前的资产价格
def get_asset_price(symbol):
    print(f"[DEBUG] 正在下载 {symbol} 的数据...")
    data = yf.download(symbol, period='1d', interval='1d')
    
    # 打印下载的数据以调试
    print(f"[DEBUG] 下载的 {symbol} 数据: \n{data.head()}")  # 查看下载的数据，确保获取正确的列
    
    # 获取最新价格
    price = data['Adj Close'].iloc[-1].item()  # 使用 .item() 获取单一值
    print(f"[DEBUG] {symbol} 最新价格: {price}")  # 确保输出的是单一的价格
    
    return price

# 计算每个资产需要购买的股数
def calculate_shares_to_buy(assets, total_investment):
    investment = {asset: total_investment * ratio for asset, ratio in assets.items()}  # 计算每个资产的投资金额
    shares_to_buy = {}

    # 计算每个资产的购买数量（股数或份额）
    for asset, amount in investment.items():
        price = get_asset_price(asset)  # 获取单一价格
        shares = amount / price  # 每个资产需要购买的份额数
        shares_to_buy[asset] = {
            'investment': amount,
            'price': price,
            'shares': shares
        }
    
    return shares_to_buy

# 打印每个资产购买的数量
def print_purchase_details(shares_to_buy):
    for asset, data in shares_to_buy.items():
        print(f"资产: {asset}")
        print(f"投资金额: ${data['investment']:.2f}")
        print(f"当前价格: ${data['price']:.2f}")  # 格式化价格，确保 'price' 是单一数值
        print(f"需要购买的数量: {data['shares']:.2f} 份")
        print("-" * 40)

# 主程序
def main():
    # 从 config.json 文件加载配置
    portfolio_config = load_portfolio_config('config.json')

    # 从配置中获取投资比例和总定投金额
    assets = portfolio_config["assets"]
    total_investment = portfolio_config["total_investment"]

    # 计算每个资产需要购买的股数
    shares_to_buy = calculate_shares_to_buy(assets, total_investment)

    # 输出购买详情
    print_purchase_details(shares_to_buy)

if __name__ == "__main__":
    main()
