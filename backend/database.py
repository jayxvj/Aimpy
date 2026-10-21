from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()


class PredictionHistory(db.Model):
    __tablename__ = "prediction_history"

    id = db.Column(db.Integer, primary_key=True)

    hours_studied = db.Column(db.Float, nullable=False)
    attendance = db.Column(db.Float, nullable=False)
    previous_scores = db.Column(db.Float, nullable=False)

    predicted_score = db.Column(db.Float, nullable=False)
    performance_category = db.Column(db.String(50), nullable=False)
    model_used = db.Column(db.String(100), nullable=False)

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    def to_dict(self):
        return {
            "id": self.id,
            "hours_studied": self.hours_studied,
            "attendance": self.attendance,
            "previous_scores": self.previous_scores,
            "predicted_score": self.predicted_score,
            "performance_category": self.performance_category,
            "model_used": self.model_used,
            "created_at": self.created_at.isoformat()
        }