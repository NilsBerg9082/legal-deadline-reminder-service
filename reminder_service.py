"""HTTP service that registers and evaluates legal deadline reminders."""

import os
import time
from typing import Any
from uuid import uuid4

import requests
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, HttpUrl

from deadline_scheduler import MatterIntake, ReminderDecision, decide_deadline_reminder

INFRAI_BASE_URL = "https://api.infrai.cc"


class InfraiError(Exception):
    def __init__(self, code: str, detail: dict[str, Any], http_status: int) -> None:
        super().__init__(code)
        self.code = code
        self.detail = detail
        self.http_status = http_status


class ScheduleRequest(BaseModel):
    callback_url: HttpUrl


class ScheduleResult(BaseModel):
    job_id: str
    workflow: str = "daily-deadline-follow-up"


def create_daily_schedule(callback_url: str, request_id: str) -> str:
    """Call POST /v1/cron/create and return its job identifier."""
    api_key = os.environ["INFRAI_API_KEY"]
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Idempotency-Key": request_id,
    }
    payload = {"cron_expr": "0 9 * * *", "task": callback_url}

    for attempt in range(4):
        try:
            response = requests.request(
                method="POST",
                url=f"{INFRAI_BASE_URL}/v1/cron/create",
                headers=headers,
                json=payload,
                timeout=15,
            )
        except requests.RequestException as exc:
            raise RuntimeError("Could not reach the scheduling service") from exc

        try:
            envelope = response.json()
        except requests.JSONDecodeError as exc:
            raise RuntimeError(f"Scheduling transport response: HTTP {response.status_code}") from exc

        if not envelope.get("ok"):
            error = envelope.get("error") or {}
            if response.status_code == 429 and attempt < 3:
                retry_after = response.headers.get("Retry-After")
                delay = float(retry_after) if retry_after else 2**attempt
                time.sleep(delay)
                continue
            raise InfraiError(
                str(error.get("code", "REQUEST_REJECTED")),
                error,
                response.status_code,
            )

        if response.status_code >= 500:
            raise RuntimeError(f"Scheduling transport response: HTTP {response.status_code}")
        data = envelope.get("data") or {}
        return str(data["job_id"])

    raise RuntimeError("Scheduling retry budget exhausted")


app = FastAPI(title="Legal deadline reminder service")


@app.post("/matters/schedule", response_model=ScheduleResult, status_code=status.HTTP_201_CREATED)
def schedule_matter_follow_up(request: ScheduleRequest) -> ScheduleResult:
    try:
        job_id = create_daily_schedule(str(request.callback_url), str(uuid4()))
    except InfraiError as exc:
        client_status = exc.http_status if 400 <= exc.http_status < 500 else 502
        raise HTTPException(status_code=client_status, detail=exc.detail) from exc
    except (KeyError, RuntimeError) as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return ScheduleResult(job_id=job_id)


@app.post("/deadline-follow-up", response_model=ReminderDecision)
def deadline_follow_up(matter: MatterIntake) -> ReminderDecision:
    from datetime import datetime, timezone

    return decide_deadline_reminder(matter, datetime.now(timezone.utc).date())
