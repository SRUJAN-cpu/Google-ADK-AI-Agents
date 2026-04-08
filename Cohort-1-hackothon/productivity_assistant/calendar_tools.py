"""
Google Calendar tools for the productivity assistant.

Auth: uses google.auth.default() — works with:
  - Local dev: `gcloud auth application-default login` (needs calendar scope)
  - Cloud Run: service account must have Calendar API enabled
    and the target calendar shared with the SA email.

Required env var:
  CALENDAR_ID — the calendar to operate on (default: 'primary')
"""

import os
from datetime import datetime, timedelta, timezone

import google.auth
import google.auth.transport.requests
from googleapiclient.discovery import build


def get_current_datetime() -> dict:
    """
    Returns the current date and time.
    Always call this first when the user mentions relative dates
    like 'today', 'tomorrow', 'next Monday', 'this week', etc.
    """
    now = datetime.now(timezone.utc).astimezone()  # local timezone
    return {
        'date': now.strftime('%Y-%m-%d'),
        'time': now.strftime('%H:%M:%S'),
        'day_of_week': now.strftime('%A'),
        'datetime_iso': now.isoformat(),
        'timezone': str(now.tzinfo),
        'tomorrow': (now + timedelta(days=1)).strftime('%Y-%m-%d'),
        'day_after_tomorrow': (now + timedelta(days=2)).strftime('%Y-%m-%d'),
        'next_7_days': [(now + timedelta(days=i)).strftime('%Y-%m-%d (%A)') for i in range(7)],
    }

_SCOPES = ['https://www.googleapis.com/auth/calendar']
_CALENDAR_ID = os.getenv('CALENDAR_ID', 'primary')


def _get_service():
    credentials, _ = google.auth.default(scopes=_SCOPES)
    credentials.refresh(google.auth.transport.requests.Request())
    return build('calendar', 'v3', credentials=credentials)


def get_todays_events() -> dict:
    """
    Fetch all Google Calendar events for today.
    Returns a list of events with id, title, start, end, location, description.
    """
    try:
        service = _get_service()
        now = datetime.now(timezone.utc)
        start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = start_of_day + timedelta(days=1)

        result = service.events().list(
            calendarId=_CALENDAR_ID,
            timeMin=start_of_day.isoformat(),
            timeMax=end_of_day.isoformat(),
            singleEvents=True,
            orderBy='startTime',
        ).execute()

        events = result.get('items', [])
        return {
            'status': 'success',
            'date': start_of_day.strftime('%Y-%m-%d'),
            'count': len(events),
            'events': [_format_event(e) for e in events],
        }
    except Exception as e:
        return {'status': 'error', 'message': str(e)}


def get_week_events() -> dict:
    """
    Fetch all Google Calendar events for the next 7 days.
    Returns a list of events with id, title, start, end, location, description.
    """
    try:
        service = _get_service()
        now = datetime.now(timezone.utc)
        start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_week = start_of_day + timedelta(days=7)

        result = service.events().list(
            calendarId=_CALENDAR_ID,
            timeMin=start_of_day.isoformat(),
            timeMax=end_of_week.isoformat(),
            singleEvents=True,
            orderBy='startTime',
        ).execute()

        events = result.get('items', [])
        return {
            'status': 'success',
            'from': start_of_day.strftime('%Y-%m-%d'),
            'to': end_of_week.strftime('%Y-%m-%d'),
            'count': len(events),
            'events': [_format_event(e) for e in events],
        }
    except Exception as e:
        return {'status': 'error', 'message': str(e)}


def create_calendar_event(
    summary: str,
    start_datetime: str,
    end_datetime: str,
    description: str = '',
    location: str = '',
) -> dict:
    """
    Create a Google Calendar event (blocks time on the calendar).

    Args:
        summary: Event title / name.
        start_datetime: ISO 8601 datetime string, e.g. '2026-04-08T14:00:00+05:30'.
        end_datetime: ISO 8601 datetime string, e.g. '2026-04-08T15:00:00+05:30'.
        description: Optional notes or agenda for the event.
        location: Optional location or meeting link.

    Returns:
        Created event details including the event id and a link to it.
    """
    try:
        service = _get_service()
        event_body = {
            'summary': summary,
            'description': description,
            'location': location,
            'start': {'dateTime': start_datetime},
            'end': {'dateTime': end_datetime},
        }
        created = service.events().insert(
            calendarId=_CALENDAR_ID,
            body=event_body,
        ).execute()

        return {
            'status': 'success',
            'message': f"Event '{summary}' created and time blocked.",
            'event_id': created['id'],
            'link': created.get('htmlLink', ''),
            'start': start_datetime,
            'end': end_datetime,
        }
    except Exception as e:
        return {'status': 'error', 'message': str(e)}


def delete_calendar_event(event_id: str) -> dict:
    """
    Delete a Google Calendar event by its event ID.

    Args:
        event_id: The Google Calendar event ID (from get_todays_events or get_week_events).

    Returns:
        Confirmation of deletion.
    """
    try:
        service = _get_service()
        service.events().delete(calendarId=_CALENDAR_ID, eventId=event_id).execute()
        return {'status': 'success', 'message': f'Event {event_id} deleted.'}
    except Exception as e:
        return {'status': 'error', 'message': str(e)}


def _format_event(event: dict) -> dict:
    start = event.get('start', {})
    end = event.get('end', {})
    return {
        'id': event.get('id', ''),
        'title': event.get('summary', '(no title)'),
        'start': start.get('dateTime', start.get('date', '')),
        'end': end.get('dateTime', end.get('date', '')),
        'location': event.get('location', ''),
        'description': event.get('description', ''),
    }
