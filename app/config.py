# app/config.py

RAG_EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
EMBED_DIM = 384

CHAT_MEMORY_LIMIT = 25  # last 20–25 messages for short-term memory

SYSTEM_PROMPT = (
    "You are NeoConsult — an AI Project Booking Assistant for an analytics company. "
    "You answer questions about services using given context and help users book "
    "project consultation slots. Be concise, professional, and clear."
)
