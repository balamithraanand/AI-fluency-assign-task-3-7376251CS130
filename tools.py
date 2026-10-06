MENU = {
    "idli": 20,
    "dosa": 40,
    "veg rice": 70,
    "coffee": 15,
    "juice": 30
}

def calculate_bill(items):
    total = 0

    for item, quantity in items.items():
        item = item.lower()

        if item not in MENU:
            return f"Error: {item} is not available in the menu."

        if quantity <= 0:
            return "Error: Quantity must be greater than zero."

        total += MENU[item] * quantity

    return f"Total bill: ₹{total}"

calculate_bill_schema = {
    "name": "calculate_bill",
    "description": "Calculates the total price of selected campus canteen items.",
    "parameters": {
        "type": "object",
        "properties": {
            "items": {
                "type": "object",
                "description": "Menu items and their quantities."
            }
        },
        "required": ["items"]
    }
}