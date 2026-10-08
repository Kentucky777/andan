import yfinance as yf
import apimoex
import requests
import pandas as pd
from datetime import datetime, timedelta

# ====== Настройка периода ======
end_date = datetime.today()
start_date = end_date - timedelta(days=400)

# ====== 1. yfinance: акции США ======
us_tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]

us_data = yf.download(
    tickers=us_tickers,
    start=start_date.strftime("%Y-%m-%d"),
    end=end_date.strftime("%Y-%m-%d"),
    interval="1d",
    group_by="ticker",
    auto_adjust=True,
    threads=True
)

# оставляем только High, Low, Volume для каждого тикера
us_data_short = us_data.loc[:, (slice(None), ["High", "Low", "Volume"])]

print("=== US акции (High, Low, Volume) ===")
print(us_data_short.tail())

# ====== 2. apimoex: акции MOEX ======
moex_tickers = ["SBER", "GAZP", "LKOH", "GMKN", "ROSN"]

moex_data = {}
with requests.Session() as session:
    for ticker in moex_tickers:
        data = apimoex.get_board_history(
            session,
            security=ticker,
            start=start_date.strftime("%Y-%m-%d"),
            end=end_date.strftime("%Y-%m-%d"),
            board="TQBR"
        )
        df = pd.DataFrame(data)
        df.set_index("TRADEDATE", inplace=True)
        moex_data[ticker] = df

print("\n=== MOEX акции (Low, Volume")
for ticker, df in moex_data.items():
    print(f"\n--- {ticker} ---")
    print(df[["CLOSE", "VOLUME"]].tail())