from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .models import Base, Customer, Booking

DB_URL = "sqlite:///bookings.db"

engine = create_engine(DB_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)


def init_db():
    """Create tables if they don't exist."""
    Base.metadata.create_all(engine)


def get_or_create_customer(db, name: str, email: str, phone: str, company: str | None = None):
    """Find customer by email or create one."""
    customer = db.query(Customer).filter_by(email=email).first()
    if customer:
        return customer

    customer = Customer(name=name, email=email, phone=phone, company=company)
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return customer


def create_booking(db, customer, booking_type, date_obj, time_obj):
    """Create a new booking row."""
    booking = Booking(
        customer_id=customer.customer_id,
        booking_type=booking_type,
        date=date_obj,
        time=time_obj,
    )
    db.add(booking)
    db.commit()
    db.refresh(booking)
    return booking


def get_all_bookings(db):
    """Return all bookings joined with customers, newest first."""
    return (
        db.query(Booking)
        .join(Customer)
        .order_by(Booking.created_at.desc())
        .all()
    )


def get_bookings_by_email(db, email: str):
    """Return bookings for a given email."""
    return (
        db.query(Booking)
        .join(Customer)
        .filter(Customer.email == email)
        .order_by(Booking.created_at.desc())
        .all()
    )
