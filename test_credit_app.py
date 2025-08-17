import unittest
import sqlite3
import tempfile
import shutil
from unittest.mock import patch, MagicMock
from pathlib import Path

# Import the modules to test
import auth
import credit_info
import db

class TestCreditApp(unittest.TestCase):
    """Unit tests for the credit scoring application."""
    
    def setUp(self):
        """Set up test environment before each test."""
        # Create a temporary directory for test database
        self.test_dir = tempfile.mkdtemp()
        self.test_db_path = Path(self.test_dir) / "test_credit_score.db"
        
        # Patch the DB_PATH to use our test database
        self.db_patcher = patch.object(db, 'DB_PATH', self.test_db_path)
        self.db_patcher.start()
        
        # init test db
        db.init_db()
    
    def tearDown(self):
        """Clean up after each test."""
        self.db_patcher.stop()
        # Remove temporary test directory
        shutil.rmtree(self.test_dir)

class TestAuthFunctions(TestCreditApp):
    """Test authentication and user management functions."""
    
    def test_hash_password(self):
        """Test password hashing functionality."""
        password = "test123"
        hashed = auth.hash_password(password)
        
        # Check that hash is not empty and is different from original
        self.assertIsNotNone(hashed)
        self.assertNotEqual(password, hashed)
        
        # Check that same password produces same hash
        hashed2 = auth.hash_password(password)
        self.assertEqual(hashed, hashed2)
        
        # Check that different passwords produce different hashes
        different_password = "different123"
        different_hash = auth.hash_password(different_password)
        self.assertNotEqual(hashed, different_hash)
    
    def test_register_user_success(self):
        """Test successful user registration."""
        result = auth.register_user("testuser", "password123", "Test User", "test@example.com")
        self.assertTrue(result)
        
        # Verify user was actually created in database
        with db.get_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT username, name, email FROM users WHERE username = ?", ("testuser",))
            user = c.fetchone()
            self.assertIsNotNone(user)
            self.assertEqual(user[0], "testuser")
            self.assertEqual(user[1], "Test User")
            self.assertEqual(user[2], "test@example.com")
    
    def test_register_user_duplicate_username(self):
        """Test registration with duplicate username fails."""
        # Register first user
        auth.register_user("testuser", "password123")
        
        # Try to register with same username
        result = auth.register_user("testuser", "different_password")
        self.assertFalse(result)
    
    def test_register_user_optional_fields(self):
        """Test user registration with optional fields as None."""
        result = auth.register_user("testuser2", "password123")
        self.assertTrue(result)
        
        # Verify user was created with None values for optional fields
        with db.get_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT name, email FROM users WHERE username = ?", ("testuser2",))
            user = c.fetchone()
            self.assertIsNotNone(user)
            self.assertIsNone(user[0])  # name should be None
            self.assertIsNone(user[1])  # email should be None
    
    def test_authenticate_user_success(self):
        """Test successful user authentication."""
        # Register a user first
        auth.register_user("testuser", "password123")
        
        # Test authentication
        result = auth.authenticate_user("testuser", "password123")
        self.assertTrue(result)
    
    def test_authenticate_user_wrong_password(self):
        """Test authentication with wrong password fails."""
        # Register a user first
        auth.register_user("testuser", "password123")
        
        # Test authentication with wrong password
        result = auth.authenticate_user("testuser", "wrong_password")
        self.assertFalse(result)
    
    def test_authenticate_user_nonexistent(self):
        """Test authentication with non-existent user fails."""
        result = auth.authenticate_user("nonexistent", "password123")
        self.assertFalse(result)

class TestCreditScoring(TestCreditApp):
    """Test credit scoring functionality."""
    
    def test_calculate_credit_score_v2_basic(self):
        """Test basic credit score calculation."""
        # Test with good credit profile
        score = credit_info.calculate_credit_score_v2(
            age=35,
            income=60000,
            debts=10000,
            missed_payments=0,
            employment_length_years=5,
            credit_history_years=10
        )
        
        # Score should be within valid range
        self.assertGreaterEqual(score, 300)
        self.assertLessEqual(score, 850)
        self.assertIsInstance(score, int)
    
    def test_calculate_credit_score_v2_edge_cases(self):
        """Test credit score calculation with edge cases."""
        # Test with zero income (high risk)
        score_zero_income = credit_info.calculate_credit_score_v2(
            age=25,
            income=0,
            debts=5000,
            missed_payments=2,
            employment_length_years=0,
            credit_history_years=1
        )
        
        # Should still be in valid range but likely low
        self.assertGreaterEqual(score_zero_income, 300)
        self.assertLessEqual(score_zero_income, 850)
        
        # Test with very high income and low debt (good profile)
        score_good_profile = credit_info.calculate_credit_score_v2(
            age=45,
            income=150000,
            debts=5000,
            missed_payments=0,
            employment_length_years=15,
            credit_history_years=20
        )
        
        # Good profile should have higher score than bad profile
        self.assertGreater(score_good_profile, score_zero_income)
    
    def test_calculate_credit_score_v2_missed_payments_impact(self):
        """Test that missed payments negatively impact credit score."""
        base_params = {
            'age': 30,
            'income': 50000,
            'debts': 15000,
            'employment_length_years': 3,
            'credit_history_years': 5
        }
        
        score_no_missed = credit_info.calculate_credit_score_v2(**base_params, missed_payments=0)
        score_one_missed = credit_info.calculate_credit_score_v2(**base_params, missed_payments=1)
        score_multiple_missed = credit_info.calculate_credit_score_v2(**base_params, missed_payments=3)
        
        # More missed payments should result in lower scores
        self.assertGreater(score_no_missed, score_one_missed)
        self.assertGreater(score_one_missed, score_multiple_missed)
    
    def test_calculate_credit_score_v2_dti_impact(self):
        """Test that debt-to-income ratio impacts credit score."""
        base_params = {
            'age': 30,
            'missed_payments': 0,
            'employment_length_years': 3,
            'credit_history_years': 5
        }
        
        # Low DTI (good)
        score_low_dti = credit_info.calculate_credit_score_v2(
            **base_params, income=60000, debts=6000  # 10% DTI
        )
        
        # High DTI (bad)
        score_high_dti = credit_info.calculate_credit_score_v2(
            **base_params, income=60000, debts=36000  # 60% DTI
        )
        
        # Lower DTI should result in higher score
        self.assertGreater(score_low_dti, score_high_dti)

class TestCreditInfoManagement(TestCreditApp):
    """Test credit information management functions."""
    
    def setUp(self):
        """Set up test user for credit info tests."""
        super().setUp()
        # Create a test user
        auth.register_user("testuser", "password123", "Test User", "test@example.com")
    
    def test_update_credit_info_success(self):
        """Test successful credit info update."""
        result = credit_info.update_credit_info(
            username="testuser",
            age=30,
            income=50000,
            debts=15000,
            missed_payments=1,
            employment_length_years=5,
            credit_history_years=8
        )
        
        self.assertTrue(result)
        
        # Verify data was stored correctly
        user_data = credit_info.get_user_info_and_score("testuser")
        self.assertIsNotNone(user_data)
        self.assertIsNotNone(user_data['credit_info'])

        credit_info_record = user_data['credit_info']
        self.assertEqual(credit_info_record[0], 30)  # age
        self.assertEqual(credit_info_record[1], 50000)  # income
        self.assertEqual(credit_info_record[2], 15000)  # debts
        self.assertEqual(credit_info_record[3], 1)  # missed_payments
        self.assertEqual(credit_info_record[4], 5)  # employment_length_years
        self.assertEqual(credit_info_record[5], 8)  # credit_history_years
        self.assertIsNotNone(credit_info_record[6])  # credit_score should be calculated
    
    def test_update_credit_info_nonexistent_user(self):
        """Test updating credit info for non-existent user fails."""
        result = credit_info.update_credit_info(
            username="nonexistent",
            age=30,
            income=50000,
            debts=15000,
            missed_payments=1,
            employment_length_years=5,
            credit_history_years=8
        )
        
        self.assertFalse(result)
    
    def test_get_user_info_and_score_no_credit_info(self):
        """Test getting user info when no credit info exists."""
        user_data = credit_info.get_user_info_and_score("testuser")
        
        self.assertIsNotNone(user_data)
        self.assertEqual(user_data['username'], "testuser")
        self.assertEqual(user_data['name'], "Test User")
        self.assertEqual(user_data['email'], "test@example.com")
        self.assertIsNone(user_data['credit_info'])
    
    def test_get_user_info_and_score_nonexistent_user(self):
        """Test getting info for non-existent user returns None."""
        user_data = credit_info.get_user_info_and_score("nonexistent")
        self.assertIsNone(user_data)

class TestCreditAdvice(TestCreditApp):
    """Test credit advice functionality."""
    
    def setUp(self):
        """Set up test user with credit info for advice tests."""
        super().setUp()
        # Create a test user
        auth.register_user("testuser", "password123", "Test User", "test@example.com")
    
    def test_get_credit_advice_high_debts(self):
        """Test advice for user with high debts."""
        # Update with high debt scenario
        credit_info.update_credit_info(
            username="testuser",
            age=30,
            income=30000,
            debts=25000,  # High debts
            missed_payments=0,
            employment_length_years=3,
            credit_history_years=5
        )
        
        advice = credit_info.get_credit_advice("testuser")
        self.assertIsNotNone(advice)
        self.assertIn('credit_score', advice)
        self.assertIn('advice', advice)
        
        # Should contain advice about high debts
        advice_text = ' '.join(advice['advice'])
        self.assertIn("your debt-to-income ratio is high", advice_text.lower())
    
    def test_get_credit_advice_missed_payments(self):
        """Test advice for user with missed payments."""
        # Update with missed payments
        credit_info.update_credit_info(
            username="testuser",
            age=30,
            income=50000,
            debts=10000,
            missed_payments=2,  # Missed payments
            employment_length_years=3,
            credit_history_years=5
        )
        
        advice = credit_info.get_credit_advice("testuser")
        self.assertIsNotNone(advice)
        
        # Should contain advice about missed payments
        advice_text = ' '.join(advice['advice'])
        self.assertIn("missed payment", advice_text.lower())
    
    def test_get_credit_advice_good_profile(self):
        """Test advice for user with good credit profile."""
        # Update with good credit profile
        credit_info.update_credit_info(
            username="testuser",
            age=35,
            income=80000,
            debts=5000,
            missed_payments=0,
            employment_length_years=8,
            credit_history_years=12
        )
        
        advice = credit_info.get_credit_advice("testuser")
        self.assertIsNotNone(advice)
        
        # Positive advice
        advice_text = ' '.join(advice['advice'])
        self.assertIn("excellent", advice_text.lower())
    
    def test_get_credit_advice_no_credit_info(self):
        """Test advice for user with no credit info."""
        advice = credit_info.get_credit_advice("testuser")
        self.assertIsNone(advice)
    
    def test_get_credit_advice_nonexistent_user(self):
        """Test advice for non-existent user."""
        advice = credit_info.get_credit_advice("nonexistent")
        self.assertIsNone(advice)

class TestDatabaseFunctions(TestCreditApp):
    """Test database functionality."""
    
    def test_init_db_creates_tables(self):
        """Test that init_db creates the required tables."""
        # Tables should already be created in setUp, so let's verify they exist
        with db.get_connection() as conn:
            c = conn.cursor()
            
            # Check users table exists
            c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
            self.assertIsNotNone(c.fetchone())
            
            # Check credit_info table exists
            c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='credit_info'")
            self.assertIsNotNone(c.fetchone())
    
    def test_get_connection(self):
        """Test database connection function."""
        conn = db.get_connection()
        self.assertIsNotNone(conn)
        self.assertIsInstance(conn, sqlite3.Connection)
        conn.close()

class TestIntegration(TestCreditApp):
    """Integration tests for complete workflows."""
    
    def test_complete_user_workflow(self):
        """Test complete user registration, login, and credit info workflow."""
        # Register user
        register_success = auth.register_user("integrationuser", "password123", "Integration User", "integration@test.com")
        self.assertTrue(register_success)
        
        # Authenticate user
        auth_success = auth.authenticate_user("integrationuser", "password123")
        self.assertTrue(auth_success)
        
        # Update credit info
        update_success = credit_info.update_credit_info(
            username="integrationuser",
            age=28,
            income=45000,
            debts=12000,
            missed_payments=0,
            employment_length_years=4,
            credit_history_years=6
        )
        self.assertTrue(update_success)
        
        # 4. Get user info and score
        user_data = credit_info.get_user_info_and_score("integrationuser")
        self.assertIsNotNone(user_data)
        self.assertEqual(user_data['username'], "integrationuser")
        self.assertIsNotNone(user_data['credit_info'])
        
        # 5. Get credit advice
        advice = credit_info.get_credit_advice("integrationuser")
        self.assertIsNotNone(advice)
        self.assertIn('credit_score', advice)
        self.assertIn('advice', advice)
        
        # Credit score should be reasonable for this profile
        credit_score = advice['credit_score']
        self.assertGreaterEqual(credit_score, 300)
        self.assertLessEqual(credit_score, 850)

if __name__ == '__main__':
    unittest.main(verbosity=2)
