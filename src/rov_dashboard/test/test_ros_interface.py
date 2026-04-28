from __future__ import annotations

from collections import deque
import threading
import time

from geometry_msgs.msg import Twist
import pytest
from rcl_interfaces.msg import Log
from rov_dashboard.core.ros_interface import RosInterface
from std_msgs.msg import Bool, Float64, Int32


class FakeTopicEndpoint:
    def __init__(self, node_name: str, node_namespace: str = '/') -> None:
        self.node_name = node_name
        self.node_namespace = node_namespace
        self.topic_type = 'std_msgs/msg/Float64'


class FakeNode:
    def __init__(
        self,
        publishers: list[FakeTopicEndpoint] | None = None,
        subscribers: list[FakeTopicEndpoint] | None = None,
    ) -> None:
        self._publishers = publishers or []
        self._subscribers = subscribers or []
        self.publisher_info_calls = 0
        self.subscription_info_calls = 0
        self.subscription_callback = None

    def get_name(self) -> str:
        return 'dashboard_ros_interface'

    def get_namespace(self) -> str:
        return '/'

    def get_publishers_info_by_topic(self, topic_name: str) -> list[FakeTopicEndpoint]:
        self.publisher_info_calls += 1
        return self._publishers

    def get_subscriptions_info_by_topic(
        self,
        topic_name: str,
    ) -> list[FakeTopicEndpoint]:
        self.subscription_info_calls += 1
        return self._subscribers

    def get_topic_names_and_types(self) -> list[tuple[str, list[str]]]:
        return [('/test/topic', ['std_msgs/msg/Float64'])]

    def create_subscription(
        self,
        msg_class: object,
        topic_name: str,
        callback: object,
        qos: int,
    ) -> object:
        self.subscription_callback = callback
        return object()


def build_interface(node: FakeNode) -> RosInterface:
    interface = object.__new__(RosInterface)
    interface._lock = threading.RLock()
    interface.node = node
    interface._latest_messages = {}
    interface._latest_message_times = {}
    interface._last_received_at = {}
    interface._capture_latest_messages = {}
    interface._subscriptions = {'/test/topic': object()}
    interface._topic_types = {'/test/topic': 'std_msgs/msg/Float64'}
    interface._sample_times = {'/test/topic': deque(maxlen=50)}
    interface._sample_sizes = {'/test/topic': deque(maxlen=50)}
    interface._logs = deque(maxlen=200)
    interface._rosout_log_handler = None
    return interface


def test_set_msg_value_supports_std_msgs_data_field() -> None:
    interface = object.__new__(RosInterface)
    message = Float64()

    interface._set_msg_value(message, 2.5)

    assert message.data == 2.5


def test_set_msg_value_coerces_integer_input_to_float_field() -> None:
    interface = object.__new__(RosInterface)
    message = Float64()

    interface._set_msg_value(message, 1)

    assert message.data == 1.0
    assert isinstance(message.data, float)


def test_set_msg_value_rejects_non_integer_for_integer_field() -> None:
    interface = object.__new__(RosInterface)
    message = Int32()

    with pytest.raises(ValueError):
        interface._set_msg_value(message, 1.5)


def test_set_msg_value_coerces_string_to_boolean_field() -> None:
    interface = object.__new__(RosInterface)
    message = Bool()

    interface._set_msg_value(message, 'true')

    assert message.data is True


def test_set_msg_value_supports_nested_message_dicts() -> None:
    interface = object.__new__(RosInterface)
    message = Twist()

    interface._set_msg_value(
        message,
        {
            'linear': {
                'x': 1.0,
                'y': 0.0,
                'z': 0.0,
            },
            'angular': {
                'x': 0.0,
                'y': 0.0,
                'z': 0.5,
            },
        },
    )

    assert message.linear.x == 1.0
    assert message.angular.z == 0.5


def test_topic_info_filters_dashboard_endpoint_counts() -> None:
    node = FakeNode(
        publishers=[FakeTopicEndpoint('dashboard_ros_interface')],
        subscribers=[FakeTopicEndpoint('dashboard_ros_interface')],
    )
    interface = build_interface(node)

    info = interface.get_topic_info('/test/topic')
    again = interface.get_topic_info('/test/topic')

    assert info['publishers_count'] == 0
    assert info['subscribers_count'] == 0
    assert info['status'] == 'no_publishers'
    assert again['status'] == 'no_publishers'
    assert node.publisher_info_calls == 1
    assert node.subscription_info_calls == 1


def test_topic_info_marks_old_latest_message_as_stale() -> None:
    interface = build_interface(
        FakeNode(
            publishers=[FakeTopicEndpoint('external_depth_node')],
            subscribers=[],
        ),
    )
    interface._latest_messages['/test/topic'] = {
        'topic': '/test/topic',
        'message_type': 'std_msgs/Float64',
        'message_type_full': 'std_msgs/msg/Float64',
        'data': {'data': 1.25},
        'received_at': '2026-04-25T00:00:00+00:00',
    }
    interface._latest_message_times['/test/topic'] = (
        time.time() - RosInterface.DEFAULT_STALE_AFTER_SECONDS - 0.1
    )

    info = interface.get_topic_info('/test/topic')
    latest = interface.get_latest_topic_data('/test/topic')

    assert info['status'] == 'stale'
    assert info['is_stale'] is True
    assert info['message_age_seconds'] > RosInterface.DEFAULT_STALE_AFTER_SECONDS
    assert latest['is_stale'] is True


def test_watch_topic_can_skip_latest_message_capture() -> None:
    node = FakeNode(publishers=[FakeTopicEndpoint('external_depth_node')])
    interface = build_interface(node)
    interface._subscriptions = {}
    interface._topic_types = {}
    interface._sample_times = {}
    interface._sample_sizes = {}

    result = interface.watch_topic(
        '/test/topic',
        'std_msgs/Float64',
        latest_message=False,
    )
    message = Float64()
    message.data = 1.25

    assert result['success'] is True
    assert callable(node.subscription_callback)

    node.subscription_callback(message)

    info = interface.get_topic_info('/test/topic')
    latest = interface.get_latest_topic_data('/test/topic')

    assert '/test/topic' not in interface._latest_messages
    assert info['status'] == 'active'
    assert info['captures_latest_message'] is False
    assert latest['data'] is None
    assert latest['capture_enabled'] is False


def test_rosout_callback_routes_structured_entries_to_handler() -> None:
    interface = build_interface(FakeNode())
    entries = []
    interface.set_rosout_log_handler(entries.append)
    msg = Log()
    msg.stamp.sec = 1
    msg.stamp.nanosec = 500_000_000
    msg.level = Log.WARN
    msg.name = 'rov_controller'
    msg.msg = 'Command timeout'
    msg.file = 'controller.py'
    msg.function = 'tick'
    msg.line = 9

    interface._rosout_callback(msg)

    assert entries == [{
        'timestamp': '1970-01-01T00:00:01.500000+00:00',
        'level': 'WARN',
        'name': 'rov_controller',
        'message': 'Command timeout',
        'file': 'controller.py',
        'function': 'tick',
        'line': 9,
    }]
