from __future__ import annotations

from typing import Any

from .base_block import BaseBlock


class SensorBlock(BaseBlock):
    def get_status(self) -> dict[str, Any]:
        if not self.enabled:
            return super().get_status()

        return {
            'state': 'ready',
            'message': 'Sensor status is placeholder data.',
            'status_source': self._dict_config('status_source'),
            'last_update': self._timestamp(),
        }

    def get_data(self) -> dict[str, Any]:
        return {
            'values': self._data_from_sources(),
            'last_update': self._timestamp(),
        }
