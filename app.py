import os
import re
import datetime
from functools import wraps
from dotenv import load_dotenv
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    make_response
)
from flask_bcrypt import Bcrypt
import jwt

from database import (
    init_db,
    create_user,
    get_user_by_email,
    get_user_by_id
)

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)

# Application Configuration
app.config["SECRET_KEY"] = os.environ.get(
    "SECRET_KEY", "default-flask-secret-key-change-in-production"
)
JWT_SECRET_KEY = os.environ.get(
    "JWT_SECRET_KEY", "default-jwt-secret-key-change-in-production"
)
JWT_EXPIRATION_HOURS = int(os.environ.get("JWT_EXPIRATION_HOURS", 2))

bcrypt = Bcrypt(app)

# Initialize SQLite database and users table automatically on app startup
with app.app_context():
    init_db()


def validate_email_format(email: str) -> bool:
    """Validate email address format using standard regex."""
    email_regex = r"^[\w\.-]+@[\w\.-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(email_regex, email))


def generate_jwt_token(user) -> str:
    """
    Generate a signed JWT token containing user details and expiration time.
    """
    now = datetime.datetime.now(datetime.timezone.utc)
    expiration = now + datetime.timedelta(hours=JWT_EXPIRATION_HOURS)

    payload = {
        "user_id": user["id"],
        "email": user["email"],
        "name": user["name"],
        "iat": now,
        "exp": expiration
    }

    token = jwt.encode(payload, JWT_SECRET_KEY, algorithm="HS256")
    return token


def get_current_user_from_request():
    """
    Inspect the request for a valid JWT token in cookies or Authorization header.
    Returns the user sqlite3.Row if valid, otherwise None.
    """
    token = request.cookies.get("auth_token")

    if not token and "Authorization" in request.headers:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header.split(" ", 1)[1]

    if not token:
        return None

    try:
        data = jwt.decode(token, JWT_SECRET_KEY, algorithms=["HS256"])
        user = get_user_by_id(data.get("user_id"))
        return user
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError, Exception):
        return None


def token_required(f):
    """
    Decorator to protect routes requiring JWT authentication.
    Checks HttpOnly cookie 'auth_token' or 'Authorization: Bearer <token>' header.
    Redirects unauthorized requests to the login page.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.cookies.get("auth_token")

        if not token and "Authorization" in request.headers:
            auth_header = request.headers.get("Authorization", "")
            if auth_header.startswith("Bearer "):
                token = auth_header.split(" ", 1)[1]

        if not token:
            flash("Please log in to access this page.", "warning")
            return redirect(url_for("login"))

        try:
            payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=["HS256"])
            current_user = get_user_by_id(payload["user_id"])

            if not current_user:
                flash("User account not found. Please log in again.", "danger")
                resp = redirect(url_for("login"))
                resp.delete_cookie("auth_token")
                return resp

        except jwt.ExpiredSignatureError:
            flash("Your session has expired. Please log in again.", "warning")
            resp = redirect(url_for("login"))
            resp.delete_cookie("auth_token")
            return resp
        except (jwt.InvalidTokenError, Exception):
            flash("Invalid authentication token. Please log in again.", "danger")
            resp = redirect(url_for("login"))
            resp.delete_cookie("auth_token")
            return resp

        return f(current_user, *args, **kwargs)

    return decorated


@app.route("/")
def index():
    """
    Home route:
    Redirects to dashboard if already logged in, otherwise to login page.
    """
    user = get_current_user_from_request()
    if user:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/register", methods=["GET", "POST"])
def register():
    """
    Registration Route:
    - GET: Render registration form.
    - POST: Validate fields, ensure unique email, hash password, and store user.
    """
    # If user is already authenticated, redirect to dashboard
    if get_current_user_from_request():
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        errors = []

        # Validate name
        if not name or len(name) < 2:
            errors.append("Name must be at least 2 characters long.")

        # Validate email
        if not email or not validate_email_format(email):
            errors.append("Please provide a valid email address.")

        # Validate password
        if not password or len(password) < 6:
            errors.append("Password must be at least 6 characters long.")

        # Validate confirm password
        if password != confirm_password:
            errors.append("Passwords do not match.")

        # Check for existing email in database
        if not errors:
            existing_user = get_user_by_email(email)
            if existing_user:
                errors.append("An account with this email already exists.")

        if errors:
            for error in errors:
                flash(error, "danger")
            return render_template(
                "register.html",
                name=name,
                email=email
            ), 400

        # Hash password securely using Flask-Bcrypt
        hashed_password = bcrypt.generate_password_hash(password).decode("utf-8")

        # Save to database
        user_id = create_user(name, email, hashed_password)
        if user_id:
            flash("Registration successful! You can now log in.", "success")
            return redirect(url_for("login"))
        else:
            flash("An error occurred while creating your account. Please try again.", "danger")
            return render_template("register.html", name=name, email=email), 500

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    """
    Login Route:
    - GET: Render login form.
    - POST: Validate credentials, verify bcrypt hash, issue JWT in HttpOnly cookie.
    """
    # If user is already authenticated, redirect to dashboard
    if get_current_user_from_request():
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not email or not password:
            flash("Please enter both email and password.", "danger")
            return render_template("login.html", email=email), 400

        user = get_user_by_email(email)

        # Verify password securely using bcrypt
        if user and bcrypt.check_password_hash(user["password"], password):
            # Generate JWT token
            token = generate_jwt_token(user)

            flash(f"Welcome back, {user['name']}!", "success")
            response = make_response(redirect(url_for("dashboard")))

            # Set JWT token in an HttpOnly secure cookie
            # max_age in seconds: JWT_EXPIRATION_HOURS * 3600
            max_age = JWT_EXPIRATION_HOURS * 3600
            response.set_cookie(
                "auth_token",
                token,
                max_age=max_age,
                httponly=True,
                samesite="Lax"
            )
            return response
        else:
            flash("Invalid email or password. Please try again.", "danger")
            return render_template("login.html", email=email), 401

    return render_template("login.html")


@app.route("/dashboard")
@token_required
def dashboard(current_user):
    """
    Dashboard Route:
    Protected by @token_required. Displays user name, email, and welcome message.
    """
    return render_template("dashboard.html", user=current_user)


@app.route("/logout")
def logout():
    """
    Logout Route:
    Clears the JWT auth_token cookie and redirects to login page.
    """
    response = make_response(redirect(url_for("login")))
    response.delete_cookie("auth_token")
    flash("You have been logged out successfully.", "info")
    return response


if __name__ == "__main__":
    app.run(debug=True, port=5000)
