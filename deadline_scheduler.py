"""Domain decisions for legal deadline reminders."""

from datetime import date, datetime, timedelta, timezone

from pydantic import BaseModel, Field


class MatterIntake(BaseModel):
    matter_id: str = Field(min_length=1)
    client_name: str = Field(min_length=1)
    deadline: date
    signed_document_delivered_at: datetime
    reminder_days_before: int = Field(default=7, ge=1, le=90)


class ReminderDecision(BaseModel):
    matter_id: str
    should_notify: bool
    reminder_date: date
    message: str | None = None


def decide_deadline_reminder(matter: MatterIntake, today: date) -> ReminderDecision:
    """Return the reminder state for a matter on a UTC calendar date."""
    reminder_date = matter.deadline - timedelta(days=matter.reminder_days_before)
    delivered_date = matter.signed_document_delivered_at.astimezone(timezone.utc).date()
    should_notify = delivered_date <= today == reminder_date
    message = None
    if should_notify:
        message = (
            f"{matter.client_name}: matter {matter.matter_id} has a deadline "
            f"on {matter.deadline.isoformat()}."
        )
    return ReminderDecision(
        matter_id=matter.matter_id,
        should_notify=should_notify,
        reminder_date=reminder_date,
        message=message,
    )
