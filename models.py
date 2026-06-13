from datetime import datetime

from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash


db = SQLAlchemy()


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(40), unique=True, nullable=False)
    pin_hash = db.Column(db.String(255), nullable=False)
    user_type = db.Column(db.String(20), nullable=False, default="morning")
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    entries = db.relationship(
        "DailyEntry",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy=True,
    )

    def set_pin(self, pin):
        self.pin_hash = generate_password_hash(pin)

    def check_pin(self, pin):
        return check_password_hash(self.pin_hash, pin)


class DailyEntry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    entry_date = db.Column(db.Date, nullable=False, index=True)
    slot_key = db.Column(db.String(40), nullable=False)
    status = db.Column(db.String(10), nullable=False, default="Maybe")
    energy = db.Column(db.Integer, nullable=False, default=3)
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    user = db.relationship("User", back_populates="entries")

    __table_args__ = (
        db.UniqueConstraint(
            "user_id",
            "entry_date",
            "slot_key",
            name="uq_daily_entry_user_date_slot",
        ),
    )
