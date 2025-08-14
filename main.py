import sys
from db import init_db
from auth import register_user, authenticate_user, get_user_info_and_score, update_credit_info, get_credit_advice

def main_menu():
    while True:
        print("\nWelcome to the Credit Scoring CLI App!")
        print("1) Login")
        print("2) Register")
        print("3) Exit")
        choice = input("Enter your choice: ").strip()
        if choice == "1":
            username = input("Username: ").strip()
            if not username:
                    print("Username cannot be empty.")
                    continue
            password = input("Password: ").strip()
            if authenticate_user(username, password):
                print(f"\nLogin successful! Welcome, {username}.")
                user_menu(username)
            else:
                print("Login failed: Invalid username or password.")
        elif choice == "2":
            while True:
                username = input("Username: ").strip()
                if not username:
                    print("Username cannot be empty.")
                    continue
                password = input("Password: ").strip()
                confirm = input("Confirm Password: ").strip()
                if password != confirm:
                    print("Passwords do not match.")
                    continue
                name = input("Name (optional): ").strip() or None
                email = input("Email (optional): ").strip() or None
                success = register_user(username, password, name, email)
                if success:
                    print("Registration successful!")
                    break
                else:
                    print("Error: That username is already registered. Please try a different username.")
                    retry = input("Try again? (y/n): ").strip().lower()
                    if retry != 'y':
                        break
        elif choice == "3":
            print("Goodbye!")
            sys.exit(0)
        else:
            print("Invalid choice. Please try again.")

def user_menu(username):
    while True:
        print(f"\n--- Main Menu for {username} ---")
        print("1) View Dashboard")
        print("2) Update Information")
        print("3) View Advice")
        print("4) Logout")
        choice = input("Enter your choice: ").strip()
        if choice == "1":
            user_data = get_user_info_and_score(username)
            if not user_data:
                print("User not found.")
                continue
            print(f"\n--- Dashboard for {user_data['username']} ---")
            print(f"Name: {user_data['name']}")
            print(f"Email: {user_data['email']}")
            credit_info = user_data['credit_info']
            if credit_info:
                age, income, debts, missed_payments, employment_length_years, credit_history_years, credit_score, last_updated = credit_info
                print(f"Age: {age}")
                print(f"Income: R{income}")
                print(f"Debts: R{debts}")
                print(f"Missed Payments: {missed_payments}")
                print(f"Employment Length (years): {employment_length_years}")
                print(f"Credit History (years): {credit_history_years}")
                print(f"Credit Score: {credit_score}")
                print(f"Last Updated: {last_updated}")
            else:
                print("No credit info found. Please update your information.")
        elif choice == "2":
            try:
                age = int(input("Age: ").strip())
                income = float(input("Income (R): ").strip())
                debts = float(input("Debts (R): ").strip())
                missed_payments = int(input("Missed Payments: ").strip())
                employment_length_years = int(input("Employment Length (years): ").strip())
                credit_history_years = int(input("Credit History Length (years): ").strip())
            except ValueError:
                print("Invalid input. Please enter valid numbers for all fields.")
                continue
            success = update_credit_info(username, age, income, debts, missed_payments, employment_length_years, credit_history_years)
            if success:
                print("Financial information updated and credit score recalculated.")
            else:
                print("Failed to update information. User not found.")
        elif choice == "3":
            result = get_credit_advice(username)
            if not result:
                print("No credit info found. Please update your information first.")
                continue
            print(f"Your current credit score: {result['credit_score']}")
            print("Advice:")
            for tip in result['advice']:
                print(f"- {tip}")
        elif choice == "4":
            print("Logging out...")
            break
        else:
            print("Invalid choice. Please try again.")

def main():
    init_db()
    main_menu()

if __name__ == "__main__":
    main()