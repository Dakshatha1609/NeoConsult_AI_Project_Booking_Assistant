import streamlit as st
from db.database import init_db, SessionLocal
from app.booking_flow import (
    BookingState,
    detect_intent,
    get_missing_field,
    validate_and_set_field,
    summarize_booking,
)
from app.tools import (
    rag_tool,
    booking_persistence_tool,
    email_tool,
    booking_lookup_tool,
)
from app.config import CHAT_MEMORY_LIMIT


def init_session_state():
    """Initialize Streamlit session_state variables."""
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    if "booking_state" not in st.session_state:
        st.session_state.booking_state = BookingState()
    if "vector_store" not in st.session_state:
        st.session_state.vector_store = None


def append_message(role: str, content: str):
    """Append a chat message and keep only last N for short-term memory."""
    st.session_state.chat_history.append({"role": role, "content": content})
    st.session_state.chat_history = st.session_state.chat_history[-CHAT_MEMORY_LIMIT:]


def handle_user_message(user_message):
    """
    Handles user chat, booking flow, and fallbacks if LLM is unavailable.
    """

    import streamlit as st
    from db.session import SessionLocal
    from app.tools import rag_tool, booking_persistence_tool, email_tool
    from datetime import datetime

    db = SessionLocal()
    chat_history = st.session_state.chat_history

    # Basic greeting logic
    if "book" in user_message.lower() and "consult" in user_message.lower():
        st.session_state.mode = "booking"
        return "Great! Let's book a NeoConsult AI project consultation. First, may I have your full name?"

    # --- Booking flow manually handled ---
    if st.session_state.get("mode") == "booking":
        if "name" not in st.session_state:
            st.session_state.name = user_message.strip()
            return "Thanks, may I have your company name?"

        elif "company" not in st.session_state:
            st.session_state.company = user_message.strip()
            return "Please share your email address for confirmation."

        elif "email" not in st.session_state:
            st.session_state.email = user_message.strip()
            return "Got it! Please enter your phone number."

        elif "phone" not in st.session_state:
            st.session_state.phone = user_message.strip()
            return "What type of project consultation would you like to book?"

        elif "booking_type" not in st.session_state:
            st.session_state.booking_type = user_message.strip()
            return "Please provide the preferred date (YYYY-MM-DD)."

        elif "date" not in st.session_state:
            st.session_state.date = user_message.strip()
            return "And what time works best for you? (HH:MM 24-hour format)"

        elif "time" not in st.session_state:
            st.session_state.time = user_message.strip()
            # Show summary for confirmation
            return (
                f"Please confirm your project consultation details:\n\n"
                f"**Name:** {st.session_state.name}\n"
                f"**Company:** {st.session_state.company}\n"
                f"**Email:** {st.session_state.email}\n"
                f"**Phone:** {st.session_state.phone}\n"
                f"**Project Type:** {st.session_state.booking_type}\n"
                f"**Date:** {st.session_state.date}\n"
                f"**Time:** {st.session_state.time}\n\n"
                "Type 'yes' to confirm or 'no' to cancel."
            )

        elif user_message.lower() == "yes":
            payload = {
                "name": st.session_state.name,
                "company": st.session_state.company,
                "email": st.session_state.email,
                "phone": st.session_state.phone,
                "booking_type": st.session_state.booking_type,
                "date": datetime.strptime(st.session_state.date, "%Y-%m-%d"),
                "time": datetime.strptime(st.session_state.time, "%H:%M").time(),
            }

            result = booking_persistence_tool(db, payload)

            if result["success"]:
                try:
                    email_tool(
                        to_email=st.session_state.email,
                        subject="NeoConsult Project Consultation Confirmation",
                        body=(
                            f"Dear {st.session_state.name},\n\n"
                            f"Your NeoConsult AI Project Consultation is confirmed.\n"
                            f"Date: {st.session_state.date} at {st.session_state.time}\n\n"
                            "Thank you for booking with NeoConsult!"
                        ),
                    )
                    msg = f" Booking confirmed! A confirmation email has been sent to {st.session_state.email}."
                except Exception:
                    msg = " Booking confirmed! (Email could not be sent due to SMTP configuration.)"

                # Clear booking state
                st.session_state.mode = "chat"
                for key in ["name", "company", "email", "phone", "booking_type", "date", "time"]:
                    if key in st.session_state:
                        del st.session_state[key]

                return msg
            else:
                return f"Booking failed: {result['error']}"

        elif user_message.lower() == "no":
            st.session_state.mode = "chat"
            return "Booking cancelled. You can start again anytime."

    # --- Fallback: RAG mode for Q&A ---
    else:
        try:
            answer = rag_tool(user_message, st.session_state.vector_store, chat_history)
            chat_history.append({"role": "user", "content": user_message})
            chat_history.append({"role": "assistant", "content": answer})
            return answer
        except Exception:
            return "I'm currently unable to use the language model service, but you can still book a consultation."

    # === Booking lookup intent (bonus) ===
    if intent == "booking_lookup":
        db = SessionLocal()
        # naive: assume email is last token
        email = user_message.split()[-1]
        lookup = booking_lookup_tool(db, email)
        db.close()

        if not lookup["success"]:
            bot = lookup["error"]
        elif not lookup["bookings"]:
            bot = "I could not find any bookings for that email."
        else:
            lines = []
            for b in lookup["bookings"]:
                lines.append(
                    f"ID {b.id}: {b.booking_type} on {b.date} at {b.time} (Status: {b.status})"
                )
            bot = "Here are your bookings:\n" + "\n".join(lines)

        append_message("assistant", bot)
        return bot

    # === Booking flow ===
    if intent == "booking":
        # starting a new flow
        if all(
            getattr(state, f) is None
            for f in ["name", "company", "email", "phone", "booking_type", "date", "time"]
        ):
            bot = (
                "Great! Let's book a NeoConsult AI project consultation.\n"
                "First, may I have your full name?"
            )
            append_message("assistant", bot)
            return bot

        # Continue filling slots
        missing = get_missing_field(state)
        if missing:
            error_msg = validate_and_set_field(state, missing, user_message)
            if error_msg:
                bot = error_msg
                append_message("assistant", bot)
                return bot

        next_missing = get_missing_field(state)
        if next_missing is None:
            state.pending_confirmation = True
            bot = summarize_booking(state)
            append_message("assistant", bot)
            return bot

        questions = {
            "company": "Please share your company name.",
            "email": "What is your work email address?",
            "phone": "Please provide your contact number.",
            "booking_type": (
                "What kind of project are you interested in? "
                "(e.g., Predictive Analytics, BI Dashboards, Data Platform, GenAI POC)"
            ),
            "date": "On which date would you like to schedule the consultation? (YYYY-MM-DD)",
            "time": "At what time? (HH:MM in 24-hour format)",
            "name": "May I have your full name?",
        }

        bot = questions[next_missing]
        append_message("assistant", bot)
        return bot

    # === General questions (RAG) ===
    if intent == "general":
        if vector_store is None:
            bot = (
                "Please upload one or more service PDFs in the sidebar "
                "so I can answer detailed questions about NeoConsult."
            )
            append_message("assistant", bot)
            return bot

        answer = rag_tool(user_message, vector_store, st.session_state.chat_history)
        append_message("assistant", answer)
        return answer

    # Fallback
    bot = "I'm not sure how to handle that. Please try rephrasing your request."
    append_message("assistant", bot)
    return bot
