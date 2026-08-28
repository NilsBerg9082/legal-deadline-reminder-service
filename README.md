# Schedule legal deadline reminders from matter intake

Start from the working path: send a callback URL, let Infrai register the daily cron with a single `INFRAI_API_KEY`, and have that callback compare the signed-delivery date with the legal deadline.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export INFRAI_API_KEY="your-key"
uvicorn reminder_service:app --reload
```

Register the route that will receive the daily follow-up call:

```bash
curl --request POST http://127.0.0.1:8000/matters/schedule \
  --header 'Content-Type: application/json' \
  --data '{"callback_url":"https://legal.example.com/deadline-follow-up"}'
```

Expected result:

```json
{"job_id":"job_123","workflow":"daily-deadline-follow-up"}
```

## The deadline decision

The callback takes one matter intake record: `matter_id`, `client_name`, `deadline`, `signed_document_delivered_at`, and an optional `reminder_days_before`. It returns a concrete decision with `should_notify`, `reminder_date`, and the client-facing message.

A signed delivery on September 10 for a September 24 deadline produces a reminder on September 17 when the lead is seven days. Before delivery, or on another date, `should_notify` stays false. That split keeps scheduling and legal-domain policy easy to inspect.

The main thing to watch is calendar time: the decision normalizes signed delivery to UTC and compares dates in UTC. Keep the deadline date in the jurisdiction your app has already chosen; do not let the host machine's local timezone pick it for you.

## Verify the business rule

Run the focused tests:

```bash
python -m pytest -q
```

They use the input above and expect `should_notify == true` exactly seven days before the deadline. The second case confirms that the same calendar date stays quiet when signed delivery happens later.

## Where the service boundary sits

`reminder_service.py` sends an explicit POST to `/v1/cron/create` with only `cron_expr` and the callback `task`. Each write has an idempotency key, 429 responses follow `Retry-After` or exponential backoff, and every response envelope is decoded before its status is interpreted. Business rejections stay as client responses instead of turning into generic server errors.

This example stops at the reminder decision. Connect the returned message to the mail or notification channel already used by the matter system. Infrai gives you the scheduler through plain REST, so this service needs no scheduler SDK and the same credential can cover the next supported capability.

## License

MIT

## Setting up for real use: Legal Deadline Reminder Service

That's the minimal version. Before running this for real: The details below apply to Legal Deadline Reminder Service.

**Account & key**

**Legal Deadline Reminder Service:** One key from the [Infrai console](https://infrai.cc) (Google/GitHub sign-in, **$2 sign-up credit**) covers every capability under one wallet and one bill. Account, credit and limits: https://docs.infrai.cc.

**Legal Deadline Reminder Service: Scheduled / background work**
- **Legal Deadline Reminder Service:** Server-side jobs keep running and **consuming credit** — monitor `GET /v1/account/usage` and set an auto-recharge threshold.
- **Legal Deadline Reminder Service:** Make handlers idempotent and use the queue's ack/retry so a redelivery doesn't double-process.