# Credit Scoring CLI

Simple CLI application to register users, store financial / credit profile data, compute a simulated Weight of Evidence (WoE) credit score, and display improvement advice.

## Features
- User registration & authentication (auth.py)
- Store multiple credit info snapshots (credit_info table)
- Credit score calculation (WoE simulation)
- Advice to improve credit score based on DTI, missed payments, employment length, age
- Historical exports & stats (Pandas utilities)
- Automated tests (unittest)

## Tech Stack
- Python 3.9+
- SQLite (embedded)
- Pandas (history + export)
- Standard library only otherwise

## Project Structure
```
credit_score_cli/
  auth.py              # register/authenticate users
  credit_info.py       # credit data CRUD, scoring, advice, pandas helpers
  db.py                # DB path + init + connection helper
  main.py              # CLI entrypoint
  test_credit_app.py   # unit + integration tests
  requirements.txt
```

## Installation (macOS / Linux)
```bash
python3 -m venv .venv
source .venv/bin/activate
pip3 install -r requirements.txt
```

## Quick Start
```bash
python3 main.py
```
Menu flow:
1) Register (first time)
2) Login
3) Update Information (enter age, income, debts, etc.)
4) View Dashboard (shows latest snapshot + score)
5) View Advice (generated from latest snapshot)

## Example Session
```
$ python main.py
1) Login
2) Register
3) Exit
Enter your choice: 2
Username: alice
Password: ****
Confirm Password: ****
Registration successful!
```

After login choose "Update Information" then "View Advice".

## Running Tests
```bash
python3 -m unittest -v
```
Tests create a temporary SQLite file (DB_PATH is patched). No manual cleanup needed.

## Database
Tables:
- users(id, username UNIQUE, password_hash, name, email)
- credit_info(id, user_id FK, age, income, debts, missed_payments, employment_length_years, credit_history_years, credit_score, last_updated)

Each update inserts a new credit_info row.

## Credit Score Model (V2)
Score derived from:
- Debt-to-Income ratio bins (risk via WoE map)
- Age band
- Missed payments count
- Employment length band
Log-odds are aggregated, transformed to 300–850 range. (See calculate_credit_score_v2() in credit_info.py)

## Pandas Utilities
- user_credit_history_df(username)
- user_summary_stats(username)
- export_user_history_csv(username[, path])

Example:
```python3
from credit_info import user_summary_stats
print(user_summary_stats("alice"))
```

## Export History
After multiple updates:
```python3
from credit_info import export_user_history_csv
export_user_history_csv("alice")  # produces alice_credit_history.csv
```
