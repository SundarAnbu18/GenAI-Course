"""
Module 02 Solutions — Control Flow & Functions
"""


def exercise_1_grade(score):
    if score >= 90:
        return "A"
    elif score >= 75:
        return "B"
    elif score >= 60:
        return "C"
    else:
        return "F"


def exercise_2_sum_even(numbers):
    total = 0
    for n in numbers:
        if n % 2 == 0:
            total += n
    return total


def exercise_3_countdown(n):
    result = []
    while n >= 1:
        result.append(n)
        n -= 1
    return result


def exercise_4_make_prompt(role, task, tone="neutral"):
    return f"You are a {role}. Please {task}. Respond in a {tone} tone."


def exercise_5_call_with_retry(fn, max_attempts=3):
    last_error = None
    for attempt in range(1, max_attempts + 1):
        try:
            return fn()
        except Exception as e:
            last_error = e
    raise last_error


def exercise_6_double_odds(numbers):
    return list(map(lambda n: n * 2 if n % 2 != 0 else n, numbers))


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
