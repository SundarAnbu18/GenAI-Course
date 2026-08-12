"""Path to the sample employees CSV used by lauch.py."""

from pathlib import Path

employees = str(Path(__file__).with_name("employees.csv"))
