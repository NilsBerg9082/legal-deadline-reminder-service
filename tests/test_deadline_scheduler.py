from datetime import date, datetime, timezone

from deadline_scheduler import MatterIntake, decide_deadline_reminder


def test_signed_delivery_triggers_reminder_seven_days_before_deadline() -> None:
    matter = MatterIntake(
        matter_id="MAT-204",
        client_name="River Street Media",
        deadline=date(2026, 9, 24),
        signed_document_delivered_at=datetime(2026, 9, 10, 16, 30, tzinfo=timezone.utc),
    )

    decision = decide_deadline_reminder(matter, today=date(2026, 9, 17))

    assert decision.should_notify is True
    assert decision.reminder_date == date(2026, 9, 17)
    assert decision.message == (
        "River Street Media: matter MAT-204 has a deadline on 2026-09-24."
    )


def test_reminder_waits_until_signed_document_is_delivered() -> None:
    matter = MatterIntake(
        matter_id="MAT-205",
        client_name="Northline Studio",
        deadline=date(2026, 9, 24),
        signed_document_delivered_at=datetime(2026, 9, 18, 8, 0, tzinfo=timezone.utc),
    )

    decision = decide_deadline_reminder(matter, today=date(2026, 9, 17))

    assert decision.should_notify is False
    assert decision.message is None
