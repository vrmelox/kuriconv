import requests
import csv
import mysql.connector as MC

def getcurrencies():
    key_api = "6d650acd6e1a42c5935ca3703dca7182"
    surl = "https://api.currencyfreaks.com/v2.0/rates/latest"
    params = {"apikey" : key_api}
    response = requests.get(surl, params)
    data = response.json()
    en_tete = []
    ligne = []
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
    my_table = {cle: None for cle in keys}
    mapping = {key: values for key, values in table.items()}
    for currencies in listcurrencies:
        cle = currencies[0].strip()
        if cle in mapping:
            currencies[0] = currencies[1].strip()
            currencies[1] = mapping[cle]
            my_table[cle] = currencies
    return my_table
buidler(getcurrencies(), payli())

try:
    # Connexion à la base de données
    conn = MC.connect(
        host='localhost',
        database='kuriconv',
        user='vrmelo',
        password='Laure@2024!'
    )
    cursor = conn.cursor()

    # Exécuter la requête
    req = "SELECT * FROM devise_rates"
    cursor.execute(req)

    # Récupérer tous les résultats
    results = cursor.fetchall()

    # Traiter les résultats
    for row in results:
        print(row)

except MC.Error as err:
    print(f"Erreur: {err}")

finally:
    # Assurer la fermeture des ressources
    if conn.is_connected():
        cursor.close()
        conn.close()