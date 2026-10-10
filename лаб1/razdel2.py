"""
Раздел 2. Свечные графики.
По выгруженным данным строятся свечные биржевые графики средствами Matplotlib (mplfinance).
Вывод разделён на два окна:
- Окно 1: Три таймфрейма вместе (1D, 1W, 1M) в одном окне
- Окно 2: Отдельное окно с комбинированным графиком: свечи + объём торгов (Volume) + SMA-20
"""

import sys
import logging
import warnings
from datetime import datetime, timedelta
import pandas as pd

# Отключаем системный спам логов шрифтов findfont от Matplotlib
warnings.filterwarnings("ignore")
logging.getLogger("matplotlib").setLevel(logging.ERROR)
logging.getLogger("matplotlib.font_manager").setLevel(logging.ERROR)

import matplotlib.pyplot as plt
import mplfinance as mpf
import yfinance as yf

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def fetch_stock_data(ticker: str = "MSFT", days: int = 400) -> pd.DataFrame:
    """Выгрузка котировок акции через yfinance."""
    end_date = datetime.today()
    start_date = end_date - timedelta(days=days)

    print(f"[i] Загрузка котировок {ticker} за период {start_date.strftime('%Y-%m-%d')} - {end_date.strftime('%Y-%m-%d')}...")
    df = yf.download(
        tickers=ticker,
        start=start_date.strftime("%Y-%m-%d"),
        end=end_date.strftime("%Y-%m-%d"),
        interval="1d",
        auto_adjust=True,
        progress=False
    )
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    df = df[["Open", "High", "Low", "Close", "Volume"]].dropna()
    df.index = pd.to_datetime(df.index)
    return df


def resample_ohlcv(df: pd.DataFrame, rule: str) -> pd.DataFrame:
    """
    Агрегация (ресемплинг) дневных свечей в заданный таймфрейм:
    - Open: цена открытия первого дня (first)
    - High: максимальная цена за период (max)
    - Low: минимальная цена за период (min)
    - Close: цена закрытия последнего дня (last)
    - Volume: суммарный объем за период (sum)
    """
    agg_rules = {
        "Open": "first",
        "High": "max",
        "Low": "min",
        "Close": "last",
        "Volume": "sum"
    }
    resampled = df.resample(rule).agg(agg_rules).dropna()
    return resampled


def plot_three_timeframes_window(df_daily: pd.DataFrame, df_weekly: pd.DataFrame, df_monthly: pd.DataFrame, ticker: str = "MSFT"):
    """
    Окно 1: Первые три графика в одном окне (1D, 1W, 1M).
    """
    fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(16, 5.5))
    if hasattr(fig.canvas, "manager") and fig.canvas.manager:
        fig.canvas.manager.set_window_title(f"Окно 1: Таймфреймы 1D, 1W, 1M ({ticker})")

    mc = mpf.make_marketcolors(up="#26a69a", down="#ef5350", inherit=True)
    custom_style = mpf.make_mpf_style(base_mpf_style="charles", marketcolors=mc, gridstyle="--")

    mpf.plot(df_daily, type="candle", ax=ax1, style=custom_style, axtitle="1. Дневной таймфрейм (1D)", ylabel="Цена ($)")
    mpf.plot(df_weekly, type="candle", ax=ax2, style=custom_style, axtitle="2. Недельный таймфрейм (1W)", ylabel="Цена ($)")
    mpf.plot(df_monthly, type="candle", ax=ax3, style=custom_style, axtitle="3. Месячный таймфрейм (1M)", ylabel="Цена ($)")

    fig.suptitle(f"Свечные графики {ticker} на разных таймфреймах (1D / 1W / 1M)", fontsize=13, fontweight="bold")
    plt.tight_layout()
    return fig


def plot_volume_separate_window(df_daily: pd.DataFrame, ticker: str = "MSFT"):
    """
    Окно 2: Отдельное окно с комбинированным графиком: свечи + объём торгов + SMA-20.
    """
    mc = mpf.make_marketcolors(up="#26a69a", down="#ef5350", inherit=True)
    custom_style = mpf.make_mpf_style(base_mpf_style="charles", marketcolors=mc, gridstyle="--")

    fig, axlist = mpf.plot(
        df_daily,
        type="candle",
        style=custom_style,
        title=f"\n{ticker}: Свечной график с объёмом торгов (Volume Subplot) и SMA-20",
        ylabel="Цена ($)",
        ylabel_lower="Объём акций",
        volume=True,
        mav=(20,),
        figsize=(11, 7),
        returnfig=True
    )
    if hasattr(fig.canvas, "manager") and fig.canvas.manager:
        fig.canvas.manager.set_window_title(f"Окно 2: Объём торгов и SMA-20 ({ticker})")
    return fig


def main():
    # 1. Загрузка котировок (MSFT)
    df_daily = fetch_stock_data("MSFT", days=400)

    # 2. Агрегация в недельный и месячный таймфреймы
    df_weekly = resample_ohlcv(df_daily, rule="W-FRI")
    df_monthly = resample_ohlcv(df_daily, rule="ME")

    print(f"\nВыгружено дневных свечей: {len(df_daily)}")
    print(f"Агрегировано недельных свечей: {len(df_weekly)}")
    print(f"Агрегировано месячных свечей: {len(df_monthly)}\n")

    print("[i] Создание двух окон Matplotlib...")
    # Окно 1: 3 таймфрейма вместе
    plot_three_timeframes_window(df_daily, df_weekly, df_monthly, ticker="MSFT")

    # Окно 2: График с объёмом и SMA-20 отдельно
    plot_volume_separate_window(df_daily, ticker="MSFT")

    print("[OK] Открытие окон через matplotlib.pyplot.show()...")
    print("     • Окно 1 — Три графика вместе: 1D, 1W, 1M")
    print("     • Окно 2 — Отдельный график: Свечи + Объём торгов + SMA-20")
    print("     (Закройте окна для завершения работы программы)")

    # Показ обоих окон
    plt.show()

    print("[OK] Работа скрипта успешно завершена.")


if __name__ == "__main__":
    main()
