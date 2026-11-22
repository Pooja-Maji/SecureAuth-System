import os
import unittest
import tempfile
import jwt
from app import app, bcrypt, JWT_SECRET_KEY
from database import init_db, get_user_by_email, get_user_by_id

class SecureAuthTestCase(unittest.TestCase):
    def setUp(self):
        # Configure test database in a temporary file
        self.db_fd, self.temp_db_path = tempfile.mkstemp(suffix=".db")
        app.config["TESTING"] = True
        app.config["WTF_CSRF_ENABLED"] = False
        os.environ["DATABASE_NAME"] = self.temp_db_path

        # Initialize the test database schema
        init_db(self.temp_db_path)

        self.client = app.test_client()

    def tearDown(self):
        os.close(self.db_fd)
        if os.path.exists(self.temp_db_path):
            os.remove(self.temp_db_path)

    def test_database_initialization(self):
        """Test that database initializes properly."""
        user = get_user_by_email("nonexistent@example.com", db_path=self.temp_db_path)
        self.assertIsNone(user)

    def test_successful_registration(self):
        """Test registering a new user with valid inputs."""
        response = self.client.post("/register", data={
            "name": "Alice Smith",
            "email": "alice@example.com",
            "password": "Password123",
            "confirm_password": "Password123"
        }, follow_redirects=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Registration successful", response.data)

        # Verify user in database
        user = get_user_by_email("alice@example.com", db_path=self.temp_db_path)
        self.assertIsNotNone(user)
        self.assertEqual(user["name"], "Alice Smith")
        # Ensure password is stored as bcrypt hash, not plaintext
        self.assertNotEqual(user["password"], "Password123")
        self.assertTrue(bcrypt.check_password_hash(user["password"], "Password123"))

    def test_duplicate_email_registration(self):
        """Test that registering with an existing email fails."""
        # First registration
        self.client.post("/register", data={
            "name": "Bob Original",
            "email": "bob@example.com",
            "password": "Password123",
            "confirm_password": "Password123"
        })

        # Second registration with identical email
        response = self.client.post("/register", data={
            "name": "Bob Duplicate",
            "email": "bob@example.com",
            "password": "Password456",
            "confirm_password": "Password456"
        }, follow_redirects=True)

        self.assertIn(b"An account with this email already exists", response.data)

    def test_registration_validation_errors(self):
        """Test password mismatch, short password, and invalid email."""
        # Password mismatch
        res1 = self.client.post("/register", data={
            "name": "Charlie",
            "email": "charlie@example.com",
            "password": "Password123",
            "confirm_password": "DifferentPassword"
        })
        self.assertIn(b"Passwords do not match", res1.data)

        # Short password
        res2 = self.client.post("/register", data={
            "name": "Charlie",
            "email": "charlie@example.com",
            "password": "123",
            "confirm_password": "123"
        })
        self.assertIn(b"Password must be at least 6 characters long", res2.data)

        # Invalid email
        res3 = self.client.post("/register", data={
            "name": "Charlie",
            "email": "invalid-email-format",
            "password": "Password123",
            "confirm_password": "Password123"
        })
        self.assertIn(b"Please provide a valid email address", res3.data)

    def test_login_success_and_jwt_generation(self):
        """Test successful login and JWT cookie generation."""
        # Register user
        self.client.post("/register", data={
            "name": "Diana Prince",
            "email": "diana@example.com",
            "password": "AmazonianPassword",
            "confirm_password": "AmazonianPassword"
        })

        # Login
        response = self.client.post("/login", data={
            "email": "diana@example.com",
            "password": "AmazonianPassword"
        }, follow_redirects=False)

        self.assertEqual(response.status_code, 302)
        self.assertIn("/dashboard", response.headers["Location"])

        # Check for auth_token cookie in response headers
        cookie_header = response.headers.get("Set-Cookie", "")
        self.assertIn("auth_token=", cookie_header)
        self.assertIn("HttpOnly", cookie_header)

        # Extract token and verify JWT payload
        cookie = self.client.get_cookie("auth_token")
        self.assertIsNotNone(cookie)
        token = cookie.value
        decoded = jwt.decode(token, JWT_SECRET_KEY, algorithms=["HS256"])
        self.assertEqual(decoded["email"], "diana@example.com")
        self.assertEqual(decoded["name"], "Diana Prince")

    def test_login_invalid_credentials(self):
        """Test login with wrong password and non-existent email."""
        # Non-existent email
        res1 = self.client.post("/login", data={
            "email": "nobody@example.com",
            "password": "Password123"
        }, follow_redirects=True)
        self.assertIn(b"Invalid email or password", res1.data)

        # Register user first
        self.client.post("/register", data={
            "name": "Eva Green",
            "email": "eva@example.com",
            "password": "CorrectPassword123",
            "confirm_password": "CorrectPassword123"
        })

        # Wrong password
        res2 = self.client.post("/login", data={
            "email": "eva@example.com",
            "password": "WrongPassword999"
        }, follow_redirects=True)
        self.assertIn(b"Invalid email or password", res2.data)

    def test_dashboard_protection_unauthorized(self):
        """Test that unauthorized access to /dashboard is blocked."""
        response = self.client.get("/dashboard", follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        # Should be redirected to login page with warning
        self.assertIn(b"Please log in to access this page", response.data)
        self.assertIn(b"Welcome Back", response.data)

    def test_dashboard_with_valid_jwt(self):
        """Test authorized access to dashboard displays user details."""
        # Register and login
        self.client.post("/register", data={
            "name": "Clark Kent",
            "email": "clark@dailyplanet.com",
            "password": "KryptonPassword",
            "confirm_password": "KryptonPassword"
        })
        self.client.post("/login", data={
            "email": "clark@dailyplanet.com",
            "password": "KryptonPassword"
        })

        # Access dashboard
        response = self.client.get("/dashboard")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Welcome, Clark Kent!", response.data)
        self.assertIn(b"clark@dailyplanet.com", response.data)
        self.assertIn(b"Logout", response.data)

    def test_dashboard_with_tampered_jwt(self):
        """Test that tampered or invalid JWT is rejected."""
        self.client.set_cookie(key="auth_token", value="invalid.jwt.token.string")
        response = self.client.get("/dashboard", follow_redirects=True)
        self.assertIn(b"Invalid authentication token", response.data)

    def test_logout(self):
        """Test logout clears the token cookie and restricts subsequent dashboard access."""
        # Register and login
        self.client.post("/register", data={
            "name": "Bruce Wayne",
            "email": "bruce@wayne.com",
            "password": "BatPassword",
            "confirm_password": "BatPassword"
        })
        self.client.post("/login", data={
            "email": "bruce@wayne.com",
            "password": "BatPassword"
        })

        # Logout
        response = self.client.get("/logout", follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"You have been logged out successfully", response.data)

        # Subsequent dashboard access must fail
        dash_response = self.client.get("/dashboard", follow_redirects=True)
        self.assertIn(b"Please log in to access this page", dash_response.data)

if __name__ == "__main__":
    unittest.main()
