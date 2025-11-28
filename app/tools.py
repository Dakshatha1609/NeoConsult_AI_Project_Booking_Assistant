import streamlit as st
from openai import OpenAI
from db.database import (
    get_or_create_customer,
    create_booking,
    get_bookings_by_email,
)
from utils.validators import is_valid_email
from .config import SYSTEM_PROMPT
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


def summarize_for_query(text: str, query: str, max_sentences: int = 6) -> str:
    """
    Very simple extractive summariser:
    - Split into sentences
    - Score sentences by overlap with query words
    - Return top N sentences in original order
    """
    import re

    # Normalise
    query_words = {w.lower() for w in re.findall(r"\w+", query) if len(w) > 3}
    # Fallback if query is tiny
    if not query_words:
        query_words = {"service", "solution", "project", "booking"}

    # Split into sentences
    raw_sentences = re.split(r"(?<=[.!?])\s+", text)
    scored = []
    for i, sent in enumerate(raw_sentences):
        tokens = {w.lower() for w in re.findall(r"\w+", sent)}
        score = len(tokens & query_words)
        # Also boost sentences that contain bullets
        if "•" in sent:
            score += 1
        if score > 0:
            scored.append((i, score, sent.strip()))

    if not scored:
        # If nothing scored, just take first few sentences
        scored = [(i, 1, s.strip()) for i, s in enumerate(raw_sentences[:max_sentences])]

    # Sort by score (desc), then index (asc) to keep order
    scored.sort(key=lambda x: (-x[1], x[0]))

    # Take top N and restore original order
    top = sorted(scored[:max_sentences], key=lambda x: x[0])
    sentences = [s for (_, _, s) in top]

    # Clean bullets / spacing a bit
    pretty = []
    for s in sentences:
        s = s.replace("•", "• ")
        pretty.append(s)
    return "\n".join(pretty)


client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])


# 1. RAG Tool
def rag_tool(query: str, vector_store, chat_history):
    """
    Input: query
    Output: answer using retrieved chunks + chat history + LLM.

    Behaviour:
    - First tries to call the OpenAI chat model (normal RAG).
    - If the API fails (quota, bad key, etc.), falls back to a
      conversational answer built directly from the retrieved chunks.
    """
    context_pairs = vector_store.similarity_search(query, k=4) if vector_store else []
    context_text = "\n\n".join([c[0] for c in context_pairs])

    history_text = "\n".join(
        [f"{m['role']}: {m['content']}" for m in chat_history[-20:]]
    )

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                f"Conversation so far:\n{history_text}\n\n"
                f"Context from uploaded PDFs:\n{context_text}\n\n"
                f"User question: {query}"
            ),
        },
    ]

    # --- First try: normal LLM call ---
    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.2,
        )
        return resp.choices[0].message.content

    # --- Fallback: no LLM, just retrieved text in a nice format ---
    except Exception:
        if context_text.strip():
            # Build a focused summary for the user’s question
            summary = summarize_for_query(context_text, query, max_sentences=6)

            return (
                "I'm temporarily unable to use the language model service "
                "(likely due to API limits), so here's a concise answer "
                "built directly from your uploaded NeoConsult document.\n\n"
                f"**What the document says about _\"{query}\"_:**\n\n"
                f"{summary}\n\n"
                "_This summary is extracted from the brochure; you can ask more "
                "follow-up questions or start a booking if you'd like._"
            )
        else:
            return (
                "I'm currently unable to use the language model and I "
                "also couldn't find relevant information in the uploaded PDFs."
            )


# 2. Booking Persistence Tool
def booking_persistence_tool(db, booking_payload: dict):
    """
    Input: structured booking payload.
    Output: dict with success flag, booking_id, error.
    """
    try:
        if not is_valid_email(booking_payload["email"]):
            return {
                "success": False,
                "booking_id": None,
                "error": "Invalid email address.",
            }

        customer = get_or_create_customer(
            db=db,
            name=booking_payload["name"],
            email=booking_payload["email"],
            phone=booking_payload["phone"],
            company=booking_payload.get("company"),
        )

        booking = create_booking(
            db=db,
            customer=customer,
            booking_type=booking_payload["booking_type"],
            date_obj=booking_payload["date"],
            time_obj=booking_payload["time"],
        )

        return {"success": True, "booking_id": booking.id, "error": None}
    except Exception as e:
        return {"success": False, "booking_id": None, "error": str(e)}


# 3. Email Tool
def email_tool(to_email: str, subject: str, body: str):
    """
    Sends an email via SMTP.
    Output: {'success': bool, 'error': str | None}
    """
    try:
        msg = MIMEMultipart()
        msg["From"] = st.secrets["EMAIL_USER"]
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        with smtplib.SMTP(st.secrets["EMAIL_HOST"], int(st.secrets["EMAIL_PORT"])) as server:
            server.starttls()
            server.login(st.secrets["EMAIL_USER"], st.secrets["EMAIL_PASSWORD"])
            server.send_message(msg)

        return {"success": True, "error": None}
    except Exception as e:
        return {"success": False, "error": str(e)}


# 4. Booking Lookup Tool (bonus)
def booking_lookup_tool(db, email: str):
    """
    Retrieve bookings for a given email address.
    """
    if not is_valid_email(email):
        return {
            "success": False,
            "error": "Please enter a valid email address.",
            "bookings": [],
        }
    bookings = get_bookings_by_email(db, email)
    return {"success": True, "error": None, "bookings": bookings}
