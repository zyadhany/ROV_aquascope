from __future__ import annotations

from collections import deque
import threading
import time

from geometry_msgs.msg import Twist
from rov_dashboard.core.ros_interface import RosInterface
from std_msgs.msg import Float64


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

    def get_name(self) -> str:
        return 'dashboard_ros_interface'

    def get_namespace(self) -> str:
        return '/'

    def get_publishers_info_by_topic(self, topic_name: str) -> list[FakeTopicEndpoint]:
        return self._publishers

    def get_subscriptions_info_by_topic(
        self,
        topic_name: str,
    ) -> list[FakeTopicEndpoint]:
        return self._subscribers

    def get_topic_names_and_types(self) -> list[tuple[str, list[str]]]:
        return [('/test/topic', ['std_msgs/msg/Float64'])]


def build_interface(node: FakeNode) -> RosInterface:
    interface = object.__new__(RosInterface)
    interface._lock = threading.RLock()
    interface.node = node
    interface._latest_messages = {}
    interface._latest_message_times = {}
    interface._subscriptions = {'/test/topic': object()}
    interface._topic_types = {'/test/topic': 'std_msgs/msg/Float64'}
    interface._sample_times = {'/test/topic': deque(maxlen=50)}
    return interface


def test_set_msg_value_supports_std_msgs_data_field() -> None:
    interface = object.__new__(RosInterface)
    message = Float64()

    interface._set_msg_value(message, 2.5)

    assert message.data == 2.5


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
    interface = build_interface(
        FakeNode(
            publishers=[FakeTopicEndpoint('dashboard_ros_interface')],
            subscribers=[FakeTopicEndpoint('dashboard_ros_interface')],
        ),
    )

    info = interface.get_topic_info('/test/topic')

    assert info['publishers_count'] == 0
    assert info['subscribers_count'] == 0
    assert info['status'] == 'no_publishers'


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
