import streamlit as st
from app.chat_logic import init_session_state, handle_user_message
from app.rag_pipeline import build_vectorstore_from_uploads
from app.admin_dashboard import show_admin_dashboard
from db.database import init_db


st.set_page_config(
    page_title="NeoConsult – AI Project Booking Assistant",
    page_icon="",
    layout="wide",
)


def main():
    init_db()
    init_session_state()

    mode = st.sidebar.radio("Mode", ["User Chat", "Admin Dashboard"])

    st.sidebar.markdown("### NeoConsult AI Booking Assistant")
    st.sidebar.markdown(
        "Upload service PDFs and then chat with the assistant, "
        "or switch to the admin dashboard to view bookings."
    )

    uploaded_files = st.sidebar.file_uploader(
        "Upload service PDFs for RAG",
        type=["pdf"],
        accept_multiple_files=True,
    )

    if uploaded_files:
        with st.spinner("Building knowledge base from PDFs..."):
            vector_store = build_vectorstore_from_uploads(uploaded_files)
            if vector_store:
                st.session_state.vector_store = vector_store
                st.sidebar.success("PDFs processed successfully!")
            else:
                st.sidebar.error("No valid text found in the uploaded PDFs.")

    if mode == "Admin Dashboard":
        show_admin_dashboard()
        return

    st.title("NeoConsult – AI Project Booking Assistant ")
    st.caption("Ask about services or book a project consultation slot.")

    # Display chat history
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    # Chat input
    user_input = st.chat_input("Type your message here...")
    if user_input:
        with st.chat_message("user"):
            st.write(user_input)
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                response = handle_user_message(user_input)
                st.write(response)


if __name__ == "__main__":
    main()
