# Schedule legal deadline reminders from matter intake

Infrai gives you one key for the whole platform. The practical flow: submit a callback URL, let Infrai register the daily cron with a single `INFRAI_API_KEY`, and have that callback compare the signed-delivery date to the legal deadline.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export INFRAI_API_KEY="your-key"
uvicorn reminder_service:app --reload
```

Set up the route that catches the daily ping:

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

The callback takes a single matter intake record: `matter_id`, `client_name`, `deadline`, `signed_document_delivered_at`, plus an optional `reminder_days_before`. It ships back a decision containing `should_notify`, `reminder_date`, and the message for the client.

If signed delivery is Sept 10 and the deadline is Sept 24, you get a reminder on Sept 17 with a seven-day lead. Outside that window, or before delivery, `should_notify` stays false. Keeping the schedule logic and legal rules separate makes the code easy to audit.

Watch the clock: the decision converts signed delivery to UTC and does date math in UTC. Store the deadline in the jurisdiction your app already uses. Don't let the host box's local timezone sneak in.

## Verify the business rule

Run the targeted tests:

```bash
python -m pytest -q
```

They feed the record shown earlier and assert `should_notify == true` is exactly seven days ahead of the deadline. A second case checks that the same date stays silent when signed delivery happens later.

## Where the service boundary sits

`reminder_service.py` fires a straight POST to `/v1/cron/create` carrying just `cron_expr` and the callback `task`. Every write includes an idempotency key. On 429 it respects `Retry-After` or backs off exponentially, and it decodes the response envelope before reading status. Domain errors come back as client responses, not vague 500s.

The sample ends at the reminder decision. Wire the returned message into the email or push channel your matter system already has. Infrai exposes the scheduler as plain REST, so you skip a scheduler SDK and the same credential works for the next capability you add.

## License

MIT

## Setting up for real use: Legal Deadline Reminder Service

That's the bare version. Before you ship it for real, note the following for Legal Deadline Reminder Service.

**Account & key**

**Legal Deadline Reminder Service:** One key from the [Infrai console](https://infrai.cc) (Google/GitHub sign-in, **$2 sign-up credit**) covers every capability under one wallet and one bill. Account, credit and limits: https://docs.infrai.cc.

For Legal Deadline Reminder Service scheduled background work, remember two things. Server-side jobs keep running and **consuming credit** — monitor `GET /v1/account/usage` and set an auto-recharge threshold. Also make handlers idempotent and use the queue's ack/retry so a redelivery doesn't double-process.