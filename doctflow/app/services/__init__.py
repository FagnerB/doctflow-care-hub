from app.services.appointment_service import appointment_service
from app.services.auth_service import auth_service
from app.services.email_service import email_service
from app.services.notification_service import NotificationService, notification_service
from app.services.schedule_service import generate_available_slots

__all__ = [
    "appointment_service",
    "auth_service",
    "email_service",
    "generate_available_slots",
    "notification_service",
    "NotificationService",
]
