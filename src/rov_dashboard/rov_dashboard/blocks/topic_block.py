from __future__ import annotations

from typing import Any

from .base_block import BaseBlock


class TopicBlock(BaseBlock):
    _STATUS_FIELDS = {
        'publishers_count': 0,
        'subscribers_count': 0,
        'bandwidth_bps': 0.0,
        'bandwidth_kbps': 0.0,
        'latest_message_size_bytes': 0,
        'last_received_at': None,
        'message_age_seconds': None,
        'is_stale': False,
    }

    def __init__(
        self,
        raw_config: dict[str, Any],
        ros_interface: Any | None = None,
    ) -> None:
        super().__init__(raw_config, ros_interface=ros_interface)
        self._watch_result: dict[str, Any] | None = None

        if self.enabled:
            self._watch_result = self.ros_interface.watch_topic(
                self._topic_name(),
                self._message_type(),
                latest_message=self._monitor_latest_message(),
            )

    def _topic_name(self) -> str:
        return str(self.raw_config.get('ros_topic', self.id)).strip()

    def _message_type(self) -> str:
        return str(self.raw_config.get('message_type', '')).strip()

    def _monitor_latest_message(self) -> bool:
        monitor_config = self._dict_config('monitor')
        return bool(monitor_config.get('latest_message', True))

    def _topic_snapshot(self) -> tuple[str, dict[str, Any], str, str]:
        topic_name = self._topic_name()
        message_type = self._message_type()
        if self._watch_result is None or not self._watch_result.get('success', False):
            self._watch_result = self.ros_interface.watch_topic(
                topic_name,
                message_type,
                latest_message=self._monitor_latest_message(),
            )

        topic_info = self.ros_interface.get_topic_info(topic_name)
        status = topic_info.get('status', 'unknown')
        message = topic_info.get('message', '')

        if not self._watch_result.get('success', False):
            status = 'error'
            message = self._watch_result.get('message', message)

        topic_info['message_type'] = topic_info.get('message_type', message_type)
        return topic_name, topic_info, status, message

    def get_status(self) -> dict[str, Any]:
        if not self.enabled:
            return super().get_status()

        topic_name, topic_info, status, message = self._topic_snapshot()

        return {
            'state': status,
            'message': message,
            'topic': topic_name,
            'message_type': topic_info['message_type'],
            **{
                field: topic_info.get(field, fallback)
                for field, fallback in self._STATUS_FIELDS.items()
            },
            'last_update': self._timestamp(),
        }

    def _disabled_data(self) -> dict[str, Any]:
        return {
            'ros_topic': self._topic_name(),
            'message_type': self._message_type(),
            'status': 'disabled',
            'message': 'Block is disabled in configuration.',
            'last_update': self._timestamp(),
        }

    def get_data(self) -> dict[str, Any]:
        if not self.enabled:
            return self._disabled_data()

        show_config = self._dict_config('show')
        topic_name, topic_info, status, message = self._topic_snapshot()

        data: dict[str, Any] = {
            'ros_topic': topic_name,
            'message_type': topic_info['message_type'],
            'status': status,
            'message': message,
            'last_received_at': topic_info.get('last_received_at'),
            'message_age_seconds': topic_info.get('message_age_seconds'),
            'is_stale': topic_info.get('is_stale', False),
            'stale_after_seconds': topic_info.get('stale_after_seconds'),
            'last_update': self._timestamp(),
        }

        if show_config.get('publishers', True):
            data['publishers'] = topic_info.get('publishers', [])

        if show_config.get('subscribers', True):
            data['subscribers'] = topic_info.get('subscribers', [])

        if show_config.get('latest_message', True):
            data['latest_message'] = self.ros_interface.get_latest_topic_data(
                topic_name,
            )

        if show_config.get('frequency', True):
            data['frequency_hz'] = topic_info.get('frequency_hz', 0.0)

        if show_config.get('bandwidth', True):
            data['bandwidth_bps'] = topic_info.get('bandwidth_bps', 0.0)
            data['bandwidth_kbps'] = topic_info.get('bandwidth_kbps', 0.0)
            data['latest_message_size_bytes'] = topic_info.get(
                'latest_message_size_bytes',
                0,
            )

        return data
