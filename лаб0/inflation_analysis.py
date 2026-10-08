import sys
from datetime import date
from io import BytesIO
from statistics import mean, stdev

import pandas as pd
import requests

FORECAST_MONTHS = 3          # на сколько месяцев вперёд прогнозировать
WINDOW_MONTHS = 12            # сколько месяцев истории скачивать с сайта
PLOT_PATH = "inflation_chart.png"   # куда сохранить график
SHOW_PLOT_WINDOW = True       # показывать ли график во всплывающем окне

LOCAL_FILE = None  # например: "inf.xlsx"

# Ссылка на экспорт в XLSX, которую использует сама страница
# https://cbr.ru/hd_base/infl/ (кнопка "XLSX" на странице).
CBR_EXPORT_URL = "https://cbr.ru/Queries/UniDbQuery/DownloadExcel/132934"


# ------------------------- Загрузка данных с сайта ЦБ -------------------------

def fetch_cbr_inflation(from_date: date, to_date: date) -> pd.DataFrame:
    """Скачивает XLSX с данными по инфляции и ключевой ставке напрямую с cbr.ru."""
    params = {
        "FromDate": from_date.strftime("%m/%d/%Y"),
        "ToDate": to_date.strftime("%m/%d/%Y"),
        "posted": "False",
    }
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

    try:
        resp = requests.get(CBR_EXPORT_URL, params=params, headers=headers, timeout=30)
        resp.raise_for_status()
    except requests.exceptions.SSLError:
        # На некоторых машинах не хватает корневого сертификата Минцифры для cbr.ru —
        # используем запрос без проверки сертификата как запасной вариант.
        print("[!] Проблема с SSL-сертификатом cbr.ru, повторяю запрос без проверки сертификата.")
        resp = requests.get(CBR_EXPORT_URL, params=params, headers=headers, timeout=30, verify=False)
        resp.raise_for_status()

    return pd.read_excel(BytesIO(resp.content))


def parse_date_cell(v) -> pd.Timestamp:
    """Поддерживает даты вида '08.2026' (строка) и 8.2026 (float, как иногда читает Excel)."""
    if isinstance(v, str):
        return pd.to_datetime(v, format="%m.%Y")
    month = int(v)
    year = round((v - month) * 10000)
    return pd.Timestamp(year=year, month=month, day=1)


def normalize(df: pd.DataFrame) -> pd.DataFrame:
    """Приводит сырые данные (с сайта или из файла) к единому виду: date, key_rate, inflation, target."""
    df = df.copy()
    df.columns = ["date_raw", "key_rate", "inflation", "target"]
    df["date"] = df["date_raw"].apply(parse_date_cell)
    df = df.sort_values("date").reset_index(drop=True)
    return df[["date", "key_rate", "inflation", "target"]]


def load_data_from_file(filepath: str) -> pd.DataFrame:
    if filepath.lower().endswith((".xlsx", ".xlsm", ".xls")):
        raw = pd.read_excel(filepath)
    else:
        raw = pd.read_csv(filepath)
    return normalize(raw)


# ------------------------- Анализ -------------------------

def analyze(df: pd.DataFrame) -> dict:
    infl = df["inflation"].tolist()
    mom_change = df["inflation"].diff().tolist()
    corr = df["key_rate"].corr(df["inflation"])

    return {
        "n": len(infl),
        "mean": mean(infl),
        "std": stdev(infl) if len(infl) > 1 else 0.0,
        "min": min(infl),
        "max": max(infl),
        "last": infl[-1],
        "mom_change": mom_change,
        "corr_rate_inflation": corr,
        "gap_to_target": infl[-1] - df["target"].iloc[-1],
    }


def linear_forecast(values: list[float], periods_ahead: int) -> list[float]:
    """Прогноз методом наименьших квадратов по индексу периода (простая линейная модель)."""
    n = len(values)
    xs = list(range(n))
    x_mean, y_mean = mean(xs), mean(values)
    num = sum((x - x_mean) * (y - y_mean) for x, y in zip(xs, values))
    den = sum((x - x_mean) ** 2 for x in xs)
    slope = num / den if den != 0 else 0.0
    intercept = y_mean - slope * x_mean
    return [slope * (n - 1 + i) + intercept for i in range(1, periods_ahead + 1)]


def forecast_dates(last_date: pd.Timestamp, periods_ahead: int) -> list[pd.Timestamp]:
    return [last_date + pd.DateOffset(months=i) for i in range(1, periods_ahead + 1)]


# ------------------------- Отчёт -------------------------

def print_report(df: pd.DataFrame, stats: dict, forecast: list[float], f_dates: list[pd.Timestamp]):
    print("=" * 60)
    print("АНАЛИЗ ИНФЛЯЦИИ И КЛЮЧЕВОЙ СТАВКИ")
    print("=" * 60)
    print(f"Период данных: {df['date'].iloc[0].strftime('%m.%Y')} — {df['date'].iloc[-1].strftime('%m.%Y')}")
    print(f"Наблюдений: {stats['n']}\n")

    print("-- Фактические данные --")
    for _, row in df.iterrows():
        print(f"  {row['date'].strftime('%m.%Y')}: инфляция {row['inflation']:.2f}%, "
              f"ключевая ставка {row['key_rate']:.2f}%, цель {row['target']:.0f}%")
    print()

    print("-- Статистика по инфляции --")
    print(f"  Среднее: {stats['mean']:.2f}%")
    print(f"  Std:     {stats['std']:.2f} п.п.")
    print(f"  Мин/Макс: {stats['min']:.2f}% / {stats['max']:.2f}%")
    print(f"  Последнее значение: {stats['last']:.2f}%")
    print(f"  Отклонение от цели: {stats['gap_to_target']:+.2f} п.п.\n")

    print("-- Изменение инфляции от месяца к месяцу (п.п.) --")
    for d, chg in zip(df["date"].iloc[1:], stats["mom_change"][1:]):
        print(f"  {d.strftime('%m.%Y')}: {chg:+.2f}")
    print()

    print(f"-- Корреляция: ключевая ставка ↔ инфляция: {stats['corr_rate_inflation']:+.2f} --")
    if stats["corr_rate_inflation"] < -0.3:
        print("  Отрицательная связь: повышение ставки в этом периоде сопровождалось")
        print("  снижением инфляции (или наоборот) — согласуется с логикой ДКП,")
        print("  но на 6 точках это не строгий вывод, а лишь наблюдение.\n")
    else:
        print("  Связь слабая/неочевидная на имеющихся данных.\n")

    print(f"-- Прогноз (простая линейная модель) на {len(forecast)} мес. вперёд --")
    for d, val in zip(f_dates, forecast):
        print(f"  {d.strftime('%m.%Y')}: {val:.2f}%")

def maybe_plot(df: pd.DataFrame, forecast: list[float], f_dates: list[pd.Timestamp], out_path: str):
    try:
        import matplotlib.pyplot as plt
        import matplotlib.dates as mdates
    except ImportError:
        print("[!] matplotlib не установлен — график пропущен.")
        return

    plt.figure(figsize=(9, 5.5))
    plt.plot(df["date"], df["inflation"], marker="o", label="Инфляция, факт (% г/г)", color="#1f77b4")
    plt.plot(df["date"], df["key_rate"], marker="s", linestyle=":", label="Ключевая ставка, % годовых", color="#888")
    plt.axhline(df["target"].iloc[-1], color="green", linestyle="--", linewidth=1, label="Цель ЦБ (4%)")

    fc_dates_full = [df["date"].iloc[-1]] + f_dates
    fc_vals_full = [df["inflation"].iloc[-1]] + forecast
    plt.plot(fc_dates_full, fc_vals_full, marker="o", linestyle="--", color="#d62728", label="Прогноз инфляции")

    plt.title("Инфляция и ключевая ставка Банка России")
    plt.xlabel("Период")
    plt.ylabel("%")
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter("%m.%Y"))
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    return plt


# ------------------------- Точка входа -------------------------

def main():
    if LOCAL_FILE:
        # Офлайн-режим — читаем локальный файл.
        print(f"[i] Использую локальный файл: {LOCAL_FILE}")
        try:
            df = load_data_from_file(LOCAL_FILE)
        except Exception as e:
            print(f"Ошибка чтения файла: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        # Основной режим — качаем свежие данные напрямую с сайта Банка России.
        to_date = date.today()
        from_date = (pd.Timestamp(to_date) - pd.DateOffset(months=WINDOW_MONTHS)).date()

        print(f"[i] Скачиваю данные с cbr.ru за период {from_date.strftime('%m.%Y')} — {to_date.strftime('%m.%Y')}...")
        try:
            raw = fetch_cbr_inflation(from_date, to_date)
            df = normalize(raw)
        except requests.exceptions.RequestException as e:
            print(f"Не удалось скачать данные с cbr.ru: {e}", file=sys.stderr)
            print("Проверьте интернет-соединение, либо укажите LOCAL_FILE в настройках вверху файла.", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"Ошибка обработки данных с сайта: {e}", file=sys.stderr)
            sys.exit(1)

    stats = analyze(df)
    forecast = linear_forecast(df["inflation"].tolist(), FORECAST_MONTHS)
    f_dates = forecast_dates(df["date"].iloc[-1], FORECAST_MONTHS)

    print_report(df, stats, forecast, f_dates)

    plt_module = maybe_plot(df, forecast, f_dates, PLOT_PATH)
    if SHOW_PLOT_WINDOW and plt_module is not None:
        plt_module.show()


if __name__ == "__main__":
    main()