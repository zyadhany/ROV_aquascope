from __future__ import annotations

from typing import Any

from .base_block import BaseBlock


class TopicBlock(BaseBlock):
    def _topic_name(self) -> str:
        return str(self.raw_config.get('ros_topic', self.id)).strip()

    def _message_type(self) -> str:
        return str(self.raw_config.get('message_type', '')).strip()

    def get_status(self) -> dict[str, Any]:
        if not self.enabled:
            return super().get_status()

        topic_name = self._topic_name()
        message_type = self._message_type()

        watch_result = self.ros_interface.watch_topic(topic_name, message_type)
        topic_info = self.ros_interface.get_topic_info(topic_name)
        state = topic_info.get('status', 'unknown')
        message = topic_info.get('message', '')

        if not watch_result.get('success', False):
            state = 'error'
            message = watch_result.get('message', message)

        return {
            'state': state,
            'message': message,
            'topic': topic_name,
            'message_type': topic_info.get('message_type', message_type),
            'publishers_count': topic_info.get('publishers_count', 0),
            'subscribers_count': topic_info.get('subscribers_count', 0),
            'last_received_at': topic_info.get('last_received_at'),
            'message_age_seconds': topic_info.get('message_age_seconds'),
            'is_stale': topic_info.get('is_stale', False),
            'last_update': self._timestamp(),
        }

    def get_data(self) -> dict[str, Any]:
        if not self.enabled:
            return {
                'ros_topic': self._topic_name(),
                'message_type': self._message_type(),
                'status': 'disabled',
                'message': 'Block is disabled in configuration.',
                'last_update': self._timestamp(),
            }

        topic_name = self._topic_name()
        message_type = self._message_type()
        show_config = self._dict_config('show')

        watch_result = self.ros_interface.watch_topic(topic_name, message_type)
        topic_info = self.ros_interface.get_topic_info(topic_name)
        latest_message = self.ros_interface.get_latest_topic_data(topic_name)
        status = topic_info.get('status', 'unknown')

        if not watch_result.get('success', False):
            status = 'error'

        data: dict[str, Any] = {
            'ros_topic': topic_name,
            'message_type': topic_info.get('message_type', message_type),
            'status': status,
            'message': (
                watch_result.get('message')
                if not watch_result.get('success', False)
                else topic_info.get('message', '')
            ),
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
            data['latest_message'] = latest_message

        if show_config.get('frequency', True):
            data['frequency_hz'] = topic_info.get('frequency_hz', 0.0)

        return data
