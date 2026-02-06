import os
import json
import html
from datetime import datetime, time, timedelta
from urllib.parse import quote
from urllib.request import urlopen
from zoneinfo import ZoneInfo
from html2image import Html2Image
from PIL import Image
import calendar_api

WEEKDAY_KR = ["월", "화", "수", "목", "금", "토", "일"]

def _weekday_label(date_value):
    return WEEKDAY_KR[date_value.weekday()]

def _format_today_label(date_value):
    return date_value.strftime("%y.%m.%d") + f"({_weekday_label(date_value)})"

def _format_day_label(date_value):
    return date_value.strftime("%m.%d") + f"({_weekday_label(date_value)})"

def _build_today_events_list(events, day_date, local_tz):
    day_start = datetime.combine(day_date, time.min, tzinfo=local_tz)
    day_end = day_start + timedelta(days=1)
    items = []

    for event in events:
        if event["end"] <= day_start or event["start"] >= day_end:
            continue
        if event["all_day"]:
            time_label = "하루종일"
        else:
            time_label = event["start"].strftime("%H:%M")
        summary = html.escape(event["summary"])
        items.append(
            f'<li><span class="event-time">{time_label}</span>'
            f'<span class="event-text">{summary}</span></li>'
        )

    if not items:
        items.append(
            '<li><span class="event-time">-</span>'
            '<span class="event-text">일정 없음</span></li>'
        )

    return "\n".join(items)

def _build_calendar_headers(days):
    return "\n".join(
        f'<div class="calendar-header-day">{_format_day_label(day)}</div>'
        for day in days
    )

def _build_calendar_columns(events, days, local_tz, start_hour, end_hour):
    columns = []
    for day in days:
        day_start = datetime.combine(day, time(hour=start_hour), tzinfo=local_tz)
        if end_hour == 24:
            day_end = datetime.combine(day + timedelta(days=1), time.min, tzinfo=local_tz)
        else:
            day_end = datetime.combine(day, time(hour=end_hour), tzinfo=local_tz)
        total_minutes = (day_end - day_start).total_seconds() / 60
        day_items = []

        for event in events:
            if event["all_day"]:
                continue
            if event["end"] <= day_start or event["start"] >= day_end:
                continue
            segment_start = max(event["start"], day_start)
            segment_end = min(event["end"], day_end)
            if segment_end <= segment_start:
                continue

            offset_minutes = (segment_start - day_start).total_seconds() / 60
            duration_minutes = (segment_end - segment_start).total_seconds() / 60
            top_pct = max(0.0, min(100.0, offset_minutes / total_minutes * 100))
            height_pct = max(0.5, min(100.0 - top_pct, duration_minutes / total_minutes * 100))

            label = (
                f"{segment_start.strftime('%H:%M')}-"
                f"{segment_end.strftime('%H:%M')} <br> "
                f"{html.escape(event['summary'])}"
            )
            day_items.append(
                f'<div class="calendar-event" style="top: {top_pct:.3f}%; '
                f'height: {height_pct:.3f}%;">{label}</div>'
            )

        columns.append(
            '<div class="calendar-day-column">\n'
            + "\n".join(day_items)
            + "\n</div>"
        )

    return "\n".join(columns)

def _resolve_time_window(events, days, default_start=10, default_end=23):
    if not events or not days:
        return default_start, default_end

    start_hour = default_start
    end_hour = default_end

    range_start = min(days)
    range_end = max(days)

    for event in events:
        if event["all_day"]:
            continue
        if event["end"].date() < range_start or event["start"].date() > range_end:
            continue

        if event["start"].hour < start_hour:
            start_hour = event["start"].hour
        elif event["start"].hour == start_hour and event["start"].minute > 0:
            start_hour = event["start"].hour

        event_end_hour = event["end"].hour
        if event["end"].minute > 0:
            event_end_hour = min(24, event_end_hour + 1)
        end_hour = max(end_hour, event_end_hour)

    if end_hour <= start_hour:
        end_hour = min(24, start_hour + 1)

    return start_hour, end_hour

def _build_calendar_time_labels(start_hour, end_hour):
    total_hours = max(1, end_hour - start_hour)
    labels = []
    for hour in range(start_hour, end_hour + 1):
        top_pct = (hour - start_hour) / total_hours * 100
        labels.append(
            f'<div class="calendar-time-label" style="top: {top_pct:.3f}%;">'
            f"{hour:02d}</div>"
        )
    return "\n".join(labels)

def _fetch_weather_label(day_date, local_tz):
    lat = float(os.getenv("WEATHER_LAT", "37.5665"))
    lon = float(os.getenv("WEATHER_LON", "126.9780"))
    tz_name = os.getenv("WEATHER_TZ", "Asia/Seoul")
    tzinfo = local_tz

    try:
        tzinfo = ZoneInfo(tz_name)
    except Exception:
        tzinfo = local_tz

    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}"
        "&hourly=precipitation,snowfall"
        f"&timezone={quote(tz_name)}"
    )

    try:
        with urlopen(url, timeout=6) as response:
            payload = json.load(response)
    except Exception:
        return "날씨 정보 없음"

    hourly = payload.get("hourly", {})
    times = hourly.get("time", [])
    precipitation = hourly.get("precipitation", [])
    snowfall = hourly.get("snowfall", [])

    for time_str, rain_mm, snow_mm in zip(times, precipitation, snowfall):
        try:
            dt = datetime.fromisoformat(time_str).replace(tzinfo=tzinfo)
        except ValueError:
            continue
        if dt.date() != day_date:
            continue
        if snow_mm and snow_mm >= 0.1:
            return f"{dt.hour}시부터 눈"
        if rain_mm and rain_mm >= 0.1:
            return f"{dt.hour}시부터 비"

    return "하루 종일 맑음"

def create_time_image(image_name: str = "calendar.jpg") -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    local_tz = datetime.now().astimezone().tzinfo
    today = datetime.now().date()
    days = [today + timedelta(days=offset) for offset in range(3)]
    events = calendar_api.fetch_events(days=len(days))
    weather_label = _fetch_weather_label(today, local_tz)
    start_hour, end_hour = _resolve_time_window(events, days)

    template_path = "index.html"
    
    with open(template_path, "r", encoding="utf-8") as f:
        html_content = f.read()
    
    html_content = html_content.replace("{{time_placeholder}}", now)
    html_content = html_content.replace("{{today_label}}", _format_today_label(today))
    html_content = html_content.replace("{{weather_label}}", weather_label)
    html_content = html_content.replace(
        "{{today_events_list}}",
        _build_today_events_list(events, today, local_tz),
    )
    html_content = html_content.replace("{{calendar_header_days}}", _build_calendar_headers(days))
    html_content = html_content.replace(
        "{{calendar_day_columns}}",
        _build_calendar_columns(events, days, local_tz, start_hour, end_hour),
    )
    html_content = html_content.replace(
        "{{calendar_time_labels}}",
        _build_calendar_time_labels(start_hour, end_hour),
    )

    filename = image_name
    
    flags = [
        '--window-size=800,601', 
        '--hide-scrollbars',
        '--force-device-scale-factor=1',
        '--headless'
    ]
    
    hti = Html2Image(custom_flags=flags)
    
    print(f"[image generation] image rendering...")
    
    hti.screenshot(html_str=html_content, save_as=filename)

    print("[image generation] cropping image...")
    
    with Image.open(filename) as img:
        cropped_img = img.crop((0, 0, 800, 480))
        cropped_img.save(filename, quality=95)

    print(f"[image generation] success: '{filename}' saved.")

    return filename

if __name__ == "__main__":
    create_time_image()