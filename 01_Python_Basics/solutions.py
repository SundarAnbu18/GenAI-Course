"""
Module 01 Solutions — Python Basics
"""


def exercise_1_variables():
    name = "Ada"
    age = 28
    knows_python = False
    return (name, age, knows_python)


def exercise_2_string_ops(sentence):
    word_count = len(sentence.split())
    uppercase_version = sentence.upper()
    reversed_string = sentence[::-1]
    return (word_count, uppercase_version, reversed_string)


def exercise_3_prompt_builder(role, task):
    return f"You are a {role}. Please {task}."


def exercise_4_temperature_convert(celsius):
    return celsius * 9 / 5 + 32


def exercise_5_type_juggling(value_str):
    float_value = float(value_str)
    int_value = int(float_value)
    return (int_value, float_value)


if __name__ == "__main__":
    print(exercise_1_variables())
    print(exercise_2_string_ops("Large language models are powerful tools"))
    print(exercise_3_prompt_builder("helpful assistant", "summarize this article"))
    print(exercise_4_temperature_convert(100))
    print(exercise_5_type_juggling("3.14"))
