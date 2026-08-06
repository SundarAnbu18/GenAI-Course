# 01 — Python Basics

## 1. Running Python

```bash
python3 script.py       # run a file
python3                 # interactive REPL
```

## 2. Variables & Data Types

```python
name = "Ada"          # str
age = 28               # int
height = 1.65          # float
is_learning = True     # bool

print(type(name))      # <class 'str'>
```

Python is dynamically typed — no need to declare a type up front.

## 3. Numbers & Operators

```python
a, b = 7, 2
print(a + b, a - b, a * b)
print(a / b)    # 3.5   (true division, always float)
print(a // b)   # 3     (floor division)
print(a % b)    # 1     (modulo)
print(a ** b)   # 49    (power)
```

## 4. Strings

```python
s = "Generative AI"
print(s.lower())          # generative ai
# these are called pre defined functions
print(s.upper())          # GENERATIVE AI
print(s.split(" "))       # ['Generative', 'AI']
print(len(s))             # 14
print(s[0], s[-1])        # G I  (indexing)
print(s[0:11])            # Generative  (slicing)

# f-strings — you WILL use these constantly for prompt templates
model = "claude"
prompt = f"Ask {model} to summarize: {s}"
print(prompt)
```

## 5. Basic Input/Output

```python
user_input = input("Enter a topic: ")
print(f"You asked about: {user_input}")
```

## 6. Booleans & Comparisons

```python
print(5 > 3)        # True
print(5 == 5)       # True
print("a" != "b")   # True
print(True and False, True or False, not True)
```

## 7. Type Conversion

```python
x = "42"
n = int(x)          # 42
s = str(n)           # "42"
f = float("3.14")    # 3.14
```

## Key takeaway

Everything you send to and receive from an LLM API is text (strings) or
structured data built from these basic types (numbers, bools, strings inside
lists/dicts). Mastering these primitives is non-negotiable.

Now do `exercises.py`.
