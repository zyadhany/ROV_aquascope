from __future__ import annotations

from typing import Any

from .base_block import BaseBlock


class HardwareBlock(BaseBlock):
    """Description-only hardware block with no runtime controls."""

    def get_status(self) -> dict[str, Any]:
        if not self.enabled:
            return {
                'state': 'disabled',
                'message': 'Hardware block is disabled in configuration.',
                'last_update': self._timestamp(),
            }

        return {
            'state': 'descriptive',
            'message': 'Hardware block is descriptive only.',
            'last_update': self._timestamp(),
        }

    def get_data(self) -> dict[str, Any]:
        return {
            'description': self.description,
            'interactive': False,
            'last_update': self._timestamp(),
        }

    def get_controls(self) -> list[dict[str, Any]]:
        return []

    def send_command(self, command: dict[str, Any]) -> dict[str, Any]:
        return {
            'success': False,
            'block_id': self.id,
            'message': 'Hardware blocks are descriptive only and do not accept commands.',
            'last_update': self._timestamp(),
        }

    def get_logs(self, limit: int | None = None) -> dict[str, Any]:
        return {
            'source': self.id,
            'lines': [],
            'limit': limit,
            'message': 'Hardware blocks do not expose logs.',
            'last_update': self._timestamp(),
        }
