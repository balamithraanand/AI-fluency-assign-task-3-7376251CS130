from tools import calculate_bill

question = "Calculate my bill: 2 dosa, 1 veg rice and 2 coffee."

items = {
    "dosa": 2,
    "veg rice": 1,
    "coffee": 2
}

print("Question:", question)
print("Decision: Tool required")
print("Tool call: calculate_bill")
print("Tool input:", items)

result = calculate_bill(items)

print("Tool result:", result)
print("Final answer:", result)