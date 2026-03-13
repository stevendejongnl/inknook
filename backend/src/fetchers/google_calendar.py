"""Google Calendar API client with service account auth."""

import logging
from datetime import datetime

import httpx
from google.auth.transport.requests import Request
from google.oauth2.service_account import Credentials

logger = logging.getLogger(__name__)


class GoogleCalendarClient:
    """Async client for Google Calendar API with service account."""

    def __init__(self, service_account_json: dict, http_client: httpx.AsyncClient) -> None:
        """
        Initialize Google Calendar client with service account.

        Args:
            service_account_json: Service account JSON dict
            http_client: httpx AsyncClient for requests
        """
        self.service_account_json = service_account_json
        self.http_client = http_client
        self._credentials: Credentials | None = None
        self._access_token: str | None = None

    async def _get_access_token(self) -> str | None:
        """
        Get valid access token using service account JWT.

        Returns:
            Access token string, or None on failure

        Implementation:
        - If token exists and not expired, return it
        - Otherwise, create JWT credentials from service_account_json
        - Refresh to get access token
        - Cache token and expiry
        """
        try:
            if not self.service_account_json:
                logger.error("Google Calendar: No service account JSON configured")
                return None

            scopes = ["https://www.googleapis.com/auth/calendar.readonly"]
            credentials = Credentials.from_service_account_info(
                self.service_account_json, scopes=scopes
            )
            credentials.refresh(Request())
            self._access_token = credentials.token
            logger.info("Google Calendar: Got new access token")
            return self._access_token
        except Exception as e:
            logger.error(f"Google Calendar: Failed to get access token: {e}")
            return None

    async def get_upcoming_events(self, max_results: int = 5) -> list[dict]:
        """
        Fetch upcoming calendar events.

        Args:
            max_results: Maximum number of events to return

        Returns:
            List of events with summary, start, end, or empty list on error
            Format: [{"summary": "...", "start": "2026-03-10T09:30:00+01:00", "end": "..."}, ...]

        Implementation:
        - GET https://www.googleapis.com/calendar/v3/calendars/primary/events
        - Query params: timeMin (now), maxResults, orderBy=startTime, singleEvents=true
        - Parse JSON response
        - Extract summary, start, end from each event
        """
        token = await self._get_access_token()
        if not token:
            logger.error("Google Calendar: No access token")
            return []

        try:
            now = datetime.utcnow().isoformat() + "Z"
            from src.config import settings
            calendar_id = settings.google_calendar_id
            url = f"https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events"
            params = {
                "timeMin": now,
                "maxResults": max_results,
                "orderBy": "startTime",
                "singleEvents": "true",
            }
            headers = {"Authorization": f"Bearer {token}"}

            response = await self.http_client.get(url, headers=headers, params=params)
            if response.status_code != 200:
                logger.error(f"Google Calendar: HTTP {response.status_code}")
                return []

            data = response.json()
            events = []
            for item in data.get("items", []):
                event = {
                    "summary": item.get("summary", "Untitled"),
                    "start": item.get("start", {}).get(
                        "dateTime", item.get("start", {}).get("date", "")
                    ),
                    "end": item.get("end", {}).get(
                        "dateTime", item.get("end", {}).get("date", "")
                    ),
                }
                events.append(event)

            logger.info(f"Google Calendar: Got {len(events)} events")
            return events
        except Exception as e:
            logger.error(f"Google Calendar: Exception: {e}")
            return []
