import sqlite3
import hashlib
from db import get_connection

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def register_user(username: str, password: str, name: str = None, email: str = None) -> bool:
    password_hash = hash_password(password)
    try:
        with get_connection() as conn:
            c = conn.cursor()
            c.execute(
                "INSERT INTO users (username, password_hash, name, email) VALUES (?, ?, ?, ?)",
                (username, password_hash, name, email)
            )
            conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False

def authenticate_user(username: str, password: str) -> bool:
    password_hash = hash_password(password)
    with get_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT id FROM users WHERE username = ? AND password_hash = ?", (username, password_hash))
        result = c.fetchone()
        return result is not None

def get_user_info_and_score(username: str):
    with get_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT id, name, email FROM users WHERE username = ?", (username,))
        user = c.fetchone()
        if not user:
            return None
        user_id, name, email = user
        c.execute("SELECT age, income, debts, missed_payments, employment_length_years, credit_history_years, credit_score, last_updated FROM credit_info WHERE user_id = ? ORDER BY last_updated DESC LIMIT 1", (user_id,))
        credit_info = c.fetchone()
        return {
            'username': username,
            'name': name,
            'email': email,
            'credit_info': credit_info
        }


"""
# First, simple credit scoring model
def calculate_credit_score(income, debts, missed_payments):
    # Simple scoring: start at 700, subtract for debts and missed payments, add for income
    score = 700
    if income:
        score += min(int(income // 1000), 100)  # up to +100 for income
    if debts:
        score -= min(int(debts // 500), 200)    # up to -200 for debts
    if missed_payments:
        score -= missed_payments * 30           # -30 per missed payment
    return max(300, min(score, 850))           # Clamp between 300 and 850
"""

import math

def calculate_credit_score_v2(
    age,
    income,
    debts,
    missed_payments,
    employment_length_years,
    credit_history_years #not used yet
):
    """
    Calculates a realistic credit score based on a simulated Weight of Evidence (WoE) scorecard.

    This model mimics industry practice by:
    1. Using engineered features like Debt-to-Income (DTI) ratio.
    2. Binning variables into categories (e.g., age groups).
    3. Assigning a pre-calculated WoE value to each bin.
    4. Summing the WoE values in a logistic regression formula to get log-odds of default.
    5. Scaling the final result to a 300-850 score range.
    """
    # --- 1. Feature Engineering ---
    # Calculate Debt-to-Income Ratio. Assume 0 income means very high risk.
    if income > 0:
        dti = debts / income
    else:
        dti = 1.0 # Assign a high DTI if income is zero

    # Simulated WoE
    # In a real model, these dictionaries would be generated from historical data analysis.
    # Positive WoE = lower risk, Negative WoE = higher risk.

    dti_woe_map = {
        (0, 0.2): -0.85,      # DTI < 20% (Low Risk)
        (0.2, 0.35): -0.25,   # DTI 20%-35% (Medium Risk)
        (0.35, 0.5): 0.45,  # DTI 35%-50% (High Risk)
        (0.5, float('inf')): 1.1 # DTI > 50% (Very High Risk)
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
        (0, 1): 0.7,        # < 1 year
        (1, 4): 0.1,
        (4, 8): -0.3,
        (8, float('inf')): -0.65 # > 8 years
    }

    # --- 3. Get WoE value for each feature ---
    def get_woe(value, woe_map):
        """Helper to find the WoE value from a map."""
        if isinstance(list(woe_map.keys())[0], tuple): # Range-based map
            for (lower, upper), woe in woe_map.items():
                if lower <= value < upper:
                    return woe
            return 0 # Default if not in range
        else: # Direct lookup map
            return woe_map.get(value, woe_map.get(max(woe_map.keys()))) # Default to highest risk bin if value exceeds keys


    woe_sum = (
        get_woe(dti, dti_woe_map) +
        get_woe(age, age_woe_map) +
        get_woe(missed_payments, missed_payments_woe_map) +
        get_woe(employment_length_years, employment_length_woe_map)
    )

    # --- 4. Logistic Regression & Scaling ---
    # This simulates the output of a logistic regression model and scales it.
    # log_odds = intercept + coefficient_1*WoE_1 + ...
    # For simplicity, we assume all coefficients are 1 and are absorbed into the WoE values.
    intercept = -0.5 # A pre-calculated model intercept
    log_odds = intercept + woe_sum

    #  300-850 standard credit score range.
    # target a score of 600 for odds of 50:1, with 20 points doubling the odds.
    factor = 20 / math.log(2)  # PDO (Points to Double Odds)
    offset = 600 - (factor * math.log(50))

    score = offset - (factor * log_odds)

    # Clamp the score to the desired 300-850 range.
    return int(max(300, min(score, 850)))


def update_credit_info(username: str, age: int, income: float, debts: float, missed_payments: int, employment_length_years: int, credit_history_years: int):
    with get_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT id FROM users WHERE username = ?", (username,))
        user = c.fetchone()
        if not user:
            return False
        user_id = user[0]
        credit_score = calculate_credit_score_v2(age, income, debts, missed_payments, employment_length_years, credit_history_years)
        c.execute(
            "INSERT INTO credit_info (user_id, age, income, debts, missed_payments, employment_length_years, credit_history_years, credit_score, last_updated) VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))",
            (user_id, age, income, debts, missed_payments, employment_length_years, credit_history_years, credit_score)
        )
        conn.commit()
        return True

def get_credit_advice(username: str):
    with get_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT id FROM users WHERE username = ?", (username,))
        user = c.fetchone()
        if not user:
            return None
        user_id = user[0]
        c.execute("SELECT age, income, debts, missed_payments, employment_length_years, credit_history_years, credit_score FROM credit_info WHERE user_id = ? ORDER BY last_updated DESC LIMIT 1", (user_id,))
        info = c.fetchone()
        if not info:
            return None
        age, income, debts, missed_payments, employment_length_years, credit_history_years, credit_score = info
        advice = []
        
        dti = debts / income if income > 0 else 1.0

        # debt-to-income ratio advice
        if dti >= 0.5:
            advice.append(f"Your Debt-to-Income ratio is high ({dti:.2f}). Consider reducing your debts to improve your score.")
        elif dti >= 0.35:
            advice.append(f"Your Debt-to-Income ratio is moderate ({dti:.2f}). Aim to lower it below 35% for better credit health.")
        elif dti >= 0.2:
            advice.append(f"Your Debt-to-Income ratio is acceptable ({dti:.2f}). Maintain it below 20% for optimal credit health.")
        else:
            advice.append(f"Your Debt-to-Income ratio is excellent ({dti:.2f}). Keep up the good financial habits!")

        # Missed payments advice
        if missed_payments >= 3:
            advice.append(f"You have {missed_payments} missed payments. This significantly impacts your credit score. Avoid missing payments in the future.")
        elif missed_payments >=1:
            advice.append(f"You have {missed_payments} missed payment(s). Try to avoid missing payments to improve your score.")
        else:
            advice.append("You have no missed payments. Excellent! Keep it up to maintain a good credit score.")
        
        # age advice
        if age < 25:
            advice.append("You are under 25. Building a good credit history now will improve your credit score and benefit you in the long run.")
            
        # Employment history advice
        if employment_length_years < 1:
            advice.append("Building longer employment history (1+ years) will improve your creditworthiness.")
        elif employment_length_years < 4:
            advice.append("Continuing stable employment (4+ years) will further boost your credit profile.")
        elif employment_length_years >= 8:
            advice.append("Your long employment history positively impacts your credit score.")

        # TODO: need to implement income advice
        # TODO: need to implement top 3 things negatively impacting credit score.
        # Income
        

        if debts and debts > 0:
            advice.append(f"Your debts are high (R{debts:.2f}). Paying down debts will improve your score.")
        if missed_payments and missed_payments > 0:
            advice.append(f"You have {missed_payments} missed payment(s). Avoid missing payments to improve your score.")
        if income and income < 5000:
            advice.append(f"Your income is relatively low (R{income:.2f}). Increasing your income can help your score.")
        if not advice:
            advice.append("Your credit score looks good! Keep up the good work.")
        return {
            'credit_score': credit_score,
            'advice': advice
        }