from __future__ import annotations

from collections import deque
from typing import Any

from .base_block import BaseBlock


class NodeBlock(BaseBlock):
    def __init__(
        self,
        raw_config: dict[str, Any],
        ros_interface: Any | None = None,
        max_logs_stored: int = 1000,
    ) -> None:
        super().__init__(raw_config, ros_interface=ros_interface)
        raw_max_logs = self.raw_config.get('max_logs_stored', max_logs_stored)
        try:
            self.max_logs_stored = max(1, int(raw_max_logs))
        except (TypeError, ValueError):
            self.max_logs_stored = max(1, int(max_logs_stored))
        self._logs: deque[dict[str, Any]] = deque(maxlen=self.max_logs_stored)

    def _log_source(self) -> str:
        logs_config = self._dict_config('logs')
        return str(logs_config.get('source', self.raw_config.get('ros_node', self.id))).strip()

    def _normalize_log_name(self, value: str) -> str:
        return str(value or '').strip().strip('/')

    def matches_rosout_log(self, entry: dict[str, Any]) -> bool:
        source = self._normalize_log_name(self._log_source())
        node_name = self._normalize_log_name(str(self.raw_config.get('ros_node', self.id)))
        log_name = self._normalize_log_name(str(entry.get('name', '')))

        if not log_name:
            return False

        return any(
            log_name == candidate or log_name.endswith(f'/{candidate}')
            for candidate in {source, node_name}
            if candidate
        )

    def add_rosout_log(self, entry: dict[str, Any]) -> None:
        self._logs.append(dict(entry))

    def _format_log_line(self, entry: dict[str, Any]) -> str:
        location = ''
        if entry.get('file') and entry.get('line'):
            location = f' ({entry["file"]}:{entry["line"]})'

        timestamp = entry.get('timestamp', '')
        level = entry.get('level', '')
        name = entry.get('name', '')
        message = entry.get('message', '')

        return (
            f'{timestamp} '
            # f'[{level}] '
            # f'[{name}] '
            f'{message}'
            # f'{location}'
        ).strip()

    def get_status(self) -> dict[str, Any]:
        node_name = str(self.raw_config.get('ros_node', self.id)).strip()
        node_info = self.ros_interface.get_node_info(node_name)
        state = node_info.get('status', 'unknown')
        return {
            'state': state,
            'message': (
                'ROS node is active.'
                if state == 'active'
                else 'ROS node was not found in the current graph.'
            ),
            'node': node_name,
            'last_update': self._timestamp(),
        }

    def get_data(self) -> dict[str, Any]:
        node_name = str(self.raw_config.get('ros_node', self.id)).strip()
        return self.ros_interface.get_node_info(node_name)

    def get_logs(self, limit: int | None = None) -> dict[str, Any]:
        lines = [self._format_log_line(entry) for entry in self._logs]
        if limit is not None and limit > 0:
            lines = lines[-limit:]

        return {
            'source': self._log_source(),
            'lines': lines,
            'available': len(self._logs),
            'source_type': 'node_block_rosout',
            'limit': limit,
            'last_update': self._timestamp(),
        }
