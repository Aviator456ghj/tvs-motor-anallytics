import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.business import BusinessProfile
from app.models.engagement import ChatMessage, ChatThread
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.engagement import ChatMessageCreate, ChatMessageOut, ChatThreadOut

router = APIRouter(prefix="/chat", tags=["chat"])

# NOTE: polling-based REST chat for now. A `/ws/chat/{thread_id}` WebSocket
# endpoint is the natural upgrade (see docs/ROADMAP.md realtime section) —
# thread/message persistence here is already websocket-ready.


@router.get("/threads", response_model=list[ChatThreadOut])
def list_threads(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role == UserRole.customer:
        return db.query(ChatThread).filter(ChatThread.customer_id == user.id).all()
    if user.role == UserRole.business:
        business = db.query(BusinessProfile).filter(BusinessProfile.owner_id == user.id).first()
        if not business:
            return []
        return db.query(ChatThread).filter(ChatThread.business_id == business.id).all()
    return db.query(ChatThread).all()


@router.post("/messages", response_model=ChatMessageOut, status_code=201)
def send_message(payload: ChatMessageCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role == UserRole.customer:
        customer_id = user.id
    else:
        raise HTTPException(403, "Only customers can start a thread; businesses reply within existing threads")

    thread = db.query(ChatThread).filter(ChatThread.customer_id == customer_id, ChatThread.business_id == payload.business_id).first()
    if not thread:
        thread = ChatThread(customer_id=customer_id, business_id=payload.business_id, booking_id=payload.booking_id)
        db.add(thread)
        db.flush()

    message = ChatMessage(thread_id=thread.id, sender_id=user.id, message=payload.message)
    db.add(message)
    db.commit()
    db.refresh(message)
    return message


@router.post("/threads/{thread_id}/messages", response_model=ChatMessageOut, status_code=201)
def reply_in_thread(thread_id: uuid.UUID, message: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    thread = db.get(ChatThread, thread_id)
    if not thread:
        raise HTTPException(404, "Thread not found")
    if user.role == UserRole.business:
        business = db.query(BusinessProfile).filter(BusinessProfile.owner_id == user.id).first()
        if not business or thread.business_id != business.id:
            raise HTTPException(403, "Not authorized")
    elif user.role == UserRole.customer and thread.customer_id != user.id:
        raise HTTPException(403, "Not authorized")

    chat_message = ChatMessage(thread_id=thread.id, sender_id=user.id, message=message)
    db.add(chat_message)
    db.commit()
    db.refresh(chat_message)
    return chat_message


@router.get("/threads/{thread_id}/messages", response_model=list[ChatMessageOut])
def list_messages(thread_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    thread = db.get(ChatThread, thread_id)
    if not thread:
        raise HTTPException(404, "Thread not found")
    return db.query(ChatMessage).filter(ChatMessage.thread_id == thread_id).order_by(ChatMessage.created_at).all()
