"""
Triggers package - Contains all workflow trigger implementations.

Available triggers:
- WebhookTrigger: HTTP webhook-based trigger
- TimerTrigger: Scheduled/cron-based trigger
- ManualTrigger: CLI-based manual trigger
"""

from .webhook_trigger import WebhookTrigger

__all__ = ['WebhookTrigger']
