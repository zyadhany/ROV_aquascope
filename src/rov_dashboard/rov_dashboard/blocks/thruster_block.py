from __future__ import annotations

from typing import Any

from .base_block import BaseBlock


class ThrusterBlock(BaseBlock):
    def get_status(self) -> dict[str, Any]:
        status_source = self._dict_config('status_source')
        if not self.enabled:
            return super().get_status()

        return {
            'state': 'idle',
            'message': 'Thruster status is placeholder data.',
            'status_source': status_source,
            'last_update': self._timestamp(),
        }

    def get_data(self) -> dict[str, Any]:
        return {
            'values': self._data_from_sources(),
            'command_mode': 'placeholder',
            'last_update': self._timestamp(),
        }

    def get_controls(self) -> list[dict[str, Any]]:
        return self._list_config('commands')

    def send_command(self, command: dict[str, Any]) -> dict[str, Any]:
        return super().send_command(command)
