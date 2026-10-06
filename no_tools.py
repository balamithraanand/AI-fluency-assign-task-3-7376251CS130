def answer_without_tool(question):
    if question == "What is an AI agent?":
        return "An AI agent is a system that observes a task, decides what action is needed, and uses available tools when required."

    return "This question can be answered directly without using an external tool."


question = "What is an AI agent?"

print("Question:", question)
print("Tool call: None")
print("Answer:", answer_without_tool(question))