# Secure Authentication System

A beginner-friendly, secure, and production-ready **User Authentication System** built with **Python**, **Flask**, **SQLite**, **Flask-Bcrypt**, **PyJWT**, and **Bootstrap 5**.

Developed as an internship project demonstrating best practices in web application security, secure password storage, and stateless token-based authentication.

---

## 📌 Features

1. **User Registration**
   - Fields: Name, Email, Password, and Confirm Password.
   - Robust input validation (name length, valid email syntax, minimum password length).
   - Passwords securely hashed with **Flask-Bcrypt** (salted Blowfish hash) before saving.
   - Duplicate email registration prevention with friendly error feedback.

2. **User Login**
   - Secure login via email and password.
   - Constant-time password verification using bcrypt to prevent timing attacks.
   - Generates a signed **JSON Web Token (JWT)** upon successful authentication.
   - Issues the JWT in an **HttpOnly**, **SameSite=Lax** cookie to protect against Cross-Site Scripting (XSS) and CSRF attacks.
   - User-friendly error messages for invalid credentials.

3. **User Dashboard (Protected Route)**
   - Protected by a custom `@token_required` decorator that decodes and verifies the JWT.
   - Displays logged-in user profile: User ID, Name, Email, and Account Created timestamp.
   - Welcoming status card and security summary.
   - Quick **Logout** button that securely destroys the authentication cookie.
   - Automatically prevents unauthorized or expired users from accessing protected pages.

4. **Database & Storage**
   - Lightweight, zero-configuration **SQLite** database (`auth_system.db`).
   - Automatically initializes the database and creates the `users` table on first run.
   - Uses parameterized SQL queries to protect against SQL Injection.

5. **Clean & Responsive UI**
   - Styled using modern **Bootstrap 5**, **Bootstrap Icons**, and custom CSS.
   - Responsive design optimized for mobile, tablet, and desktop screens.
   - Includes real-time password visibility toggles and flash message alerts.

---

## 📁 Project Structure

```
SecureAuth-System/
│
├── app.py                 # Main Flask application, routes, and JWT decorator
├── database.py            # SQLite database initialization and query helpers
├── test_app.py            # Automated test suite (10 test cases)
├── requirements.txt       # Python dependencies
├── .env                   # Environment variables (JWT & Flask secrets)
├── .env.example           # Example template for environment variables
├── README.md              # Documentation and setup instructions
│
├── static/
│   └── css/
│       └── style.css      # Custom styling, modern cards, and badges
│
└── templates/
    ├── base.html          # Shared layout, navbar, and flash message container
    ├── register.html      # Registration form template
    ├── login.html         # Login form template
    └── dashboard.html     # User dashboard template
```

---

## ⚙️ Technologies Used

| Technology | Purpose |
|------------|---------|
| **Python 3.10+** | Programming language |
| **Flask (3.1.3)** | Lightweight WSGI web application framework |
| **SQLite3** | Embedded relational database management system |
| **Flask-Bcrypt (1.0.1)** | Secure password hashing using the Blowfish cipher |
| **PyJWT (2.15.1)** | JSON Web Token encoding, decoding, and cryptographic signing |
| **python-dotenv (1.2.4)** | Loading configuration and secrets from `.env` |
| **Bootstrap 5.3 & Icons** | Responsive UI components and iconography |

---

## 🚀 Getting Started

Follow these steps to set up and run the application locally.

### 1. Prerequisites
Ensure you have **Python 3.10** or higher and `pip` installed:
```bash
python --version
pip --version
```

### 2. Navigate to Project Directory
```bash
cd SecureAuth-System
```

### 3. (Optional but Recommended) Create a Virtual Environment
```bash
# On Windows
python -m venv venv
venv\Scripts\activate

# On macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### 4. Install Dependencies
```bash
pip install -r requirements.txt
```

### 5. Configure Environment Variables
A `.env` file is already provided. If needed, you can customize your secret keys:
```ini
# Flask Secret Key
SECRET_KEY=super-secret-flask-session-key-change-this-in-production

# JWT Configuration
JWT_SECRET_KEY=super-secret-jwt-key-for-token-signing-change-this-in-production
JWT_EXPIRATION_HOURS=2

# SQLite Database File
DATABASE_NAME=auth_system.db
```

### 6. Run the Application
```bash
python app.py
```

The server will start and you will see output similar to:
```
 * Serving Flask app 'app'
 * Debug mode: on
 * Running on http://127.0.0.1:5000
```

Open your web browser and navigate to:
[http://127.0.0.1:5000](http://127.0.0.1:5000)

---

## 🧪 Running Automated Tests

A comprehensive test suite is included in `test_app.py` covering all core functionalities:
- Database schema initialization
- Successful user registration & bcrypt hashing
- Duplicate email prevention
- Input validation (short passwords, invalid email format, mismatched passwords)
- Login authentication & JWT cookie issuance
- Invalid credential rejection
- Route protection for unauthorized users
- Route access for authorized users with valid JWT
- Rejection of tampered or corrupted JWT tokens
- Logout and cookie invalidation

Run the tests using Python's built-in `unittest`:
```bash
python -m unittest test_app.py
```

**Test Output:**
```
..........
----------------------------------------------------------------------
Ran 10 tests in 4.923s

OK
```

---

## 🔒 Security Concepts Explained

### 1. Why Bcrypt for Passwords?
Standard cryptographic hashes (like MD5 or SHA-256) are fast to calculate, making them vulnerable to brute-force attacks and GPU rainbow table lookups. **Bcrypt** incorporates:
- **Automatic Salt Generation**: Prevents rainbow table attacks by ensuring identical passwords yield distinct hashes.
- **Configurable Work Factor**: Computationally expensive by design, making offline brute-force cracking unfeasible.

### 2. How JWT Works in this Application
When a user logs in with valid credentials:
1. The server creates a payload containing the user's ID, email, name, issuance time (`iat`), and expiration time (`exp`).
2. The payload is signed with the `JWT_SECRET_KEY` using the HMAC-SHA256 (`HS256`) algorithm.
3. The token is sent to the browser via an **HttpOnly cookie**:
   - `HttpOnly`: Prevents client-side JavaScript (`document.cookie`) from reading the token, neutralizing XSS attacks.
   - `SameSite=Lax`: Defends against Cross-Site Request Forgery (CSRF).
4. On subsequent requests to `/dashboard`, the `@token_required` decorator extracts and verifies the token's cryptographic signature and expiration.

### 3. Protection Against SQL Injection
All queries in `database.py` use SQLite parameterized queries with placeholders (`?`):
```python
cursor.execute("SELECT * FROM users WHERE LOWER(email) = ?", (email.strip().lower(),))
```
This guarantees user input is treated strictly as data and never executed as SQL code.

---

