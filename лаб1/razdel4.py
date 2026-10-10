"""
Раздел 4. Портфельный анализ.
1. Выбор двух тикеров акций на букву фамилии в транслитерации (Байков -> B: BSPB и BANEP).
2. Формирование портфеля: X акций первой компании (27 шт.) и T акций второй компании (5 шт.).
   Построение графика стоимости портфеля.
3. Формирование портфеля с равными долями по стоимости (50% / 50%) на начальную дату.
4. Ребалансировка портфеля через полгода (6 месяцев). Анализ: даёт ли это рост доходности?

Оба графика отображаются в ОДНОМ окне Matplotlib:
- Слева: Стоимость портфеля X и T (по дате рождения)
- Справа: Сравнение стратегий 50/50 (Buy & Hold против ребалансировки через 6 месяцев)
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

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def fetch_moex_history(ticker: str, days: int = 400) -> pd.DataFrame:
    """Выгрузка исторических котировок с Московской Биржи."""
    end_date = datetime.today()
    start_date = end_date - timedelta(days=days)

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
    return df[["CLOSE"]].rename(columns={"CLOSE": ticker}).dropna()


def analyze_portfolios(x_shares: int = 27, t_shares: int = 5):
    """
    Анализ трёх вариантов портфеля:
    1. Портфель X и T (27 акций BSPB, 5 акций BANEP)
    2. Портфель с равными долями 50/50 по начальной стоимости БЕЗ ребалансировки (Buy & Hold)
    3. Портфель с равными долями 50/50 С РЕБАЛАНСИРОВКОЙ через 6 месяцев
    """
    ticker1 = "BSPB"
    ticker2 = "BANEP"

    print(f"[i] Выгрузка данных по {ticker1} и {ticker2}...")
    df1 = fetch_moex_history(ticker1)
    df2 = fetch_moex_history(ticker2)

    # Объединяем котировки по общим торговым дням
    df = pd.concat([df1, df2], axis=1).dropna()
    p1_0 = df[ticker1].iloc[0]
    p2_0 = df[ticker2].iloc[0]

    # ==========================================
    # 1. Портфель X и T
    # ==========================================
    df["Portfolio_XT"] = x_shares * df[ticker1] + t_shares * df[ticker2]
    v_xt_start = df["Portfolio_XT"].iloc[0]
    v_xt_end = df["Portfolio_XT"].iloc[-1]
    ret_xt = (v_xt_end - v_xt_start) / v_xt_start * 100

    # Начальные доли
    val1_0_xt = x_shares * p1_0
    val2_0_xt = t_shares * p2_0
    w1_xt_start = val1_0_xt / v_xt_start * 100
    w2_xt_start = val2_0_xt / v_xt_start * 100

    # ==========================================
    # 2. Портфель 50/50 по начальной стоимости (Buy & Hold)
    # ==========================================
    v0 = v_xt_start
    c_each_0 = v0 / 2.0
    n1_eq = c_each_0 / p1_0
    n2_eq = c_each_0 / p2_0

    df["Portfolio_50_50_BH"] = n1_eq * df[ticker1] + n2_eq * df[ticker2]
    v_bh_end = df["Portfolio_50_50_BH"].iloc[-1]
    ret_bh = (v_bh_end - v0) / v0 * 100

    # ==========================================
    # 3. Портфель 50/50 С РЕБАЛАНСИРОВКОЙ через 6 месяцев
    # ==========================================
    start_date = df.index[0]
    reb_target_date = start_date + pd.DateOffset(months=6)

    reb_idx = df.index.searchsorted(reb_target_date)
    if reb_idx >= len(df):
        reb_idx = len(df) // 2
    reb_date = df.index[reb_idx]

    port_reb_values = []
    cur_n1 = n1_eq
    cur_n2 = n2_eq

    for date, row in df.iterrows():
        if date == reb_date:
            v_reb = cur_n1 * row[ticker1] + cur_n2 * row[ticker2]
            cur_n1 = (0.5 * v_reb) / row[ticker1]
            cur_n2 = (0.5 * v_reb) / row[ticker2]

        val = cur_n1 * row[ticker1] + cur_n2 * row[ticker2]
        port_reb_values.append(val)

    df["Portfolio_50_50_REB"] = port_reb_values
    v_reb_end = df["Portfolio_50_50_REB"].iloc[-1]
    ret_reb = (v_reb_end - v0) / v0 * 100

    # Статистика волатильности
    ret_bh_daily = df["Portfolio_50_50_BH"].pct_change().dropna()
    ret_reb_daily = df["Portfolio_50_50_REB"].pct_change().dropna()

    vol_bh_annual = ret_bh_daily.std() * np.sqrt(252) * 100
    vol_reb_annual = ret_reb_daily.std() * np.sqrt(252) * 100

    # Максимальная просадка (Max Drawdown)
    def calc_mdd(series):
        cummax = series.cummax()
        drawdown = (series - cummax) / cummax
        return drawdown.min() * 100

    mdd_bh = calc_mdd(df["Portfolio_50_50_BH"])
    mdd_reb = calc_mdd(df["Portfolio_50_50_REB"])

    results = {
        "ticker1": ticker1,
        "ticker2": ticker2,
        "x_shares": x_shares,
        "t_shares": t_shares,
        "start_date": df.index[0].strftime("%d.%m.%Y"),
        "end_date": df.index[-1].strftime("%d.%m.%Y"),
        "reb_date": reb_date.strftime("%d.%m.%Y"),
        "p1_0": p1_0,
        "p2_0": p2_0,
        "p1_end": df[ticker1].iloc[-1],
        "p2_end": df[ticker2].iloc[-1],
        "v0": v0,
        "v_xt_start": v_xt_start,
        "v_xt_end": v_xt_end,
        "ret_xt": ret_xt,
        "w1_xt_start": w1_xt_start,
        "w2_xt_start": w2_xt_start,
        "n1_eq": n1_eq,
        "n2_eq": n2_eq,
        "v_bh_end": v_bh_end,
        "ret_bh": ret_bh,
        "vol_bh_annual": vol_bh_annual,
        "mdd_bh": mdd_bh,
        "v_reb_end": v_reb_end,
        "ret_reb": ret_reb,
        "vol_reb_annual": vol_reb_annual,
        "mdd_reb": mdd_reb,
        "diff_ret": ret_reb - ret_bh
    }
    return df, results


def plot_portfolio_dashboard_window(df: pd.DataFrame, res: dict):
    """
    Вывод обоих графиков Раздела 4 в ОДНОМ окне Matplotlib.
    Слева: Портфель X и T (по дате рождения).
    Справа: Сравнение стратегий 50/50 (Buy & Hold vs Ребалансировка через 6 мес.).
    """
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
    if hasattr(fig.canvas, "manager") and fig.canvas.manager:
        fig.canvas.manager.set_window_title(f"Раздел 4: Портфельный анализ ({res['ticker1']} и {res['ticker2']})")

    # 1. Левый график: портфель X и T
    ax1.plot(df.index, df["Portfolio_XT"], color="#0288d1", lw=2, label=f"Портфель ({res['x_shares']} шт. {res['ticker1']} + {res['t_shares']} шт. {res['ticker2']})")
    ax1.set_title(f"1. Портфель по дате рождения ({res['x_shares']} {res['ticker1']} + {res['t_shares']} {res['ticker2']})", fontsize=11, fontweight="bold")
    ax1.set_xlabel("Дата", fontsize=10)
    ax1.set_ylabel("Стоимость портфеля (руб.)", fontsize=10)
    ax1.grid(True, linestyle="--", alpha=0.5)
    ax1.legend(loc="upper left", frameon=True, fontsize=9.5)

    ax1.scatter([df.index[0], df.index[-1]], [df["Portfolio_XT"].iloc[0], df["Portfolio_XT"].iloc[-1]], color="#d32f2f", zorder=5)
    ax1.text(df.index[0], df["Portfolio_XT"].iloc[0] + 250, f" Старт: {df['Portfolio_XT'].iloc[0]:.0f} ₽", fontsize=9, fontweight="bold")
    ax1.text(df.index[-1], df["Portfolio_XT"].iloc[-1] + 250, f" Финал: {df['Portfolio_XT'].iloc[-1]:.0f} ₽", ha="right", fontsize=9, fontweight="bold")

    # 2. Правый график: Buy & Hold против Ребалансировки
    ax2.plot(df.index, df["Portfolio_50_50_BH"], label=f"Buy & Hold (доходность: {res['ret_bh']:+.2f}%)", color="#1976d2", lw=2)
    ax2.plot(df.index, df["Portfolio_50_50_REB"], label=f"С ребалансировкой (доходность: {res['ret_reb']:+.2f}%)", color="#e65100", lw=2, linestyle="--")

    reb_date = pd.to_datetime(res["reb_date"], format="%d.%m.%Y")
    ax2.axvline(reb_date, color="#388e3c", linestyle=":", lw=2, label=f"Ребалансировка: {res['reb_date']}")

    ax2.set_title("2. Сравнение стратегий 50/50 (Buy & Hold vs Ребалансировка)", fontsize=11, fontweight="bold")
    ax2.set_xlabel("Дата", fontsize=10)
    ax2.set_ylabel("Стоимость портфеля (руб.)", fontsize=10)
    ax2.legend(loc="upper left", frameon=True, fontsize=9.5)
    ax2.grid(True, linestyle="--", alpha=0.5)

    fig.suptitle(f"Портфельный анализ акций {res['ticker1']} и {res['ticker2']}", fontsize=13, fontweight="bold", y=0.98)
    plt.tight_layout()
    return fig


def main():
    df, res = analyze_portfolios(x_shares=27, t_shares=5)

    print("=" * 70)
    print("РАЗДЕЛ 4: ПОРТФЕЛЬНЫЙ АНАЛИЗ (BSPB и BANEP)")
    print("=" * 70)
    print(f"Период анализа: {res['start_date']} — {res['end_date']}")
    print(f"Стартовая цена {res['ticker1']}: {res['p1_0']:.2f} руб., финальная: {res['p1_end']:.2f} руб.")
    print(f"Стартовая цена {res['ticker2']}: {res['p2_0']:.2f} руб., финальная: {res['p2_end']:.2f} руб.")
    print()
    print("1. Портфель из X (27) акций BSPB и T (5) акций BANEP:")
    print(f"   - Начальная стоимость: {res['v_xt_start']:.2f} руб.")
    print(f"   - Доля {res['ticker1']} на старте: {res['w1_xt_start']:.2f}%")
    print(f"   - Доля {res['ticker2']} на старте: {res['w2_xt_start']:.2f}%")
    print(f"   - Конечная стоимость:   {res['v_xt_end']:.2f} руб.")
    print(f"   - Доходность портфеля: {res['ret_xt']:+.2f}%")
    print()
    print("2. Портфель с равными долями 50/50 по стоимости (начальный капитал = 14 998.58 руб.):")
    print(f"   - Количество акций {res['ticker1']}: {res['n1_eq']:.4f} шт. (стоимость {res['v0']/2:.2f} руб.)")
    print(f"   - Количество акций {res['ticker2']}: {res['n2_eq']:.4f} шт. (стоимость {res['v0']/2:.2f} руб.)")
    print(f"   - Финальная стоимость (Buy & Hold): {res['v_bh_end']:.2f} руб.")
    print(f"   - Доходность (Buy & Hold):         {res['ret_bh']:+.2f}%")
    print(f"   - Волатильность годовая:           {res['vol_bh_annual']:.2f}%")
    print(f"   - Максимальная просадка (MDD):      {res['mdd_bh']:.2f}%")
    print()
    print("3. Ребалансировка через 6 месяцев (дата: " + res['reb_date'] + "):")
    print(f"   - Финальная стоимость (с ребалансировкой): {res['v_reb_end']:.2f} руб.")
    print(f"   - Доходность (с ребалансировкой):         {res['ret_reb']:+.2f}%")
    print(f"   - Волатильность годовая:                  {res['vol_reb_annual']:.2f}%")
    print(f"   - Максимальная просадка (MDD):             {res['mdd_reb']:.2f}%")
    print()
    print("4. Ответ на вопрос: Даёт ли ребалансировка рост доходности портфеля?")
    diff = res["diff_ret"]
    if diff > 0:
        print(f"   [ДА] Ребалансировка увеличила доходность на {diff:+.2f} процентных пунктов.")
    else:
        print(f"   [НЕТ] Доходность с ребалансировкой изменилась на {diff:+.2f} процентных пунктов по сравнению с Buy & Hold.")
    print("=" * 70)

    print("\n[i] Построение графиков Раздела 4 в одном окне Matplotlib...")
    plot_portfolio_dashboard_window(df, res)

    print("[OK] Открытие единого окна графиков через matplotlib.pyplot.show()...")
    print("     (Закройте окно для завершения работы программы)")
    plt.show()

    print("[OK] Работа скрипта успешно завершена.")


if __name__ == "__main__":
    main()
