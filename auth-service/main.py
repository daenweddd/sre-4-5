import os
import logging
import psycopg2

from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel
from prometheus_fastapi_instrumentator import Instrumentator
from fastapi.middleware.cors import CORSMiddleware

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("auth-service")

app = FastAPI(title="Tech Store Auth Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_HOST = os.getenv("DB_HOST", "postgres")
DB_NAME = os.getenv("DB_NAME", "techstore")
DB_USER = os.getenv("DB_USER", "techuser")
DB_PASSWORD = os.getenv("DB_PASSWORD", "techpassword")

tokens = {}


class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str


class LoginRequest(BaseModel):
    username: str
    password: str


def get_connection():
    return psycopg2.connect(
        host=DB_HOST,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username VARCHAR(100) UNIQUE NOT NULL,
            email VARCHAR(150) NOT NULL,
            password VARCHAR(100) NOT NULL,
            role VARCHAR(50) DEFAULT 'customer'
        );
    """)

    conn.commit()
    cursor.close()
    conn.close()


@app.on_event("startup")
def startup():
    try:
        init_db()
        logger.info("Users table initialized")
    except Exception as error:
        logger.error("Database initialization failed: %s", str(error))


@app.get("/")
def home():
    return {
        "service": "auth-service",
        "status": "running"
    }


@app.post("/register")
def register(data: RegisterRequest):
    try:
        init_db()

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO users (username, email, password, role)
            VALUES (%s, %s, %s, %s)
            RETURNING id;
            """,
            (
                data.username,
                data.email,
                data.password,
                "customer"
            )
        )

        user_id = cursor.fetchone()[0]

        conn.commit()
        cursor.close()
        conn.close()

        logger.info("New customer registered: %s", data.username)

        return {
            "message": "Customer registered successfully",
            "user_id": user_id,
            "username": data.username,
            "email": data.email,
            "role": "customer"
        }

    except psycopg2.errors.UniqueViolation:
        logger.warning("Registration failed: user already exists")
        raise HTTPException(status_code=400, detail="User already exists")

    except Exception as error:
        logger.error("Registration failed: %s", str(error))
        raise HTTPException(
            status_code=500,
            detail=f"Registration failed: {str(error)}"
        )


@app.post("/login")
def login(data: LoginRequest):
    try:
        init_db()

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT username, email, password, role
            FROM users
            WHERE username = %s;
            """,
            (data.username,)
        )

        user = cursor.fetchone()

        cursor.close()
        conn.close()

        if user is None:
            logger.error("Login failed: customer not found")
            raise HTTPException(status_code=404, detail="Customer not found")

        username, email, password, role = user

        if password != data.password:
            logger.error("Login failed: invalid password")
            raise HTTPException(status_code=401, detail="Invalid password")

        token = f"token-{username}"
        tokens[token] = username

        logger.info("Customer logged in: %s", username)

        return {
            "message": "Login successful",
            "username": username,
            "email": email,
            "role": role,
            "token": token
        }

    except HTTPException:
        raise

    except Exception as error:
        logger.error("Login failed: %s", str(error))
        raise HTTPException(
            status_code=500,
            detail=f"Login failed: {str(error)}"
        )


@app.get("/verify")
def verify_token(authorization: str = Header(None)):
    if authorization is None:
        logger.error("Authorization header missing")
        raise HTTPException(status_code=401, detail="Missing token")

    token = authorization.replace("Bearer ", "")

    if token not in tokens:
        logger.error("Invalid token")
        raise HTTPException(status_code=401, detail="Invalid token")

    username = tokens[token]

    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT username, email, role
            FROM users
            WHERE username = %s;
            """,
            (username,)
        )

        user = cursor.fetchone()

        cursor.close()
        conn.close()

        if user is None:
            raise HTTPException(status_code=404, detail="User not found")

        return {
            "valid": True,
            "username": user[0],
            "email": user[1],
            "role": user[2]
        }

    except HTTPException:
        raise

    except Exception as error:
        logger.error("Token verification failed: %s", str(error))
        raise HTTPException(
            status_code=500,
            detail=f"Token verification failed: {str(error)}"
        )


@app.get("/users")
def get_users():
    try:
        init_db()

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, username, email, role
            FROM users
            ORDER BY id;
        """)

        rows = cursor.fetchall()

        cursor.close()
        conn.close()

        users = []

        for row in rows:
            users.append({
                "id": row[0],
                "username": row[1],
                "email": row[2],
                "role": row[3]
            })

        return users

    except Exception as error:
        logger.error("Could not retrieve users: %s", str(error))
        raise HTTPException(
            status_code=500,
            detail=f"Could not retrieve users: {str(error)}"
        )


@app.get("/health")
def health():
    try:
        conn = get_connection()
        conn.close()

        return {
            "status": "healthy",
            "database": "connected"
        }

    except Exception as error:
        logger.error("Health check failed: %s", str(error))
        raise HTTPException(
            status_code=500,
            detail=f"Database connection failed: {str(error)}"
        )


Instrumentator().instrument(app).expose(app)