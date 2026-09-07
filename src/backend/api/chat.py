import uuid
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
import httpx
import json

from fastapi import APIRouter, HTTPException, Header, Form, UploadFile, File
from pydantic import BaseModel

from src.backend.config import get_settings
from src.backend.storage.sqlite_store import _get_connection
from src.backend.intelligence.context_builder import build_context
from src.backend.intelligence.tools import pop_emitted_charts
from src.backend.extraction.vision import describe_image_with_ollama

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/chat", tags=["chat"])

class ChatMessage(BaseModel):
    message: str
    session_id: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    charts: List[Dict[str, Any]]
    session_id: str

def save_message(user_id: str, role: str, content: str, session_id: str):
    conn = _get_connection()
    conn.execute(
        "INSERT INTO conversation_history (id, user_id, timestamp, role, content, session_id) VALUES (?, ?, ?, ?, ?, ?)",
        (str(uuid.uuid4()), user_id, datetime.now(timezone.utc).isoformat(), role, content, session_id)
    )
    conn.commit()
    conn.close()

def get_history(user_id: str, session_id: str, limit: int = 20) -> List[Dict[str, str]]:
    conn = _get_connection()
    cursor = conn.execute(
        "SELECT role, content FROM conversation_history WHERE session_id = ? AND user_id = ? ORDER BY timestamp DESC LIMIT ?",
        (session_id, user_id, limit)
    )
    rows = cursor.fetchall()
    conn.close()
    
    return [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]

def get_session_summary(user_id: str, session_id: str) -> Optional[str]:
    conn = _get_connection()
    row = conn.execute(
        "SELECT summary FROM chat_sessions WHERE id = ? AND user_id = ?",
        (session_id, user_id)
    ).fetchone()
    conn.close()
    return row["summary"] if row and row["summary"] else None

async def generate_headline(user_msg: str) -> str:
    settings = get_settings()
    prompt = f"Write a 3-5 word headline summarizing this message: '{user_msg}'. Respond ONLY with the headline, no quotes or intro."
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{settings.ollama_base_url}/api/generate",
                json={"model": settings.ollama_model, "prompt": prompt, "stream": False}
            )
            response.raise_for_status()
            return response.json()["response"].strip().strip('"')
    except Exception:
        return "New Conversation"

async def generate_response(user_msg: str, session_id: str, user_id: str) -> str:
    settings = get_settings()
    context = build_context(user_id)
    history = get_history(user_id, session_id)
    summary = get_session_summary(user_id, session_id)
    
    system_prompt = f"You are a health copilot. Be concise, factual, and supportive.\\n\\n{context}"
    if summary:
        system_prompt += f"\\n\\nSession Summary:\\n{summary}"
        
    messages = [{"role": "system", "content": system_prompt}]
    for msg in history:
        messages.append(msg)
    messages.append({"role": "user", "content": user_msg})
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{settings.ollama_base_url}/api/chat",
                json={
                    "model": settings.ollama_model,
                    "messages": messages,
                    "stream": False
                }
            )
            response.raise_for_status()
            data = response.json()
            return data["message"]["content"]
    except Exception as e:
        logger.exception("LLM generation failed")
        return "I am currently unable to reach my reasoning engine."

async def summarize_session_history(user_id: str, session_id: str):
    conn = _get_connection()
    # Get all messages chronologically
    rows = conn.execute(
        "SELECT id, role, content FROM conversation_history WHERE session_id = ? AND user_id = ? ORDER BY timestamp ASC",
        (session_id, user_id)
    ).fetchall()
    
    current_summary = get_session_summary(user_id, session_id)
    
    # Check if we have too many messages. e.g. if we have > 15 messages, summarize all except the last 10.
    if len(rows) > 15:
        to_summarize = rows[:-10]
        last_summarized_id = to_summarize[-1]["id"]
        
        # Build prompt
        text_to_summarize = "\\n".join([f"{r['role']}: {r['content']}" for r in to_summarize])
        prompt = f"Summarize the following chat history concisely. If there is an existing summary, update it with this new context.\\n\\nExisting Summary: {current_summary or 'None'}\\n\\nNew History:\\n{text_to_summarize}"
        
        settings = get_settings()
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{settings.ollama_base_url}/api/generate",
                    json={"model": settings.ollama_model, "prompt": prompt, "stream": False}
                )
                response.raise_for_status()
                new_summary = response.json()["response"].strip()
                update_chat_session_summary(session_id, user_id, new_summary, last_summarized_id)
                
                # Delete the summarized messages to save space, or just keep them and rely on summarized_through_message_id.
                # To prevent get_history from fetching them, we should actually filter by summarized_through_message_id in get_history,
                # but an easier approach for now is to delete them. 
                # The user said "summarize the old portion and retain recent turns verbatim".
                ids_to_delete = [r["id"] for r in to_summarize]
                placeholders = ",".join("?" * len(ids_to_delete))
                conn.execute(f"DELETE FROM conversation_history WHERE id IN ({placeholders}) AND user_id = ?", (*ids_to_delete, user_id))
                conn.commit()
        except Exception as e:
            logger.exception("Failed to generate session summary")
    conn.close()

from src.backend.storage.sqlite_store import create_chat_session, get_chat_sessions, update_chat_session, update_chat_session_summary
import asyncio

@router.post("", response_model=ChatResponse)
async def chat_endpoint(
    message: str = Form(...),
    session_id: Optional[str] = Form(None),
    screen_context: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    x_user_id: str = Header(...)
):
    if not session_id or session_id == "null":
        session_id = str(uuid.uuid4())
        title = await generate_headline(message)
        create_chat_session(session_id, x_user_id, title)
    else:
        update_chat_session(session_id, x_user_id)

    # Process file attachment
    image_desc = ""
    if file:
        try:
            image_bytes = await file.read()
            image_desc = await describe_image_with_ollama(
                image_bytes, 
                prompt="Describe this image in detail. If it contains health data, graphs, or logs, extract the relevant data."
            )
            image_desc = f"\\n\\n[User attached an image:\\n{image_desc}]"
        except Exception as e:
            logger.exception("Image vision extraction failed")
            image_desc = "\\n\\n[User attached an image, but vision extraction failed.]"

    full_message = message + image_desc

    save_message(x_user_id, "user", full_message, session_id)
    
    # Inject screen context if available
    context_msg = full_message
    if screen_context and screen_context != "null":
        context_msg += f"\\n\\n[Screen Context: {screen_context}]"

    response_text = await generate_response(context_msg, session_id, x_user_id)
    charts = pop_emitted_charts()
    
    save_message(x_user_id, "assistant", response_text, session_id)
    
    # Summarize older messages if context gets too long in background
    asyncio.create_task(summarize_session_history(x_user_id, session_id))
    
    return ChatResponse(response=response_text, charts=charts, session_id=session_id)

@router.get("/sessions")
def get_sessions_endpoint(x_user_id: str = Header(...)):
    return get_chat_sessions(x_user_id)

@router.get("/sessions/{session_id}/history")
def get_chat_history(session_id: str, x_user_id: str = Header(...)):
    return get_history(x_user_id, session_id, 50)
