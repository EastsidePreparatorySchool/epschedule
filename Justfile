# This is the main Justfile for the EPSchedule repo.
# To install Just, see: https://github.com/casey/just#installation 

# This causes the .env file to be read by Just.
set dotenv-load := true

# Allow for positional arguments in Just receipes.
set positional-arguments := true


default: format check test

install:
    pip install -r requirements.txt
    
format:
    #autoflake . --remove-all-unused-imports --quiet --in-place -r --exclude venv
    isort .  --profile black --skip venv
    black . --exclude venv

check:
    #autoflake . --remove-all-unused-imports --quiet --in-place -r --exclude venv --check
    isort .  --profile black --skip venv --check
    black . --exclude venv --check
    #mypy .

test PATH=".":
    pytest --ignore venv {{PATH}}

test-verbose PATH=".":
    pytest --ignore venv -vv --log-cli-level=INFO {{PATH}}

run *FLAGS:
    python main.py {{FLAGS}}

deploy:     
    gcloud app deploy --project=epschedule-v2 

update-schedules *FLAGS:
    python update.py {{FLAGS}} schedules

update-photos *FLAGS:
    python update.py {{FLAGS}} photos

update-lunches *FLAGS:
    python update.py {{FLAGS}} lunches
