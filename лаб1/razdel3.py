"""
Раздел 3. Доходность, вариация.
1. Расчёт ежедневных доходностей: относительных и логарифмических.
2. Расчёт С-среднего (средней доходности) и В-вариации (дисперсии и волатильности) за год.
3. Проверка правила sqrt(T): сравнение месячных вариаций и годовой.

Все 3 графика отображаются в ОДНОМ общем окне Matplotlib:
- Сверху: Динамика ежедневных доходностей
- Снизу слева: Распределение доходностей с нормальной кривой Гаусса
- Снизу справа: Проверка правила sqrt(T)
"""

import sys
import logging
import warnings
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
import requests
import apimoex

# Отключаем системный спам логов шрифтов от Matplotlib
warnings.filterwarnings("ignore")
logging.getLogger("matplotlib").setLevel(logging.ERROR)
logging.getLogger("matplotlib.font_manager").setLevel(logging.ERROR)

import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def fetch_moex_stock(ticker: str = "SBER", days: int = 400) -> pd.DataFrame:
    """Выгрузка исторических котировок акции с Московской Биржи (TQBR)."""
    end_date = datetime.today()
    start_date = end_date - timedelta(days=days)

    print(f"[i] Загрузка котировок {ticker} с MOEX за период {start_date.strftime('%Y-%m-%d')} - {end_date.strftime('%Y-%m-%d')}...")
    with requests.Session() as session:
        data = apimoex.get_board_history(
            session,
            security=ticker,
            start=start_date.strftime("%Y-%m-%d"),
            end=end_date.strftime("%Y-%m-%d"),
            board="TQBR"
        )
    df = pd.DataFrame(data)
    df["TRADEDATE"] = pd.to_datetime(df["TRADEDATE"])
    df.set_index("TRADEDATE", inplace=True)
    df.sort_index(inplace=True)
    df = df[["CLOSE", "VOLUME"]].dropna()
    return df


def calculate_returns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Расчёт ежедневных доходностей:
    - Относительная доходность: R_t = (P_t - P_{t-1}) / P_{t-1} = P_t / P_{t-1} - 1
    - Логарифмическая доходность: r_t = ln(P_t / P_{t-1}) = ln(P_t) - ln(P_{t-1})
    """
    res = df.copy()
    res["Simple_Return"] = res["CLOSE"].pct_change()
    res["Log_Return"] = np.log(res["CLOSE"] / res["CLOSE"].shift(1))
    return res.dropna()


def analyze_returns(df_returns: pd.DataFrame, ticker: str = "SBER") -> dict:
    """
    Расчёт С-среднего и В-вариации за год, а также проверка правила sqrt(T).
    """
    log_ret = df_returns["Log_Return"]
    n_days = len(log_ret)
    trading_days_per_year = 252

    # Дневные статистики
    mean_daily = log_ret.mean()
    var_daily = log_ret.var(ddof=1)
    std_daily = log_ret.std(ddof=1)

    # Годовые статистики (аннуализированные)
    mean_annual = mean_daily * trading_days_per_year
    var_annual = var_daily * trading_days_per_year
    std_annual = std_daily * np.sqrt(trading_days_per_year)
    cv_annual = std_annual / mean_annual if mean_annual != 0 else np.nan

    # Расчёт месячных показателей
    df_monthly = df_returns["CLOSE"].resample("ME").last().dropna()
    monthly_log_ret = np.log(df_monthly / df_monthly.shift(1)).dropna()

    mean_monthly = monthly_log_ret.mean()
    var_monthly = monthly_log_ret.var(ddof=1)
    std_monthly = monthly_log_ret.std(ddof=1)

    # Проверка правила sqrt(T) для месячных данных (T = 12 месяцев в году)
    std_annual_from_monthly = std_monthly * np.sqrt(12)
    var_annual_from_monthly = var_monthly * 12

    abs_diff_std = abs(std_annual_from_monthly - std_annual)
    rel_diff_std_pct = (abs_diff_std / std_annual) * 100

    abs_diff_var = abs(var_annual_from_monthly - var_annual)
    rel_diff_var_pct = (abs_diff_var / var_annual) * 100

    stats = {
        "ticker": ticker,
        "n_days": n_days,
        "n_months": len(monthly_log_ret),
        "mean_daily": mean_daily,
        "var_daily": var_daily,
        "std_daily": std_daily,
        "mean_annual": mean_annual,
        "var_annual": var_annual,
        "std_annual": std_annual,
        "cv_annual": cv_annual,
        "mean_monthly": mean_monthly,
        "var_monthly": var_monthly,
        "std_monthly": std_monthly,
        "std_annual_from_monthly": std_annual_from_monthly,
        "var_annual_from_monthly": var_annual_from_monthly,
        "abs_diff_std": abs_diff_std,
        "rel_diff_std_pct": rel_diff_std_pct,
        "abs_diff_var": abs_diff_var,
        "rel_diff_var_pct": rel_diff_var_pct,
        "monthly_series": monthly_log_ret
    }
    return stats


def plot_returns_dashboard_window(df_returns: pd.DataFrame, stats: dict):
    """
    Вывод всех 3 графиков Раздела 3 в ОДНОМ окне Matplotlib.
    """
    fig = plt.figure(figsize=(15, 8.5))
    if hasattr(fig.canvas, "manager") and fig.canvas.manager:
        fig.canvas.manager.set_window_title(f"Раздел 3: Анализ доходности и риска ({stats['ticker']})")

    gs = gridspec.GridSpec(2, 2, figure=fig, height_ratios=[1.1, 1.0], hspace=0.35, wspace=0.25)

    # 1. Верхний график на всю ширину: динамика ежедневных доходностей
    ax1 = fig.add_subplot(gs[0, :])
    ax1.plot(df_returns.index, df_returns["Simple_Return"] * 100, label="Относительная доходность (Simple %)", color="#1976d2", alpha=0.7, lw=1)
    ax1.plot(df_returns.index, df_returns["Log_Return"] * 100, label="Логарифмическая доходность (Log %)", color="#d32f2f", alpha=0.7, lw=1, linestyle="--")
    ax1.axhline(0, color="black", lw=0.8, linestyle=":")
    ax1.set_title(f"1. Динамика ежедневных доходностей {stats['ticker']}", fontsize=12, fontweight="bold")
    ax1.set_xlabel("Дата", fontsize=10)
    ax1.set_ylabel("Доходность (%)", fontsize=10)
    ax1.legend(loc="upper right", frameon=True)
    ax1.grid(True, linestyle="--", alpha=0.5)

    # 2. Нижний левый: гистограмма распределения с нормальной кривой
    ax2 = fig.add_subplot(gs[1, 0])
    ret_pct = df_returns["Log_Return"] * 100
    ax2.hist(ret_pct, bins=35, density=True, color="#42a5f5", edgecolor="#1565c0", alpha=0.7, label="Фактическая плотность")

    mu_pct = ret_pct.mean()
    sigma_pct = ret_pct.std()
    x = np.linspace(ret_pct.min(), ret_pct.max(), 200)
    pdf = (1 / (sigma_pct * np.sqrt(2 * np.pi))) * np.exp(-0.5 * ((x - mu_pct) / sigma_pct) ** 2)
    ax2.plot(x, pdf, color="#d32f2f", lw=2, label=f"Нормальное распределение\n(μ={mu_pct:.2f}%, σ={sigma_pct:.2f}%)")
    ax2.axvline(mu_pct, color="green", linestyle="--", lw=1.5, label=f"Среднее = {mu_pct:.2f}%")
    ax2.set_title(f"2. Распределение доходностей {stats['ticker']}", fontsize=11, fontweight="bold")
    ax2.set_xlabel("Дневная лог-доходность (%)", fontsize=9.5)
    ax2.set_ylabel("Плотность вероятности", fontsize=9.5)
    ax2.legend(frameon=True, fontsize=8.5)
    ax2.grid(True, linestyle="--", alpha=0.5)

    # 3. Нижний правый: проверка правила sqrt(T)
    ax3 = fig.add_subplot(gs[1, 1])
    categories = [
        "Месячная волатильность\nσ_month",
        "По правилу √12\nσ_month * √12\n(теоретическая)",
        "Годовая волатильность\nσ_year\n(фактическая)"
    ]
    vals = [
        stats["std_monthly"] * 100,
        stats["std_annual_from_monthly"] * 100,
        stats["std_annual"] * 100
    ]
    colors = ["#4caf50", "#ff9800", "#2196f3"]
    bars = ax3.bar(categories, vals, color=colors, width=0.55, edgecolor="black", linewidth=0.8)

    for bar, val in zip(bars, vals):
        yval = bar.get_height()
        ax3.text(bar.get_x() + bar.get_width() / 2, yval + 0.4, f"{val:.2f}%", ha="center", va="bottom", fontsize=10, fontweight="bold")

    ax3.set_ylim(0, max(vals) * 1.25)
    ax3.set_ylabel("Волатильность (%)", fontsize=9.5)
    ax3.set_title("3. Проверка правила √T (месячная vs годовая)", fontsize=11, fontweight="bold")
    ax3.grid(axis="y", linestyle="--", alpha=0.5)

    fig.suptitle(f"Статистический анализ доходности и волатильности {stats['ticker']}", fontsize=14, fontweight="bold", y=0.98)
    return fig


def main():
    ticker = "SBER"

    # 1. Загрузка данных и расчёт доходностей
    df = fetch_moex_stock(ticker=ticker, days=400)
    df_returns = calculate_returns(df)

    # 2. Анализ С-среднего, В-вариации и правила sqrt(T)
    stats = analyze_returns(df_returns, ticker=ticker)

    # Вывод статистического отчёта в консоль
    print("=" * 65)
    print(f"РАЗДЕЛ 3: СТАТИСТИЧЕСКИЙ АНАЛИЗ ДОХОДНОСТЕЙ {ticker}")
    print("=" * 65)
    print(f"Количество торговых дней: {stats['n_days']}")
    print(f"Количество месяцев:       {stats['n_months']}")
    print()
    print("1. Ежедневные показатели:")
    print(f"   - Дневное С-среднее (μ_day):       {stats['mean_daily'] * 100:+.4f}%")
    print(f"   - Дневная В-вариация (дисперсия):  {stats['var_daily']:.6f}")
    print(f"   - Дневная волатильность (σ_day):   {stats['std_daily'] * 100:.4f}%")
    print()
    print("2. Годовые показатели (на базе 252 торговых дней):")
    print(f"   - Годовое С-среднее (μ_year):      {stats['mean_annual'] * 100:+.2f}%")
    print(f"   - Годовая В-вариация (дисперсия):  {stats['var_annual']:.6f}")
    print(f"   - Годовая волатильность (σ_year):  {stats['std_annual'] * 100:.2f}%")
    print(f"   - Коэффициент вариации (CV = σ/μ): {stats['cv_annual']:.2f}")
    print()
    print("3. Месячные показатели:")
    print(f"   - Месячное среднее (μ_month):      {stats['mean_monthly'] * 100:+.2f}%")
    print(f"   - Месячная вариация (дисперсия):   {stats['var_monthly']:.6f}")
    print(f"   - Месячная волатильность (σ_month):{stats['std_monthly'] * 100:.2f}%")
    print()
    print("4. Проверка правила корня из времени sqrt(T):")
    print(f"   - Месячная волатильность:             {stats['std_monthly'] * 100:.2f}%")
    print(f"   - Теоретическая годовая волатильность (σ_month * √12): {stats['std_annual_from_monthly'] * 100:.2f}%")
    print(f"   - Фактическая годовая волатильность (дневная * √252):   {stats['std_annual'] * 100:.2f}%")
    print(f"   - Абсолютное расхождение волатильностей:               {stats['abs_diff_std'] * 100:.2f} п.п.")
    print(f"   - Относительное отклонение:                            {stats['rel_diff_std_pct']:.2f}%")
    print("=" * 65)

    print("\n[i] Построение графиков Раздела 3 в одном окне Matplotlib...")
    plot_returns_dashboard_window(df_returns, stats)

    print("[OK] Открытие единого окна графиков через matplotlib.pyplot.show()...")
    print("     (Закройте окно для завершения работы программы)")
    plt.show()

    print("[OK] Работа скрипта успешно завершена.")


if __name__ == "__main__":
    main()
