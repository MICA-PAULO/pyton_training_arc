def menu_data():
    menu_dict = [
        {"menu_item_id": "1", "menu_item": "Pizza Slice", "menu_price": 2.99},
        {"menu_item_id": "2", "menu_item": "Burger Combo", "menu_price": 6.49},
        {"menu_item_id": "3", "menu_item": "Coca Cola", "menu_price": 1.99},
        {"menu_item_id": "4", "menu_item": "Nachos with Cheese", "menu_price": 4.25},
        {"menu_item_id": "5", "menu_item": "Ice Cream Sundae", "menu_price": 3.99},
    ]
    return menu_dict

def haal_order(menu):
    programma_draait = True
    cart = {}
    totaal = 0
    while programma_draait:
        food = input("Selecteer een nummer om een product toe te voegen. (q voor quit) ")
        if food == "q":
            programma_draait = False
        else:
            item = next((item for item in menu if item["menu_item_id"] == food), None)
            if item is not None:
                if item["menu_item"] in cart:
                    cart[item["menu_item"]]["aantal"] += 1
                else:
                    cart[item["menu_item"]] = {"item": item, "aantal": 1}
                totaal += item["menu_price"]

            for product, data in cart.items():
                print(f"{product}: {data['aantal']}x {data['item']['menu_price']:.2f} EUR")

    print("\nJe bestelling:")
    for product, data in cart.items():
        print(f"{product}: {data['aantal']}x {data['item']['menu_price']:.2f} EUR")
    print(f"Totaal: {totaal:.2f} EUR")
    return cart, totaal

def menu_uitlezen(menu):
    for item in menu:
        menu_item = item["menu_item"]
        menu_price = item["menu_price"]
        menu_id = item["menu_item_id"]
        print(f"{menu_id}.{menu_item.ljust(30)}{menu_price:.2f}")

def main():
    print("Welkom in de bioscoop winkel! Selecteer welke items je wilt kopen:")
    menu = menu_data()

    while True:
        menu_uitlezen(menu)
        cart, totaal = haal_order(menu)

        again = input("Wil je nog een bestelling plaatsen? (ja/nee): ")
        if again.lower() != "ja":
            break

if __name__ == '__main__':
    main()
