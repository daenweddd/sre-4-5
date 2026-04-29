import logging
from fastapi import FastAPI
from pydantic import BaseModel
from prometheus_fastapi_instrumentator import Instrumentator
from fastapi.middleware.cors import CORSMiddleware

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("chat-service")

app = FastAPI(title="Tech Store Chat Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

messages = []


class MessageRequest(BaseModel):
    sender: str
    receiver: str
    message: str


@app.get("/")
def home():
    return {
        "service": "chat-service",
        "status": "running"
    }


@app.post("/messages")
def send_message(data: MessageRequest):
    new_message = {
        "id": len(messages) + 1,
        "sender": data.sender,
        "receiver": data.receiver,
        "message": data.message,
        "context": "Tech store customer support"
    }

    messages.append(new_message)

    logger.info("Support message sent from %s to %s", data.sender, data.receiver)

    return {
        "message": "Support message sent successfully",
        "data": new_message
    }


@app.get("/messages")
def get_messages():
    logger.info("Support messages requested")
    return messages


@app.get("/health")
def health():
    return {"status": "healthy"}


Instrumentator().instrument(app).expose(app)