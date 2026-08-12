"""Task 5 — the 10 evaluation questions."""

QUESTIONS = [
    # --- 5 factual ---
    {"kind": "factual", "question": "How many casual leave days do I get per year?",
     "expected": "12 days"},
    {"kind": "factual", "question": "How far back can I restore a file with CloudSync?",
     "expected": "180 days; 365 on Business as a paid add-on"},
    {"kind": "factual", "question": "What HTTP status code is returned for an invalid API key?",
     "expected": "401"},
    {"kind": "factual", "question": "How many days of paternity leave are provided?",
     "expected": "15 days, within 6 months of birth or adoption"},
    {"kind": "factual", "question": "What is the default value of the hours parameter on the hourly forecast endpoint?",
     "expected": "24"},

    # --- 3 reworded: near-zero vocabulary overlap with the source ---
    {"kind": "reworded", "question": "I want to spend less each month — can I move to a smaller plan?",
     "expected": "Yes; downgrades take effect next billing cycle"},
    {"kind": "reworded", "question": "My child is due next month, how much time off can I take?",
     "expected": "15 days paternity leave"},
    {"kind": "reworded", "question": "How do I prove who I am to the weather service?",
     "expected": "API key in the X-API-Key header"},

    # --- 2 out-of-scope: must refuse ---
    {"kind": "out_of_scope", "question": "What is the company WiFi password?",
     "expected": "I don't know based on the provided documents."},
    {"kind": "out_of_scope", "question": "Does CloudSync integrate with Salesforce?",
     "expected": "I don't know based on the provided documents."},
]