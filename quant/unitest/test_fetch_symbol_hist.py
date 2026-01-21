import akshare as ak
stock_zh_a_hist = ak.stock_zh_a_hist(symbol="600519", period="daily", adjust="qfq")
print(stock_zh_a_hist.tail())
