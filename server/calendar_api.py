import datetime
import os.path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]

def _get_credentials():
    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                "credentials.json", SCOPES
            )
            creds = flow.run_local_server(port=0)

        with open("token.json", "w") as token:
            token.write(creds.to_json())

    return creds

def _parse_event_time(value):
    if not value:
        return None
    if "T" in value:
        if value.endswith("Z"):
            value = value.replace("Z", "+00:00")
        return datetime.datetime.fromisoformat(value)
    return datetime.date.fromisoformat(value)

def fetch_events(days: int = 5):
    creds = _get_credentials()
    local_tz = datetime.datetime.now().astimezone().tzinfo

    try:
        service = build("calendar", "v3", credentials=creds)

        now = datetime.datetime.now().astimezone()
        end_time = (now + datetime.timedelta(days=days)).isoformat()
        start_time = now.isoformat()

        print(f"[calendar API] search period: {start_time} ~ {end_time}")
        print("-" * 50)

        events_result = (
            service.events()
            .list(
                calendarId="primary",
                timeMin=start_time,
                timeMax=end_time,
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )
        items = events_result.get("items", [])
        events = []

        for event in items:
            start_raw = event.get("start", {}).get("dateTime") or event.get("start", {}).get("date")
            end_raw = event.get("end", {}).get("dateTime") or event.get("end", {}).get("date")
            start_parsed = _parse_event_time(start_raw)
            end_parsed = _parse_event_time(end_raw)

            all_day = not isinstance(start_parsed, datetime.datetime)
            if all_day:
                start_dt = datetime.datetime.combine(start_parsed, datetime.time.min, tzinfo=local_tz)
                if isinstance(end_parsed, datetime.date):
                    end_dt = datetime.datetime.combine(end_parsed, datetime.time.min, tzinfo=local_tz)
                else:
                    end_dt = start_dt + datetime.timedelta(days=1)
            else:
                start_dt = start_parsed.astimezone(local_tz)
                end_dt = end_parsed.astimezone(local_tz) if isinstance(end_parsed, datetime.datetime) else start_dt

            events.append(
                {
                    "summary": event.get("summary", "No title"),
                    "start": start_dt,
                    "end": end_dt,
                    "all_day": all_day,
                }
            )

        events.sort(key=lambda item: item["start"])
        return events

    except HttpError as error:
        print(f"[calendar API] Error: {error}")
        return []

def main():
    events = fetch_events()
    if not events:
        print("[calendar API] No events found for the period.")
        return

    for event in events:
        if event["all_day"]:
            start = event["start"].strftime("%Y-%m-%d")
        else:
            start = event["start"].strftime("%Y-%m-%d %H:%M")
        print(f"[{start}] {event['summary']}")

if __name__ == "__main__":
    main()