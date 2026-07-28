# 02 — Control Flow & Functions

## 1. Conditionals

```python
score = 85
if score >= 90:
    grade = "A"
elif score >= 75:
    grade = "B"
else:
    grade = "C"
```

## 2. Loops

```python
for i in range(5):          # 0,1,2,3,4
    print(i)

tokens = ["Hello", "world", "!"]
for t in tokens:
    print(t)

count = 0
while count < 3:
    print("retrying...")
    count += 1
```

`break` exits a loop early, `continue` skips to the next iteration — both are
common in retry/streaming loops when calling an LLM API.

## 3. Functions

```python
def greet(name, greeting="Hello"):
    return f"{greeting}, {name}!"

print(greet("Ada"))                  # Hello, Ada!
print(greet("Ada", greeting="Hi"))   # Hi, Ada!
```

- Parameters can have defaults.
- Functions return `None` if there's no `return` statement.
- `*args` and `**kwargs` let a function accept variable numbers of arguments —
  you'll see this everywhere in LLM SDK function signatures.

```python
def call_model(prompt, *, temperature=0.7, **extra_params):
    print(prompt, temperature, extra_params)

call_model("Summarize this", max_tokens=200)
```

## 4. Lambdas & Higher-order functions

```python
square = lambda x: x * x
print(square(5))   # 25

nums = [1, 2, 3, 4]
print(list(map(lambda n: n * 2, nums)))       # [2, 4, 6, 8]
print(list(filter(lambda n: n % 2 == 0, nums)))  # [2, 4]
```

## 5. Retry pattern (a real Gen-AI-flavored example)

```python
def call_with_retry(fn, max_attempts=3):
    for attempt in range(1, max_attempts + 1):
        try:
            return fn()
        except Exception as e:
            print(f"Attempt {attempt} failed: {e}")
    raise RuntimeError("All attempts failed")
```

This exact shape (loop + try/except + function argument) is how you'd retry
a flaky LLM API call. We'll cover `try/except` properly in module 04.

Now do `exercises.py`.
