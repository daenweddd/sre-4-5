import logging
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from prometheus_fastapi_instrumentator import Instrumentator
from fastapi.middleware.cors import CORSMiddleware

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("user-service")

app = FastAPI(title="Tech Store User Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

customers = [
    {
        "id": 1,
        "username": "student",
        "email": "student@example.com",
        "role": "customer"
    },
    {
        "id": 2,
        "username": "admin",
        "email": "admin@techstore.com",
        "role": "admin"
    }
]


class CustomerRequest(BaseModel):
    username: str
    email: str
    role: str = "customer"


@app.get("/")
def home():
    return {
        "service": "user-service",
        "status": "running"
    }


@app.get("/users")
def get_users():
    logger.info("Customer list requested")
    return customers


@app.get("/users/{username}")
def get_user(username: str):
    for customer in customers:
        if customer["username"] == username:
            logger.info("Customer found: %s", username)
            return customer

    logger.error("Customer not found: %s", username)
    raise HTTPException(status_code=404, detail="Customer not found")


@app.post("/users")
def create_user(customer: CustomerRequest):
    new_customer = {
        "id": len(customers) + 1,
        "username": customer.username,
        "email": customer.email,
        "role": customer.role
    }

    customers.append(new_customer)

    logger.info("Customer profile created: %s", customer.username)

    return {
        "message": "Customer profile created",
        "customer": new_customer
    }


@app.get("/health")
def health():
    return {"status": "healthy"}


Instrumentator().instrument(app).expose(app)