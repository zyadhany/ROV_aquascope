from __future__ import annotations

from collections import deque
from datetime import datetime, timezone
import threading
import time
from typing import Any

import rclpy
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node
from rosidl_runtime_py.convert import message_to_ordereddict
from rosidl_runtime_py.utilities import get_message


class RosInterface:
    """
    Real ROS 2 adapter for the dashboard.

    Responsibilities:
    - Watch ROS topics
    - Store latest topic message
    - Calculate topic frequency
    - Show publishers/subscribers
    - Publish dashboard commands
    - Show basic node info
    """

    DEFAULT_STALE_AFTER_SECONDS = 2.0

    def __init__(self) -> None:
        self._lock = threading.RLock()

        self._latest_messages: dict[str, dict[str, Any]] = {}
        self._latest_message_times: dict[str, float] = {}
        self._topic_types: dict[str, str] = {}
        self._subscriptions: dict[str, Any] = {}
        self._publishers: dict[str, Any] = {}
        self._sample_times: dict[str, deque[float]] = {}
        self._logs: deque[str] = deque(maxlen=200)

        if not rclpy.ok():
            rclpy.init(args=None)

        self.node = Node('dashboard_ros_interface')

        self.executor = MultiThreadedExecutor()
        self.executor.add_node(self.node)

        self._executor_thread = threading.Thread(
            target=self.executor.spin,
            daemon=True,
        )
        self._executor_thread.start()

        self._add_log('Dashboard ROS interface started.')

    def _timestamp(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def _add_log(self, message: str) -> None:
        line = f'{self._timestamp()} {message}'
        with self._lock:
            self._logs.append(line)

        try:
            self.node.get_logger().info(message)
        except Exception:
            pass

    def _normalize_topic_name(self, topic_name: str) -> str:
        topic_name = str(topic_name).strip()

        if not topic_name:
            raise ValueError('Topic name cannot be empty')

        return topic_name if topic_name.startswith('/') else f'/{topic_name}'

    def _normalize_node_name(self, node_name: str) -> str:
        node_name = str(node_name).strip()

        if not node_name:
            raise ValueError('Node name cannot be empty')

        return node_name if node_name.startswith('/') else f'/{node_name}'

    def _normalize_message_type(self, message_type: str | None) -> str:
        message_type = str(message_type or '').strip()

        if not message_type:
            return ''

        if message_type.count('/') == 1:
            package, msg_name = message_type.split('/')
            return f'{package}/msg/{msg_name}'

        return message_type

    def _short_message_type(self, message_type: str) -> str:
        message_type = self._normalize_message_type(message_type)

        parts = message_type.split('/')
        if len(parts) == 3 and parts[1] == 'msg':
            return f'{parts[0]}/{parts[2]}'

        return message_type

    def _to_plain_json(self, value: Any) -> Any:
        if isinstance(value, dict):
            return {str(k): self._to_plain_json(v) for k, v in value.items()}

        if isinstance(value, list):
            return [self._to_plain_json(item) for item in value]

        if isinstance(value, tuple):
            return [self._to_plain_json(item) for item in value]

        if isinstance(value, (str, int, float, bool)) or value is None:
            return value

        return str(value)

    def _message_to_dict(self, msg: Any) -> dict[str, Any]:
        try:
            return self._to_plain_json(dict(message_to_ordereddict(msg)))
        except Exception:
            return {'raw': str(msg)}

    def _calculate_frequency(self, topic_name: str) -> float:
        with self._lock:
            samples = self._sample_times.get(topic_name)

            if not samples or len(samples) < 2:
                return 0.0

            duration = samples[-1] - samples[0]

            if duration <= 0:
                return 0.0

            frequency = (len(samples) - 1) / duration
            return round(frequency, 2)

    def _is_own_endpoint(self, endpoint_info: Any) -> bool:
        return (
            endpoint_info.node_name == self.node.get_name()
            and endpoint_info.node_namespace == self.node.get_namespace()
        )

    def _message_age_seconds(self, topic_name: str) -> float | None:
        with self._lock:
            received_time = self._latest_message_times.get(topic_name)

        if received_time is None:
            return None

        return round(max(0.0, time.time() - received_time), 3)

    def _is_stale(self, topic_name: str) -> bool:
        age_seconds = self._message_age_seconds(topic_name)
        return (
            age_seconds is not None
            and age_seconds > self.DEFAULT_STALE_AFTER_SECONDS
        )

    def _infer_message_type(self, topic_name: str) -> str:
        topic_name = self._normalize_topic_name(topic_name)

        try:
            for name, types in self.node.get_topic_names_and_types():
                if name == topic_name and types:
                    return self._normalize_message_type(types[0])
        except Exception as exc:
            self._add_log(f'Failed to infer message type for {topic_name}: {exc}')

        return ''

    def _get_all_topic_types(self, topic_name: str) -> list[str]:
        topic_name = self._normalize_topic_name(topic_name)

        try:
            for name, types in self.node.get_topic_names_and_types():
                if name == topic_name:
                    return [self._normalize_message_type(t) for t in types]
        except Exception as exc:
            self._add_log(f'Failed to get topic types for {topic_name}: {exc}')

        return []

    def watch_topic(
        self,
        topic_name: str,
        message_type: str | None = None,
    ) -> dict[str, Any]:
        topic_name = self._normalize_topic_name(topic_name)
        message_type = self._normalize_message_type(message_type)

        with self._lock:
            if topic_name in self._subscriptions:
                stored_type = self._topic_types.get(topic_name, message_type)
                return {
                    'success': True,
                    'topic': topic_name,
                    'message_type': self._short_message_type(stored_type),
                    'message_type_full': stored_type,
                    'message': 'Already watching topic.',
                    'last_update': self._timestamp(),
                }

        if not message_type:
            message_type = self._infer_message_type(topic_name)

        if not message_type:
            return {
                'success': False,
                'topic': topic_name,
                'message_type': '',
                'message': (
                    'Could not determine topic message type. '
                    'Add message_type in blocks.json.'
                ),
                'last_update': self._timestamp(),
            }

        try:
            msg_class = get_message(message_type)
        except Exception as exc:
            return {
                'success': False,
                'topic': topic_name,
                'message_type': message_type,
                'message': f'Invalid ROS message type: {exc}',
                'last_update': self._timestamp(),
            }

        with self._lock:
            self._topic_types[topic_name] = message_type
            self._sample_times[topic_name] = deque(maxlen=50)

        def callback(msg: Any) -> None:
            now = time.time()

            with self._lock:
                self._sample_times[topic_name].append(now)
                self._latest_message_times[topic_name] = now
                self._latest_messages[topic_name] = {
                    'topic': topic_name,
                    'message_type': self._short_message_type(message_type),
                    'message_type_full': message_type,
                    'data': self._message_to_dict(msg),
                    'received_at': self._timestamp(),
                }

        try:
            subscription = self.node.create_subscription(
                msg_class,
                topic_name,
                callback,
                1,
            )
        except Exception as exc:
            return {
                'success': False,
                'topic': topic_name,
                'message_type': message_type,
                'message': f'Failed to create subscription: {exc}',
                'last_update': self._timestamp(),
            }

        with self._lock:
            self._subscriptions[topic_name] = subscription

        self._add_log(f'Watching topic {topic_name} [{message_type}]')

        return {
            'success': True,
            'topic': topic_name,
            'message_type': self._short_message_type(message_type),
            'message_type_full': message_type,
            'message': 'Started watching topic.',
            'last_update': self._timestamp(),
        }

    def get_topic_info(self, topic_name: str) -> dict[str, Any]:
        topic_name = self._normalize_topic_name(topic_name)

        try:
            publishers_info = self.node.get_publishers_info_by_topic(topic_name)
        except Exception:
            publishers_info = []

        try:
            subscribers_info = self.node.get_subscriptions_info_by_topic(topic_name)
        except Exception:
            subscribers_info = []

        publishers = [
            {
                'node_name': info.node_name,
                'node_namespace': info.node_namespace,
                'topic_type': self._short_message_type(info.topic_type),
                'topic_type_full': self._normalize_message_type(info.topic_type),
            }
            for info in publishers_info
            if not self._is_own_endpoint(info)
        ]

        subscribers = [
            {
                'node_name': info.node_name,
                'node_namespace': info.node_namespace,
                'topic_type': self._short_message_type(info.topic_type),
                'topic_type_full': self._normalize_message_type(info.topic_type),
            }
            for info in subscribers_info
            if not self._is_own_endpoint(info)
        ]

        with self._lock:
            is_watched = topic_name in self._subscriptions
            has_latest = topic_name in self._latest_messages
            stored_type = self._topic_types.get(topic_name, '')
            latest = self._latest_messages.get(topic_name)

        discovered_types = self._get_all_topic_types(topic_name)
        message_type_full = (
            stored_type or (discovered_types[0] if discovered_types else '')
        )
        message_age_seconds = self._message_age_seconds(topic_name)
        is_stale = self._is_stale(topic_name)
        last_received_at = latest.get('received_at') if latest else None

        if has_latest and is_stale:
            status = 'stale'
            message = f'Last data received {message_age_seconds:.3f}s ago.'
        elif has_latest:
            status = 'active'
            message = 'Live data received.'
        elif publishers:
            status = 'waiting'
            message = 'Publisher found, waiting for first message.'
        elif is_watched:
            status = 'no_publishers'
            message = 'Dashboard is watching, but no external publisher detected.'
        else:
            status = 'not_watched'
            message = 'Topic is not being watched yet.'

        return {
            'topic': topic_name,
            'message_type': (
                self._short_message_type(message_type_full)
                if message_type_full else ''
            ),
            'message_type_full': message_type_full,
            'available_types': [
                self._short_message_type(t) for t in discovered_types
            ],
            'publishers': publishers,
            'subscribers': subscribers,
            'publishers_count': len(publishers),
            'subscribers_count': len(subscribers),
            'frequency_hz': self._calculate_frequency(topic_name),
            'last_received_at': last_received_at,
            'message_age_seconds': message_age_seconds,
            'is_stale': is_stale,
            'stale_after_seconds': self.DEFAULT_STALE_AFTER_SECONDS,
            'status': status,
            'message': message,
            'watched': is_watched,
            'last_update': self._timestamp(),
        }

    def get_latest_topic_data(self, topic_name: str) -> dict[str, Any]:
        topic_name = self._normalize_topic_name(topic_name)

        with self._lock:
            latest = self._latest_messages.get(topic_name)

        if latest is None:
            return {
                'topic': topic_name,
                'value': None,
                'data': None,
                'message': 'No message received yet.',
                'received_at': None,
                'age_seconds': None,
                'is_stale': False,
                'stale_after_seconds': self.DEFAULT_STALE_AFTER_SECONDS,
                'last_update': self._timestamp(),
            }

        payload = dict(latest)
        payload['age_seconds'] = self._message_age_seconds(topic_name)
        payload['is_stale'] = self._is_stale(topic_name)
        payload['stale_after_seconds'] = self.DEFAULT_STALE_AFTER_SECONDS
        return payload

    def get_node_info(self, node_name: str) -> dict[str, Any]:
        node_name = self._normalize_node_name(node_name)

        target_namespace = '/'
        target_name = node_name.lstrip('/')

        if '/' in target_name:
            parts = target_name.split('/')
            target_name = parts[-1]
            target_namespace = '/' + '/'.join(parts[:-1])

        nodes = self.node.get_node_names_and_namespaces()

        found = any(
            name == target_name and namespace == target_namespace
            for name, namespace in nodes
        )

        publishers: list[dict[str, Any]] = []
        subscribers: list[dict[str, Any]] = []
        services: list[dict[str, Any]] = []

        if found:
            try:
                pubs = self.node.get_publisher_names_and_types_by_node(
                    target_name,
                    target_namespace,
                )
                publishers = [
                    {
                        'topic': topic,
                        'types': [self._short_message_type(t) for t in types],
                    }
                    for topic, types in pubs
                ]
            except Exception as exc:
                self._add_log(
                    f'Failed reading publishers for node {node_name}: {exc}',
                )

            try:
                subs = self.node.get_subscriber_names_and_types_by_node(
                    target_name,
                    target_namespace,
                )
                subscribers = [
                    {
                        'topic': topic,
                        'types': [self._short_message_type(t) for t in types],
                    }
                    for topic, types in subs
                ]
            except Exception as exc:
                self._add_log(
                    f'Failed reading subscribers for node {node_name}: {exc}',
                )

            try:
                srvs = self.node.get_service_names_and_types_by_node(
                    target_name,
                    target_namespace,
                )
                services = [
                    {
                        'service': service,
                        'types': types,
                    }
                    for service, types in srvs
                ]
            except Exception as exc:
                self._add_log(
                    f'Failed reading services for node {node_name}: {exc}',
                )

        return {
            'node': node_name,
            'node_name': target_name,
            'node_namespace': target_namespace,
            'status': 'active' if found else 'not_found',
            'publishers': publishers,
            'subscribers': subscribers,
            'services': services,
            'last_update': self._timestamp(),
        }

    def _set_msg_value(self, msg: Any, value: Any) -> None:
        if isinstance(value, dict):
            self._set_message_fields(msg, value)
            return

        if hasattr(msg, 'data'):
            msg.data = value
            return

        raise ValueError(
            "This message does not have a 'data' field. "
            'Send a dict matching the message fields.',
        )

    def _set_message_fields(self, msg: Any, values: dict[str, Any]) -> None:
        for field_name, field_value in values.items():
            if not hasattr(msg, field_name):
                raise ValueError(f'Unknown message field: {field_name}')

            current_value = getattr(msg, field_name)
            if (
                isinstance(field_value, dict)
                and hasattr(current_value, 'get_fields_and_field_types')
            ):
                self._set_message_fields(current_value, field_value)
                continue

            setattr(msg, field_name, field_value)

    def publish_command(
        self,
        topic_name: str,
        message_type: str,
        value: Any,
    ) -> dict[str, Any]:
        topic_name = self._normalize_topic_name(topic_name)
        message_type = self._normalize_message_type(message_type)

        if not message_type:
            return {
                'success': False,
                'topic': topic_name,
                'message_type': message_type,
                'value': value,
                'last_update': self._timestamp(),
                'message': 'Missing message_type.',
            }

        try:
            msg_class = get_message(message_type)
        except Exception as exc:
            return {
                'success': False,
                'topic': topic_name,
                'message_type': message_type,
                'value': value,
                'last_update': self._timestamp(),
                'message': f'Invalid ROS message type: {exc}',
            }

        publisher_key = f'{topic_name}:{message_type}'

        with self._lock:
            publisher = self._publishers.get(publisher_key)

            if publisher is None:
                publisher = self.node.create_publisher(
                    msg_class,
                    topic_name,
                    10,
                )
                self._publishers[publisher_key] = publisher
                self._add_log(f'Created publisher {topic_name} [{message_type}]')

        try:
            msg = msg_class()
            self._set_msg_value(msg, value)
            publisher.publish(msg)
        except Exception as exc:
            return {
                'success': False,
                'topic': topic_name,
                'message_type': self._short_message_type(message_type),
                'message_type_full': message_type,
                'value': value,
                'last_update': self._timestamp(),
                'message': f'Failed to publish command: {exc}',
            }

        return {
            'success': True,
            'topic': topic_name,
            'message_type': self._short_message_type(message_type),
            'message_type_full': message_type,
            'value': value,
            'placeholder': False,
            'last_update': self._timestamp(),
            'message': 'Command published to ROS 2 topic.',
        }

    def get_logs(self, source: str) -> dict[str, Any]:
        with self._lock:
            lines = list(self._logs)

        return {
            'source': source,
            'lines': lines,
            'placeholder': False,
            'last_update': self._timestamp(),
        }

    def shutdown(self) -> None:
        self._add_log('Shutting down dashboard ROS interface.')

        try:
            self.executor.shutdown()
        except Exception:
            pass

        try:
            self.node.destroy_node()
        except Exception:
            pass
