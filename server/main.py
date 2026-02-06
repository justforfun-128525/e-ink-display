import time
from datetime import datetime

import calendar_api
import generate_image
import send_image

CHECK_INTERVAL_SECONDS = 10 * 60

def _events_signature(events):
    return [
        {
            "summary": event["summary"],
            "start": event["start"].isoformat(),
            "end": event["end"].isoformat(),
            "all_day": event["all_day"],
        }
        for event in events
    ]

def main():
    last_signature = None
    last_date = None
    while True:
        try:
            events = calendar_api.fetch_events()
            signature = _events_signature(events)
            current_date = datetime.now().date()
            date_changed = current_date != last_date
            calendar_changed = signature != last_signature

            if calendar_changed or date_changed:
                image_name = generate_image.create_time_image()
                time.sleep(1)
                send_image.send_image_to_pico(image_name)
                last_signature = signature
                last_date = current_date
            else:
                print("[main] No calendar or date changes. Skip image update.")
        except Exception as exc:
            print(f"[main] Error: {exc}")

        time.sleep(CHECK_INTERVAL_SECONDS)

if __name__ == "__main__":
    main()