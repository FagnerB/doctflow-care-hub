from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Patient(Base):
    __tablename__ = "patients"
    __table_args__ = (
        # Paciente é escopado por médico, não global -- o mesmo telefone pode
        # ser mãe + dois filhos (nomes diferentes) ou o mesmo paciente em dois
        # médicos distintos (registros separados de propósito, nunca fundidos).
        UniqueConstraint("doctor_id", "phone", "name_key", name="uq_patients_doctor_phone_name"),
    )

    # doctor_id/phone sem index=True próprio: o índice do UniqueConstraint
    # acima já cobre (doctor_id) e (doctor_id, phone) como prefixo à esquerda
    # -- um índice solto em cada um seria redundante.
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    doctor_id: Mapped[str] = mapped_column(ForeignKey("doctors.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    # Nome normalizado (normalize_name em app/models/common.py) -- chave de
    # identidade junto com doctor_id+phone, não exibido em lugar nenhum.
    name_key: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str] = mapped_column(String(32), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    doctor = relationship("Doctor")
    appointments = relationship("Appointment", back_populates="patient")
