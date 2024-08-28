def payli():
    with open('currencies.txt', 'r') as currencies:
        total =  currencies.read()
    total = total.split("\n")
    car = []
    table = []
    for x in total:
        car = x.split("-", 1)
        table.append(car)
    return table