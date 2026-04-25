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

    def _data_from_sources(self) -> dict[str, Any]:
        values: dict[str, Any] = {}
        for source in self._list_config('data_sources'):
            name = str(source.get('name', source.get('topic', 'value'))).strip()
            topic = str(source.get('topic', '')).strip()
            key = name or topic or 'value'
            values[key] = {
                'value': None,
                'unit': source.get('unit'),
                'source_type': source.get('source_type', 'topic'),
                'topic': topic,
                'message_type': source.get('message_type'),
                'field': source.get('field'),
                'message': 'No live ROS data connected yet.',
            }
        return values

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

        return {
            'state': 'placeholder',
            'message': 'Runtime status is waiting for ROS 2 integration.',
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

    def get_logs(self) -> dict[str, Any]:
        logs_config = self._dict_config('logs')
        source = str(logs_config.get('source', self.id)).strip()
        return self.ros_interface.get_logs(source)
