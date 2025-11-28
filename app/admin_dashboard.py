import streamlit as st
from db.database import SessionLocal, get_all_bookings


def show_admin_dashboard():
    """Admin UI to view and filter all bookings."""
    st.header("NeoConsult Project Bookings – Admin Dashboard")

    db = SessionLocal()
    bookings = get_all_bookings(db)

    filter_name = st.text_input("Filter by contact name")
    filter_email = st.text_input("Filter by email")
    filter_date = st.date_input("Filter by date", value=None, format="YYYY-MM-DD")

    rows = []
    for b in bookings:
        c = b.customer
        if filter_name and filter_name.lower() not in c.name.lower():
            continue
        if filter_email and filter_email.lower() not in c.email.lower():
            continue
        if filter_date and b.date != filter_date:
            continue

        rows.append(
            {
                "Booking ID": b.id,
                "Name": c.name,
                "Company": c.company,
                "Email": c.email,
                "Phone": c.phone,
                "Project Type": b.booking_type,
                "Date": b.date,
                "Time": b.time,
                "Status": b.status,
                "Created At": b.created_at,
            }
        )

    if rows:
        st.dataframe(rows, use_container_width=True)
    else:
        st.info("No bookings found with the current filters.")

    db.close()
