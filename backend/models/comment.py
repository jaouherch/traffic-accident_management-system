from db import db
from datetime import datetime

class Comment(db.Model):
    __tablename__ = "comments"

    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    score = db.Column(db.Integer, nullable=False, default=0)

    accident_id = db.Column(db.String(36), db.ForeignKey("accidents.id"), nullable=False)
    # Correctly points to "user.id"
    user_id = db.Column(db.String(36), db.ForeignKey("user.id"), nullable=False)

    author = db.relationship("User", back_populates="comments")
    accident = db.relationship("Accident", back_populates="comments")


class CommentVote(db.Model):
    """Prevent awarding gamification points repeatedly for the same vote."""

    __tablename__ = "comment_votes"
    id = db.Column(db.Integer, primary_key=True)
    comment_id = db.Column(db.Integer, db.ForeignKey("comments.id"), nullable=False)
    user_id = db.Column(db.String(36), db.ForeignKey("user.id"), nullable=False)
    __table_args__ = (db.UniqueConstraint("comment_id", "user_id", name="one_vote_per_user"),)
