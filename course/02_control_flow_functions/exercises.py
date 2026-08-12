"""
Module 02 Exercises — Control Flow & Functions
Fill in each function. Run this file to check your answers.
"""


def exercise_1_grade(score):
    """
    Return "A" if score >= 90, "B" if score >= 75, "C" if score >= 60,
    else "F".
    """
    # TODO: implement
    if score >= 90:
        return "A"
    elif score >= 75:
        return "B"
    elif score >= 60:
        return "C"
    else:
        return "F"


def exercise_2_sum_even(numbers):
    """
    Given a list of ints, return the sum of only the even numbers,
    using a for loop.
    """
    # TODO: implement
    sum = 0
    for number in numbers:
        if number % 2 == 0:
            sum += number
    return sum


def exercise_3_countdown(n):
    """
    Return a list counting down from n to 1 (inclusive), using a while loop.
    e.g. countdown(3) -> [3, 2, 1]
    """
    # TODO: implement
    countdown_list = []
    while n >= 1:
        countdown_list.append(n)
        n -= 1
    return countdown_list


def exercise_4_make_prompt(role, task, tone="neutral"):
    """
    A function with a default argument.
    Return: "You are a {role}. Please {task}. Respond in a {tone} tone."
    """
    # TODO: implement
    return f"You are a {role}. Please {task}. Respond in a {tone} tone."


def exercise_5_call_with_retry(fn, max_attempts=3):
    """
    Call fn() up to max_attempts times. If it raises an exception,
    try again. If it succeeds, return its result immediately.
    If all attempts fail, re-raise the last exception.
    """
    # TODO: implement
    for i in range(max_attempts):
        try:
            return fn()
        except Exception as e:
            if i == max_attempts - 1:
                raise e
            continue


def exercise_6_double_odds(numbers):
    """
    Given a list of ints, return a new list where every odd number
    is doubled and every even number is left unchanged.
    Use map() and/or filter() and a lambda — no for loop.
    """
    # TODO: implement
    return list(map(lambda x: x * 2 if x % 2 == 1 else x, numbers))

# ---- Test harness (do not need to edit below) ----
if __name__ == "__main__":
    print(exercise_1_grade(92))
    print(exercise_2_sum_even([1, 2, 3, 4, 5, 6]))
    print(exercise_3_countdown(3))
    print(exercise_4_make_prompt("teacher", "explain recursion"))

    attempts = {"count": 0}

    def flaky():
        attempts["count"] += 1
        if attempts["count"] < 2:
            raise ValueError("simulated failure")
        return "success"

    print(exercise_5_call_with_retry(flaky))
    print(exercise_6_double_odds([1, 2, 3, 4, 5]))
