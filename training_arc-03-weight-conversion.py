# Python weight converter

weight = float(input("Enter your weight: "))
unit = input("Kilogram or Pounds? (K or L): ")

if unit.upper() == "K":
    weight = weight * 2.205
    unit = "Lbs."
elif unit.upper() == "P":
    weight = weight / 2.205
    unit = "Kgs."
else:
    print(f"{unit} is niet geldig")

print(f"Jouw gewicht is: {round(weight,1)} {unit}")