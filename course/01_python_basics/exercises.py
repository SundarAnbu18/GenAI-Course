"""
Module 01 Exercises — Python Basics
Fill in each function. Run this file to check your answers.
"""


def exercise_1_variables():
    """
    Create three variables: your name (str), your age (int),
    and whether you know Python already (bool).
    Return them as a tuple: (name, age, knows_python)
    """
    # TODO: implement
    name = "John"
    age = 20
    knows_python = True
    return (name, age, knows_python)


def exercise_2_string_ops(sentence):
    """
    Given a sentence string, return a tuple of:
    (word_count, uppercase_version, reversed_string)
    """
    # TODO: implement
    word_count = len(sentence.split())
    uppercase_version = sentence.upper()
    reversed_string = sentence[::-1]
    return (word_count, uppercase_version, reversed_string)


def exercise_3_prompt_builder(role, task):
    """
    Build and return a prompt string in this exact format using an f-string:
    "You are a {role}. Please {task}."
    """
    # TODO: implement
    return f"You are a {role}. Please {task}."


def exercise_4_temperature_convert(celsius):
    """
    Convert Celsius to Fahrenheit: F = C * 9/5 + 32
    Return the result as a float.
    """
    # TODO: implement
    return f"{celsius}°C is {celsius * 9/5 + 32}°F"


def exercise_5_type_juggling(value_str):
    """
    Given a string like "3.14", convert it to a float,
    then return an int (truncated) and the original float, as a tuple:
    (int_value, float_value)
    """
    # TODO: implement
    return int(float(value_str)), float(value_str)


# ---- Test harness (do not need to edit below) ----
if __name__ == "__main__":
    print(exercise_1_variables())
    print(exercise_2_string_ops("Large language models are powerful tools"))
    print(exercise_3_prompt_builder("helpful assistant", "summarize this article"))
    print(exercise_4_temperature_convert(100))
    print(exercise_5_type_juggling("3.14"))
