import pandas as pd
import logging
import math
import sqlite3
from db import get_connection

logging.basicConfig(level=logging.DEBUG, format="%(levelname)s: %(message)s")


def get_user_info_and_score(username: str):
    logging.debug(f"Fetching user info and score for '{username}'.")
    try:
        with get_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT id, name, email FROM users WHERE username = ?", (username,))
            user = c.fetchone()
            if not user:
                logging.debug(f"User '{username}' not found.")
                return None
            user_id, name, email = user
            c.execute(
                "SELECT age, income, debts, missed_payments, employment_length_years, credit_history_years, credit_score, last_updated "
                "FROM credit_info WHERE user_id = ? ORDER BY last_updated DESC LIMIT 1",
                (user_id,)
            )
            credit_info = c.fetchone()
        logging.debug(f"Fetched credit info for '{username}': {bool(credit_info)}.")
        return {
            'username': username,
            'name': name,
            'email': email,
            'credit_info': credit_info
        }
    except sqlite3.Error as e:
        logging.error(f"Database error during get_user_info_and_score: {e}")
        raise


"""
# First, simple credit scoring model
def calculate_credit_score(income, debts, missed_payments):
    # Simple scoring: start at 700, subtract for debts and missed payments, add for income
    score = 700
    if income:
        score += min(int(income // 1000), 100)
    if debts:
        score -= min(int(debts // 500), 200)
    if missed_payments:
        score -= missed_payments * 30 
    return max(300, min(score, 850))
"""
# Credit scoring model V2

def calculate_credit_score_v2(
    age,
    income,
    debts,
    missed_payments,
    employment_length_years,
    credit_history_years #not used yet
):
    """
    Calculates a realistic credit score based on a simulated Weight of Evidence (WoE) score
    """
    logging.debug("Calculating credit score v2.")

    for label, value in [
        ("age", age), ("income", income), ("debts", debts),
        ("missed_payments", missed_payments),
        ("employment_length_years", employment_length_years),
        ("credit_history_years", credit_history_years)
    ]:
        if value is None:
            logging.error(f"Missing value for {label}.")
            raise ValueError(f"{label} is required")
        
    # Debt-to-Income Ratio
    if income > 0:
        dti = debts / income
    else:
        dti = 1.0 # DTI = 0 if income is 0

    # simulate WoE mapping for the different credit features (maps to risk scores)

    dti_woe_map = {
        (0, 0.2): -0.85, # DTI < 20% (low risk)
        (0.2, 0.35): -0.25, # medium risk
        (0.35, 0.5): 0.45, # high risk
        (0.5, float('inf')): 1.1 # very high risk
    }

    age_woe_map = {
        (0, 24): 0.6,       # < 25 years old
        (25, 34): 0.15,
        (35, 54): -0.2,
        (55, float('inf')): -0.45 # > 55 years old (Low Risk)
    }

    missed_payments_woe_map = {
        0: -0.95,
        1: 0.5,
        2: 1.0,
        3: 1.8
    }

    employment_length_woe_map = {
        (0, 1): 0.7,
        (1, 4): 0.1,
        (4, 8): -0.3,
        (8, float('inf')): -0.65 # > 8 years
    }

    # Get WoE value for each feature 
    def get_woe(value, woe_map):
        if isinstance(list(woe_map.keys())[0], tuple): 
            for (lower, upper), woe in woe_map.items():
                if lower <= value < upper:
                    return woe
            return 0 
        else:
            return woe_map.get(value, woe_map.get(max(woe_map.keys()))) # Default to highest risk bin if value exceeds keys


    woe_sum = (
        get_woe(dti, dti_woe_map) +
        get_woe(age, age_woe_map) +
        get_woe(missed_payments, missed_payments_woe_map) +
        get_woe(employment_length_years, employment_length_woe_map)
    )

    # simulate output of a logistic regression model
    # Assume all coefficients are 1 and are absorbed into the WoE values for simplicity.
    intercept = -0.5 # pre-calculated intercept
    log_odds = intercept + woe_sum

    #  300-850 standard credit score range.
    # target a score of 600 for odds of 50:1, with 20 points doubling the odds.
    factor = 20 / math.log(2)
    offset = 600 - (factor * math.log(50))

    score = offset - (factor * log_odds)

    # keep score in 300 - 850 range
    final_score = int(max(300, min(score, 850)))

    logging.debug(f"Calculated credit score: {final_score} for user with age {age}, income {income}, debts {debts}, missed_payments {missed_payments}, employment_length_years {employment_length_years}, credit_history_years {credit_history_years}.")

    return final_score


def update_credit_info(username: str, age: int, income: float, debts: float,
                       missed_payments: int, employment_length_years: int,
                       credit_history_years: int):
    logging.debug(f"Updating credit info for '{username}'.")
    try:
        with get_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT id FROM users WHERE username = ?", (username,))
            user = c.fetchone()
            if not user:
                logging.debug(f"User '{username}' not found for update.")
                return False
            user_id = user[0]
            credit_score = calculate_credit_score_v2(age, income, debts, missed_payments, employment_length_years, credit_history_years)
            c.execute(
                "INSERT INTO credit_info (user_id, age, income, debts, missed_payments, employment_length_years, credit_history_years, credit_score, last_updated) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))",
                (user_id, age, income, debts, missed_payments, employment_length_years, credit_history_years, credit_score)
            )
            conn.commit()
        logging.debug(f"Inserted credit info for '{username}' with score {credit_score}.")
        return True
    except sqlite3.Error as e:
        logging.error(f"Database error during update_credit_info: {e}")
        raise

def get_credit_advice(username: str):
    logging.debug(f"Generating credit advice for '{username}'.")
    try:
        with get_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT id FROM users WHERE username = ?", (username,))
            user = c.fetchone()
            if not user:
                logging.debug(f"User '{username}' not found for advice.")
                return None
            user_id = user[0]
            c.execute(
                "SELECT age, income, debts, missed_payments, employment_length_years, credit_history_years, credit_score "
                "FROM credit_info WHERE user_id = ? ORDER BY last_updated DESC LIMIT 1",
                (user_id,))
            info = c.fetchone()
            if not info:
                logging.debug(f"No credit info for '{username}'.")
                return None
            age, income, debts, missed_payments, employment_length_years, credit_history_years, credit_score = info
        advice = []
        dti = debts / income if income > 0 else 1.0

        if dti >= 0.5:
            advice.append(f"Your Debt-to-Income ratio is high ({dti:.2f}). Consider reducing your debts to improve your score.")
        elif dti >= 0.35:
            advice.append(f"Your Debt-to-Income ratio is moderate ({dti:.2f}). Aim to lower it below 35% for better credit health.")
        elif dti >= 0.2:
            advice.append(f"Your Debt-to-Income ratio is acceptable ({dti:.2f}). Maintain it below 20% for optimal credit health.")
        else:
            advice.append(f"Your Debt-to-Income ratio is excellent ({dti:.2f}). Keep up the good financial habits!")

        if missed_payments >= 3:
            advice.append(f"You have {missed_payments} missed payments. This significantly impacts your credit score. Avoid missing payments in the future.")
        elif missed_payments >= 1:
            advice.append(f"You have {missed_payments} missed payment(s). Try to avoid missing payments to improve your score.")
        else:
            advice.append("You have no missed payments. Excellent! Keep it up to maintain a good credit score.")

        if age < 25:
            advice.append("You are under 25. Building a good credit history now will improve your credit score and benefit you in the long run.")

        if employment_length_years < 1:
            advice.append("Building longer employment history (1+ years) will improve your creditworthiness.")
        elif employment_length_years < 4:
            advice.append("Continuing stable employment (4+ years) will further boost your credit profile.")
        elif employment_length_years >= 8:
            advice.append("Your long employment history positively impacts your credit score.")


        logging.debug(f"Advice generated for '{username}'.")
        return {
            'credit_score': credit_score,
            'advice': advice
        }
    except sqlite3.Error as e:
        logging.error(f"Database error during get_credit_advice: {e}")
        raise


#### Pandas summaries

def user_credit_history_df(username: str):
    """
    Return a Pandas DataFrame of the user's credit history with useful derived columns.
    """
    logging.debug(f"Loading credit history (Pandas) for '{username}'.")
    with get_connection() as conn:
        df = pd.read_sql_query(
            """
            SELECT ci.last_updated,
                   ci.age, ci.income, ci.debts, ci.missed_payments,
                   ci.employment_length_years, ci.credit_history_years,
                   ci.credit_score
            FROM credit_info AS ci
            JOIN users AS u ON u.id = ci.user_id
            WHERE u.username = ?
            ORDER BY ci.last_updated
            """,
            conn,
            params=(username,)
        )

    if df.empty:
        logging.debug(f"No credit history found for '{username}'.")
        return df

    # Basic cleaning/derived metrics
    df["last_updated"] = pd.to_datetime(df["last_updated"], errors="coerce")
    df["dti"] = (df["debts"] / df["income"]).where(df["income"] > 0, 1.0).clip(0, 10)
    df["score_change"] = df["credit_score"].diff().fillna(0)
    df["score_3pt_ma"] = df["credit_score"].rolling(window=3, min_periods=1).mean().round()

    logging.debug(f"Loaded {len(df)} rows for '{username}'.")
    return df


def user_summary_stats(username: str):
    """
    Compute simple numeric summaries with Pandas and return a dict ready to print/log.
    """
    df = user_credit_history_df(username)
    if df.empty:
        return {"message": "No credit history yet."}

    stats = {
        "observations": int(len(df)),
        "current_score": int(df["credit_score"].iloc[-1]),
        "best_score": int(df["credit_score"].max()),
        "worst_score": int(df["credit_score"].min()),
        "avg_score": float(df["credit_score"].mean()),
        "score_std": float(df["credit_score"].std(ddof=0)),
        "avg_dti": float(df["dti"].mean()),
        "last_updated": (
            df["last_updated"].max().isoformat()
            if df["last_updated"].notna().any()
            else None
        ),
    }
    return stats


def export_user_history_csv(username: str, path: str = None):
    """
    export the panda DB summary as a csv file
    """
    import os
    df = user_credit_history_df(username)
    if df.empty:
        return None
    if path is None:
        safe_user = "".join(ch for ch in username if ch.isalnum() or ch in ("-", "_"))
        path = f"{safe_user}_credit_history.csv"
    df.to_csv(path, index=False)
    return os.path.abspath(path)