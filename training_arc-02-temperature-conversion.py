unit = input("Is dit temperatuur in Celcius of Fahrenheit (C / F): ")
temp = float(input("Enter de temperatuur: "))

if unit == "C":
    temp = round((9 * temp) / 5 + 32, 1)
    print(f"De temperatuur in Fahrenheit is: {temp}°F")
elif unit == "F":
    temp = round((temp - 32 ) * 5 / 9, 1)
    print(f"De temperatuur in Celcius is: {temp}°C")
else:
    print(f"Unit is een ongeldig")