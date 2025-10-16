# Before committing, run this. Make sure you have black, isort, pytest, autoflake, and prettier installed.
# Command for python checks is "pip install black isort autoflake pytest"
# For prettier, if you have npm, run "npm install prettier".
# Otherwise, in cmd, run: winget install OpenJS.NodeJS
#       Then open a new cmd and run: npm install --save-dev prettier
# VERY IMPORTANT WHEN INSTALLING PRETTIER RUN FROM NON-VS CODE TERMINAL OR CLOSE AND REOPEN VS CODE BETWEEN COMMANDS

import os

os.system("python -m isort . --profile black")
os.system("python -m pytest")
os.system("npx prettier --write .")
os.system("python -m black .")
print("If there is anything below this line it needs to be fixed for tests to pass")
os.system(
    "python -m autoflake . --remove-all-unused-imports --quiet --in-place -r --exclude venv --check"
)
