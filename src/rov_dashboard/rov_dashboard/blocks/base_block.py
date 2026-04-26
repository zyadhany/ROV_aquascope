from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any

from ..core.ros_interface import RosInterface


class BaseBlock:
    def __init__(
        self,
        raw_config: dict[str, Any],
        ros_interface: RosInterface | None = None,
    ) -> None:
        self.raw_config = raw_config if isinstance(raw_config, dict) else {}
        self.ros_interface = ros_interface or RosInterface()
        self.id = str(self.raw_config.get('id', '')).strip()
        self.name = str(self.raw_config.get('name', self.id or 'Unnamed Block')).strip()
        self.type = str(self.raw_config.get('type', 'unknown')).strip()
        self.category = str(self.raw_config.get('category', 'unknown')).strip()
        self.description = str(self.raw_config.get('description', '')).strip()
        self.enabled = bool(self.raw_config.get('enabled', True))

    def _timestamp(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def _list_config(self, key: str) -> list[dict[str, Any]]:
        value = self.raw_config.get(key, [])
        if not isinstance(value, list):
            return []
        return [item for item in value if isinstance(item, dict)]

    def _dict_config(self, key: str) -> dict[str, Any]:
        value = self.raw_config.get(key, {})
        return value if isinstance(value, dict) else {}

    def _extract_field(self, data: Any, field_path: str | None) -> Any:
        field_path = str(field_path or '').strip()
        if not field_path:
            return data

        value = data
        for field_name in field_path.split('.'):
            if isinstance(value, dict):
                value = value.get(field_name)
                continue

            if hasattr(value, field_name):
                value = getattr(value, field_name)
                continue

            return None

        return value

    def _topic_source_snapshot(self, source: dict[str, Any]) -> dict[str, Any]:
        topic = str(source.get('topic', '')).strip()
        message_type = str(source.get('message_type', '')).strip()
        field = str(source.get('field', '')).strip()

        if not topic:
            return {
                'source_type': 'topic',
                'status': 'misconfigured',
                'message': 'Topic source is missing topic.',
                'value': None,
                'field': field,
                'last_update': self._timestamp(),
            }

        watch_result = self.ros_interface.watch_topic(topic, message_type)
        topic_info = self.ros_interface.get_topic_info(topic)
        latest = self.ros_interface.get_latest_topic_data(topic)
        latest_data = latest.get('data')
        value = self._extract_field(latest_data, field)
        source_status = topic_info.get('status', 'unknown')
        message = topic_info.get('message', '')

        if not watch_result.get('success', False):
            source_status = 'error'
            message = watch_result.get('message', message)
        elif latest_data is None:
            message = latest.get('message', message)

        return {
            'source_type': 'topic',
            'topic': topic,
            'message_type': topic_info.get('message_type', message_type),
            'message_type_full': topic_info.get('message_type_full', ''),
            'field': field,
            'value': value,
            'latest_message': latest,
            'status': source_status,
            'message': message,
            'publishers_count': topic_info.get('publishers_count', 0),
            'subscribers_count': topic_info.get('subscribers_count', 0),
            'frequency_hz': topic_info.get('frequency_hz', 0.0),
            'last_received_at': topic_info.get('last_received_at'),
            'message_age_seconds': topic_info.get('message_age_seconds'),
            'is_stale': topic_info.get('is_stale', False),
            'last_update': self._timestamp(),
        }

    def _source_snapshot(self, source: dict[str, Any]) -> dict[str, Any]:
        source_type = str(source.get('source_type', 'topic')).strip() or 'topic'

        if source_type == 'topic':
            snapshot = self._topic_source_snapshot(source)
        elif source_type in {'static', 'config'}:
            snapshot = {
                'source_type': source_type,
                'status': 'configured',
                'message': 'Value loaded from configuration.',
                'value': source.get('value'),
                'last_update': self._timestamp(),
            }
        else:
            snapshot = {
                'source_type': source_type,
                'status': 'unsupported',
                'message': f'Unsupported source type: {source_type}',
                'value': None,
                'last_update': self._timestamp(),
            }

        snapshot['unit'] = source.get('unit')
        snapshot['name'] = str(source.get('name', source.get('topic', 'value'))).strip()
        return snapshot

    def _state_from_source_statuses(
        self,
        statuses: list[str],
        fallback: str = 'configured',
    ) -> str:
        if not statuses:
            return fallback

        if any(status in {'active', 'ready', 'running'} for status in statuses):
            return 'active'

        if any(status in {'error', 'misconfigured', 'unsupported'} for status in statuses):
            return 'error'

        if any(status == 'stale' for status in statuses):
            return 'stale'

        if any(status == 'waiting' for status in statuses):
            return 'waiting'

        if any(status == 'no_publishers' for status in statuses):
            return 'no_publishers'

        return statuses[0] or fallback

    def _data_from_sources(self) -> dict[str, Any]:
        values: dict[str, Any] = {}
        for source in self._list_config('data_sources'):
            name = str(source.get('name', source.get('topic', 'value'))).strip()
            topic = str(source.get('topic', '')).strip()
            key = name or topic or 'value'
            values[key] = self._source_snapshot(source)
        return values

    def _status_from_source(self, status_source: dict[str, Any]) -> dict[str, Any]:
        snapshot = self._source_snapshot(status_source)
        value = snapshot.get('value')
        state = str(value).strip().lower() if value not in (None, '') else ''

        if not state:
            state = str(snapshot.get('status', 'unknown'))

        return {
            'state': state,
            'value': value,
            'message': snapshot.get('message', ''),
            'status_source': snapshot,
            'last_update': self._timestamp(),
        }

    def _find_command_definition(self, command_name: str) -> dict[str, Any] | None:
        for definition in self._list_config('commands'):
            if definition.get('name') == command_name:
                return definition
        return None

    def _publish_configured_command(
        self,
        command_payload: dict[str, Any],
    ) -> dict[str, Any]:
        command_name = str(command_payload.get('command', '')).strip()
        definition = self._find_command_definition(command_name)

        if definition is None:
            return {
                'success': False,
                'block_id': self.id,
                'command': command_name,
                'message': f'Unknown command for block: {command_name}',
                'last_update': self._timestamp(),
            }

        value = command_payload.get(
            'value',
            definition.get('value', definition.get('default')),
        )
        target_topic = str(definition.get('target_topic', '')).strip()
        message_type = str(definition.get('message_type', '')).strip()

        ros_response = self.ros_interface.publish_command(
            target_topic,
            message_type,
            value,
        )
        success = bool(ros_response.get('success', False))

        return {
            'success': success,
            'block_id': self.id,
            'command': command_name,
            'value': value,
            'definition': deepcopy(definition),
            'ros_response': ros_response,
            'message': ros_response.get(
                'message',
                'Command published to ROS 2 topic.' if success else 'Command failed.',
            ),
            'last_update': self._timestamp(),
        }

    def to_dict(self) -> dict[str, Any]:
        payload = deepcopy(self.raw_config)
        payload['id'] = self.id
        payload['name'] = self.name
        payload['type'] = self.type
        payload['category'] = self.category
        payload['description'] = self.description
        payload['enabled'] = self.enabled
        return payload

    def get_info(self) -> dict[str, Any]:
        return {
            'id': self.id,
            'name': self.name,
            'type': self.type,
            'category': self.category,
            'description': self.description,
            'enabled': self.enabled,
        }

    def get_status(self) -> dict[str, Any]:
        if not self.enabled:
            return {
                'state': 'disabled',
                'message': 'Block is disabled in configuration.',
                'last_update': self._timestamp(),
            }

        status_source = self._dict_config('status_source')
        if status_source:
            return self._status_from_source(status_source)

        data_values = self._data_from_sources()
        statuses = [
            str(value.get('status', ''))
            for value in data_values.values()
            if isinstance(value, dict)
        ]
        state = self._state_from_source_statuses(statuses)
        if data_values:
            message = 'Runtime state derived from configured data sources.'
        elif self.get_controls():
            message = 'Command-only block is configured.'
        else:
            message = 'Block is configured.'

        return {
            'state': state,
            'message': message,
            'last_update': self._timestamp(),
        }

    def get_data(self) -> dict[str, Any]:
        return {
            'values': self._data_from_sources(),
            'last_update': self._timestamp(),
        }

    def get_controls(self) -> list[dict[str, Any]]:
        return deepcopy(self._list_config('commands'))

    def send_command(self, command: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(command, dict):
            return {
                'success': False,
                'block_id': self.id,
                'message': 'Command payload must be a JSON object.',
                'last_update': self._timestamp(),
            }

        if not self.enabled:
            return {
                'success': False,
                'block_id': self.id,
                'message': 'Block is disabled.',
                'last_update': self._timestamp(),
            }

        return self._publish_configured_command(command)

    def get_logs(self, limit: int | None = None) -> dict[str, Any]:
        logs_config = self._dict_config('logs')
        source = str(logs_config.get('source', self.id)).strip()
        return self.ros_interface.get_logs(source, limit=limit)
