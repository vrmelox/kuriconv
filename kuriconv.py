import requests
import csv
import mysql.connector as MC

def getcurrencies():
    key_api = "6d650acd6e1a42c5935ca3703dca7182"
    surl = "https://api.currencyfreaks.com/v2.0/rates/latest"
    params = {"apikey" : key_api}
    response = requests.get(surl, params)
    data = response.json()
    rates = data["rates"]
    table = {}
    table = {keys: values for keys, values in rates.items()}
    return table

def payli():
    with open('currencies.txt', 'r') as currencies:
        total =  currencies.read()
    total = total.split("\n")
    car = []
    tabcurrencies = []
    for x in total:
        car = x.split("-", 1)
        tabcurrencies.append(car)
    return tabcurrencies

def buidler(table, listcurrencies):
    keys = list(table.keys())
    my_table = {cle: None for cle in keys if cle != "SOLVBTC" and cle != "USD0"}
    mapping = {key: values for key, values in table.items()}
    for currencies in listcurrencies:
        cle = currencies[0].strip()
        if cle in mapping:
            currencies[0] = currencies[1].strip()
            currencies[1] = mapping[cle]
            my_table[cle] = currencies
    return my_table

def currency_storage(table):
    try:
        conn = MC.connect(
            host='localhost',
            database='kuriconv',
            user='vrmelo',
            password='Laure@2024!'
        )
        cursor = conn.cursor()

        curates = [(key, value[0], value[1]) for key, value in table.items()]
        cursor.executemany("""INSERT INTO devise_rates(devise, devise_name, rates) VALUES(%s, %s, %s)""", curates)
        conn.commit()

    except MC.Error as err:
        print(f"Erreur: {err}")
        conn.rollback()
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

table = buidler(getcurrencies(), payli())
currency_storage(table)