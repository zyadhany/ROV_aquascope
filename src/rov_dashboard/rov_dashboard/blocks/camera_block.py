from __future__ import annotations

from typing import Any

from .base_block import BaseBlock


class CameraBlock(BaseBlock):
    def get_status(self) -> dict[str, Any]:
        if not self.enabled:
            return super().get_status()

        return {
            'state': 'standby',
            'message': 'Camera stream is placeholder data.',
            'status_source': self._dict_config('status_source'),
            'last_update': self._timestamp(),
        }

    def get_data(self) -> dict[str, Any]:
        media = self._dict_config('media')
        topic = str(media.get('topic', '')).strip()
        return {
            'values': self._data_from_sources(),
            'media': {
                **media,
                'stream_url': None,
                'topic': topic,
                'message': 'No live camera stream connected yet.',
            },
            'last_update': self._timestamp(),
        }

    def get_controls(self) -> list[dict[str, Any]]:
        return self._list_config('commands')

    def send_command(self, command: dict[str, Any]) -> dict[str, Any]:
        return super().send_command(command)
