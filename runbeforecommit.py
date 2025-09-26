# Before committing, run this. Make sure you have black, isort, pytest, and autoflake installed.
# Command is "pip install black isort autoflake pytest"
import os

os.system("python -m isort . --profile black")
os.system("python -m pytest")
os.system("python -m black .")
print("If there is anything below this line it needs to be fixed for tests to pass")
os.system(
    "python -m autoflake . --remove-all-unused-imports --quiet --in-place -r --exclude venv --check"
)
