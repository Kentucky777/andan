import math

x = float(input("Введите число: "))
print("Корень:", math.sqrt(x))

import random

a = int(input("От: "))
b = int(input("До: "))
print("Случайное число:", random.randint(a, b))

from datetime import datetime, timedelta

days = int(input("Через сколько дней дата? "))
future = datetime.now() + timedelta(days=days)
print("Дата:", future.strftime("%d.%m.%Y"))

import numpy as np

values = input("Введите числа через пробел: ")
arr = np.array([float(x) for x in values.split()])
print("Среднее:", arr.mean())

import pandas as pd

names = []
ages = []

# Ввод нескольких строк данных
n = int(input("Сколько человек хотите ввести? "))

for i in range(n):
    name = input(f"Введите имя {i+1}: ").strip()
    try:
        age = int(input(f"Введите возраст {i+1}: "))
    except ValueError:
        print("Возраст введён некорректно, будет сохранён как пустое значение")
        age = None
    names.append(name)
    ages.append(age)

# Создаём таблицу
df = pd.DataFrame({"Имя": names, "Возраст": ages})
print("\nВся таблица:")
print(df)

# Фильтрация на столбцы (выбираем только один столбец, например "Имя")
print("\nТолько имена:")
print(df["Имя"])

# Фильтрация по условию (например, возраст больше 20)
print("\nЛюди старше 20 лет:")
print(df[df["Возраст"] > 20])

# Функция, которая считает средний возраст
def average_age(dataframe):
    return dataframe["Возраст"].mean()

print("\nСредний возраст:", average_age(df))