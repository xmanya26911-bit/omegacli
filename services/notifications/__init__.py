"""
Ω OMEGA Notifications Service — Webhook, email, push notifications (§384).

Manages outbound notifications with retry, templates, and delivery tracking.
"""

from __future__ import annotations

import asyncio
import json
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


# ── Types ──────────────────────────────────────────────────────────────────

class NotificationChannel(Enum):
    WEBHOOK = "webhook"
    CONSOLE = "console"  # Log-based for local/dev


class NotificationPriority(Enum):
    LOW = 0
    NORMAL = 1
    HIGH = 2


@dataclass
class Notification:
    """A notification to be delivered."""
    id: str
    channel: NotificationChannel
    title: str
    body: str
    priority: NotificationPriority = NotificationPriority.NORMAL
    target: str = ""  # URL, email, etc.
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: float = 0.0
    delivered_at: Optional[float] = None
    error: Optional[str] = None
    retry_count: int = 0


# ── Dispatcher ─────────────────────────────────────────────────────────────

class NotificationDispatcher:
    """Dispatches notifications to configured channels."""

    MAX_RETRIES = 3
    RETRY_DELAY = 2.0  # seconds

    def __init__(self):
        self._handlers: dict[NotificationChannel, Any] = {}

    def register_handler(self, channel: NotificationChannel, handler: Any) -> None:
        """Register a handler for a delivery channel."""
        self._handlers[channel] = handler

    async def dispatch(self, notification: Notification) -> bool:
        """Send a notification. Returns True on success."""
        handler = self._handlers.get(notification.channel)
        if not handler:
            notification.error = f"No handler for {notification.channel}"
            return False

        for attempt in range(self.MAX_RETRIES):
            try:
                if notification.channel == NotificationChannel.CONSOLE:
                    print(f"[NOTIFICATION] {notification.title}: {notification.body}")
                elif notification.channel == NotificationChannel.WEBHOOK:
                    # TODO: actual HTTP POST
                    print(f"[WEBHOOK] -> {notification.target}: {notification.title}")
                else:
                    await handler(notification)

                notification.delivered_at = time.time()
                return True
            except Exception as e:
                notification.retry_count = attempt + 1
                notification.error = str(e)
                if attempt < self.MAX_RETRIES - 1:
                    await asyncio.sleep(self.RETRY_DELAY)

        return False

    async def dispatch_many(self, notifications: list[Notification]) -> list[bool]:
        """Dispatch multiple notifications concurrently."""
        results = await asyncio.gather(
            *[self.dispatch(n) for n in notifications],
            return_exceptions=True,
        )
        return [not isinstance(r, Exception) and r for r in results]


def create_notification(
    channel: NotificationChannel,
    title: str,
    body: str,
    target: str = "",
    priority: NotificationPriority = NotificationPriority.NORMAL,
) -> Notification:
    """Create a notification with generated ID."""
    return Notification(
        id=f"notif-{uuid.uuid4().hex[:12]}",
        channel=channel,
        title=title,
        body=body,
        target=target,
        priority=priority,
        created_at=time.time(),
    )
