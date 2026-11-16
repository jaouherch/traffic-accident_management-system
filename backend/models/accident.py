import uuid
from datetime import datetime
from db import db

class Accident(db.Model):
    __tablename__ = "accidents"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Must point to "user.id" (singular) to match your User model
    user_id = db.Column(db.String(36), db.ForeignKey("user.id"), nullable=True)
    status = db.Column(db.String(20), default="pending_verification", nullable=False)
    verified_by = db.Column(db.String(36), db.ForeignKey("user.id"), nullable=True)

    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    description = db.Column(db.Text, nullable=False)
    severity = db.Column(db.Integer, nullable=False)
    reporter = db.relationship("User", back_populates="accidents", foreign_keys=[user_id])
    is_anonymous = db.Column(db.Boolean, default=False)
    is_safe = db.Column(db.Boolean, default=False)
    casualties_injured = db.Column(db.Integer, default=0)
    casualties_dead = db.Column(db.Integer, default=0)
    photo_url = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship with Comment
    comments = db.relationship("Comment", back_populates="accident", cascade="all, delete-orphan")

    # Explicit relationships back to User
    @property
    def author(self):
        """Backward-compatible alias for the accident reporter."""
        return self.reporter
    verifier = db.relationship("User", foreign_keys=[verified_by])
