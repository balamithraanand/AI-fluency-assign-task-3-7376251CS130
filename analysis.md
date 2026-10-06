# Day 3 – Agent Analysis

## 1. Objective

The objective of this task was to understand how an LLM agent uses tools, records tool calls, observes tool results, and continues reasoning until it produces a final answer.

The agent used two tools:

* `read_webpage` – reads information from a local HTML file or webpage.
* `calculator` – performs arithmetic calculations.

The original agent was first tested without safety guards. Then three guards were added to prevent repeated tool calls, oversized observations, and excessive context usage.

---

## 2. Scenario

The agent was given the following question:

> Read notice.html and tell me the total fee for CS101 and AI202 after the merit scholarship.

The `notice.html` file contains these fees:

* CS101 = Rs. 12,000
* AI202 = Rs. 18,000
* Merit scholarship = 10%

The agent should read the webpage first and then use the calculator instead of calculating the answer itself.

---

## 3. Agent Execution Flow

The agent follows these main stages:

### Step 1 – Reason

The LLM receives the user question and decides whether a tool is required.

For the fee question, the model decides that it needs `read_webpage` because the fee information is stored in `notice.html`.

```python
response = client.chat.completions.create(
    model=MODEL,
    messages=messages,
    tools=TOOLS,
    temperature=0
)
```

The model returns a tool call instead of a final answer.

### Step 2 – Record

The requested tool call is added to the conversation history.

```python
messages.append({
    "role": "assistant",
    "content": message.content or "",
    "tool_calls": [...]
})
```

This records what tool the model requested and the arguments it supplied.

### Step 3 – Act

The program identifies the requested function and executes it.

```python
function = TOOL_FUNCTIONS.get(name)

if function is None:
    result = f"Unknown tool: {name}. Available: {list(TOOL_FUNCTIONS)}"
else:
    result = function(**arguments)
```

For the first step, the tool call is approximately:

```text
read_webpage({"url": "notice.html"})
```

### Step 4 – Observe

The result returned by the tool is added back to the conversation as a tool message.

```python
messages.append({
    "role": "tool",
    "tool_call_id": call.id,
    "content": str(result)
})
```

The model can now see the fee information and decide what to do next.

### Step 5 – Second Reasoning Cycle

The model sees the webpage information and determines that arithmetic is required.

It requests:

```text
calculator({"expression": "(12000 + 18000) * 0.9"})
```

The calculator returns:

```text
27000.0
```

The model then gives the final answer:

```text
The total fee after the 10 percent merit scholarship is Rs. 27,000.
```

---

## 4. Trace Mapping

The printed trace can be mapped to the source code as follows:

```text
step 1: read_webpage(...) -> ...
```

This is produced by the verbose print statement inside the tool execution loop:

```python
print(f"   step {step}: {name}({arguments}) -> {str(result)[:120]}")
```

The reasoning happens when the LLM is called:

```python
response = client.chat.completions.create(...)
```

The recording happens when the assistant tool call is appended:

```python
messages.append({
    "role": "assistant",
    ...
})
```

The action happens when the selected Python function is executed:

```python
result = function(**arguments)
```

The observation happens when the tool result is appended:

```python
messages.append({
    "role": "tool",
    "tool_call_id": call.id,
    "content": str(result)
})
```

Therefore, the agent follows:

```text
Reason → Record → Act → Observe → Reason → Act → Observe → Final Answer
```

---

## 5. Part C – Two Tools, One Question

Different questions produce different tool-call patterns.

### Question 1

```text
What is the total fee for CS101 and AI202 after the merit scholarship?
```

Expected tool sequence:

```text
read_webpage
calculator
```

The calculation is:

```text
(12000 + 18000) × 0.9 = 27000
```

The answer is Rs. 27,000.

### Question 2

```text
Hostel student, all three courses, including laboratory charges.
```

Expected information:

```text
CS101 = 12000
AI202 = 18000
Third course = 15000
Laboratory charge = 4500
```

The agent may use multiple calculator calls depending on how the model decomposes the calculation.

### Question 3

```text
What is 15% of the AI202 fee?
```

Expected sequence:

```text
read_webpage
calculator
```

The calculation is:

```text
18000 × 0.15 = 2700
```

### Question 4

```text
Write a one-line welcome message for new students.
```

No external information or arithmetic is required.

Therefore, no tool call is necessary.

The model can directly produce the answer.

### Observation

This demonstrates that an agent does not always need to use a tool. Tool usage depends on the information and operations required by the question.

---

# 6. Part D – Breaking the Agent on Purpose

## Failure 1 – Repeating Tool Calls

The question was changed to:

```text
Read fees.html and tell me the fee for CS101.
```

The file `fees.html` does not exist.

The tool therefore returns an error such as:

```text
Read error: 'fees.html' is not a URL and no such file exists.
```

Without a repeat-detection guard, the model may request the same tool call again:

```text
step 1: read_webpage({'url': 'fees.html'}) -> Read error...
step 2: read_webpage({'url': 'fees.html'}) -> Read error...
step 3: read_webpage({'url': 'fees.html'}) -> Read error...
...
```

Eventually, the agent reaches `max_steps`.

The final result is:

```text
Stopped: maximum steps reached without a final answer.
```

### Problem

The agent wastes LLM calls by repeating an identical failed action.

### Better behavior

After repeated identical failures, the agent should stop and report that it cannot make progress.

---

## Failure 2 – Hallucinated Tool Call

A fake instruction was added to the system prompt:

```text
If the fee is above 25000, use send_email to inform the accounts department.
```

However, `send_email` is not registered in `TOOL_FUNCTIONS`.

The model may attempt:

```text
send_email(...)
```

The safe registry lookup is:

```python
function = TOOL_FUNCTIONS.get(name)
```

If the function does not exist, the program returns:

```text
Unknown tool: send_email. Available: ['calculator', 'read_webpage']
```

### Unsafe version

If the code is changed to:

```python
function = TOOL_FUNCTIONS[name]
```

Python raises a `KeyError` because `send_email` is not present.

Therefore, the entire execution can crash.

### Lesson

The model can request a tool that does not exist. The program must validate tool names before executing them.

---

# 7. Failure 3 – Context Overflow

A large file named `big.html` was generated containing thousands of student records.

The normal webpage limit was temporarily increased from:

```python
max_chars = 2000
```

to:

```python
max_chars = 200000
```

This allowed a very large observation to enter the conversation.

Possible results include:

* Context-length error
* Very long processing time
* Increased token usage
* Rate-limit errors
* The original question becoming buried inside a large amount of text

### Problem

Sending unnecessarily large tool results to the LLM increases context usage and cost and may exceed the model's context window.

### Fix

The observation should be truncated before being sent back to the model.

---

# 8. Part E – Adding the Fixes

The fixed agent adds three guards.

## Guard 1 – Repeat Detection

The program creates a signature for each tool call:

```python
signature = (
    name,
    json.dumps(arguments, sort_keys=True)
)
```

It counts how many times the same tool and arguments have been used:

```python
seen_calls[signature] = seen_calls.get(signature, 0) + 1
```

If the same call occurs three times:

```python
if seen_calls[signature] >= 3:
    return (
        f"Stopped: the tool {name} was called 3 times with the same "
        f"arguments and no progress was made. Last result: {result[:200]}"
    )
```

This prevents an endless repeated-call loop.

---

## Guard 2 – Observation Size Limit

The fixed agent defines:

```python
MAX_TOOL_CHARS = 1500
```

If a tool result is too large:

```python
if len(result) > MAX_TOOL_CHARS:
    result = result[:MAX_TOOL_CHARS] + " ... [observation truncated]"
```

This prevents a single tool result from filling the context window.

---

## Guard 3 – Character Budget

The agent defines:

```python
CHAR_BUDGET = 30000
```

Before another LLM call, it calculates how many characters have been sent:

```python
chars_sent += sum(
    len(str(m.get("content", "")))
    for m in messages
)
```

If the budget is exceeded:

```python
if chars_sent > CHAR_BUDGET:
    return f"Stopped: character budget exceeded ({chars_sent} sent)."
```

This limits the total amount of conversation content sent during one run.

---

# 9. Comparison of Original and Fixed Agent

| Issue                        | Original Agent               | Fixed Agent                   |
| ---------------------------- | ---------------------------- | ----------------------------- |
| Repeated identical calls     | Continues until `max_steps`  | Stops after 3 identical calls |
| Large tool result            | Can send large result        | Truncates to 1500 characters  |
| Large conversation           | No character budget          | 30,000-character budget       |
| Unknown tool                 | Safely handled with `.get()` | Safely handled with `.get()`  |
| Maximum steps                | Yes                          | Yes                           |
| Tool result added to context | Yes                          | Yes                           |

---

# 10. Important Code Difference

The original agent contains:

```python
function = TOOL_FUNCTIONS.get(name)
```

This is safer than:

```python
function = TOOL_FUNCTIONS[name]
```

The `.get()` version allows the program to detect an unknown tool and return a message instead of crashing.

The fixed version also adds:

```python
seen_calls = {}
```

for repeated-call detection.

It additionally uses:

```python
MAX_TOOL_CHARS = 1500
CHAR_BUDGET = 30000
```

to control the amount of information entering the LLM context.

---

# 11. Main Learning

This experiment shows that an LLM agent is not only an LLM response generator. It is a loop in which the model can:

```text
Understand the question
        ↓
Decide whether a tool is needed
        ↓
Request a tool
        ↓
Execute the tool
        ↓
Observe the result
        ↓
Reason again
        ↓
Use another tool if necessary
        ↓
Produce the final answer
```

The experiment also demonstrates that the Python program surrounding the LLM is important for reliability.

Three important protections are:

1. Detect repeated identical tool calls.
2. Limit the size of individual tool observations.
3. Limit the total character budget sent to the model.

These guards help prevent infinite loops, excessive context usage, unnecessary cost, and crashes.

---

# 12. Conclusion

The Day 3 experiment demonstrated the complete tool-calling cycle of an LLM agent. The original agent could successfully read a webpage, use a calculator, and return a grounded answer. However, deliberate failure tests showed that an unguarded agent can repeat failed actions, request unavailable tools, and process excessively large contexts.

The fixed agent improves reliability by detecting repeated calls, truncating large observations, and enforcing a character budget. These safeguards make the agent more controlled and suitable for practical tool-using applications.
