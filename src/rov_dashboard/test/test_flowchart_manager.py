from __future__ import annotations

import pytest

import rov_dashboard.flowchart.block_manager as block_manager_module
from rov_dashboard.flowchart.block_manager import BlockManager
from rov_dashboard.flowchart.flowchart_manager import FlowchartManager


class FakeRosInterface:
    def set_rosout_log_handler(self, handler: object) -> None:
        self.rosout_log_handler = handler

    def publish_command(self, *args: object) -> dict[str, object]:
        return {'success': True}

    def get_logs(self, source: str, limit: int | None = None) -> dict[str, object]:
        return {'source': source, 'lines': [], 'limit': limit}

    def watch_topic(self, topic: str, message_type: str = '') -> dict[str, object]:
        return {
            'success': True,
            'topic': topic,
            'message_type': message_type,
            'message': 'Watching topic.',
        }

    def get_topic_info(self, topic: str) -> dict[str, object]:
        return {
            'topic': topic,
            'message_type': 'std_msgs/Float64',
            'status': 'active',
            'message': 'Live data received.',
            'publishers_count': 1,
            'subscribers_count': 0,
            'frequency_hz': 10.0,
        }

    def get_latest_topic_data(self, topic: str) -> dict[str, object]:
        return {
            'topic': topic,
            'data': {'data': 1.25},
            'received_at': '2026-04-25T00:00:00+00:00',
        }


def test_block_manager_loads_blocks_once(monkeypatch: pytest.MonkeyPatch) -> None:
    block_config = {
        'blocks': [
            {
                'id': '/hardware_1',
                'type': 'hardware',
                'name': 'Hardware 1',
            },
        ],
        'connections': [],
    }

    def fake_load_blocks_config() -> dict[str, object]:
        return block_config

    monkeypatch.setattr(
        block_manager_module,
        'load_blocks_config',
        fake_load_blocks_config,
    )

    manager = BlockManager(FakeRosInterface())

    first_block = manager.get_block('/hardware_1')
    second_block = manager.get_block('/hardware_1')

    assert first_block.id == '/hardware_1'
    assert second_block is first_block


def test_block_manager_keeps_loaded_blocks_until_explicit_reload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = {
        'config': {
            'blocks': [
                {
                    'id': '/block_a',
                    'type': 'hardware',
                    'name': 'Block A',
                },
            ],
            'connections': [],
        },
    }

    def fake_load_blocks_config() -> dict[str, object]:
        return state['config']

    monkeypatch.setattr(
        block_manager_module,
        'load_blocks_config',
        fake_load_blocks_config,
    )

    manager = BlockManager(FakeRosInterface())

    assert manager.get_block('/block_a').id == '/block_a'
    block_a = manager.get_block('/block_a')

    state['config'] = {
        'blocks': [
            {
                'id': '/block_b',
                'type': 'hardware',
                'name': 'Block B',
            },
        ],
        'connections': [],
    }

    with pytest.raises(KeyError):
        manager.get_block('/block_b')

    manager.load_from_config()
    assert manager.get_block('/block_b').id == '/block_b'
    block_b = manager.get_block('/block_b')
    with pytest.raises(KeyError):
        manager.get_block('/block_a')

    assert block_b is not block_a


def test_flowchart_manager_returns_block_data(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    block_config = {
        'blocks': [
            {
                'id': '/topics/depth/current',
                'type': 'topic',
                'name': 'Current Depth',
                'ros_topic': '/rov/depth/current',
                'message_type': 'std_msgs/Float64',
            },
        ],
        'connections': [],
    }

    def fake_load_blocks_config() -> dict[str, object]:
        return block_config

    monkeypatch.setattr(
        block_manager_module,
        'load_blocks_config',
        fake_load_blocks_config,
    )

    block_manager = BlockManager(FakeRosInterface())
    manager = FlowchartManager(FakeRosInterface(), block_manager)
    data = manager.get_block_data('/topics/depth/current')

    assert data['ros_topic'] == '/rov/depth/current'
    assert data['latest_message']['data'] == {'data': 1.25}


def test_hardware_block_is_descriptive_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    block_config = {
        'blocks': [
            {
                'id': '/hardware/pump',
                'type': 'hardware',
                'name': 'Pump',
                'description': 'Physical pump controlled through ROS topics.',
            },
        ],
        'connections': [],
    }

    def fake_load_blocks_config() -> dict[str, object]:
        return block_config

    monkeypatch.setattr(
        block_manager_module,
        'load_blocks_config',
        fake_load_blocks_config,
    )

    block_manager = BlockManager(FakeRosInterface())
    manager = FlowchartManager(FakeRosInterface(), block_manager)
    state = manager.get_block_state('/hardware/pump')

    assert state['status'] == 'descriptive'
    assert state['controls'] == []
    assert state['data']['interactive'] is False
    assert state['data']['description'] == 'Physical pump controlled through ROS topics.'


def test_block_manager_routes_rosout_logs_to_matching_node_block(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    block_config = {
        'blocks': [
            {
                'id': '/nodes/mcu_gateway',
                'type': 'nodes',
                'name': 'MCU Gateway',
                'ros_node': '/mcu_gateway',
                'logs': {
                    'source': '/mcu_gateway',
                },
            },
        ],
        'connections': [],
    }

    monkeypatch.setattr(
        block_manager_module,
        'load_blocks_config',
        lambda: block_config,
    )
    monkeypatch.setattr(
        block_manager_module,
        'load_dashboard_settings',
        lambda: {'max_logs_stored': 2},
    )

    manager = BlockManager(FakeRosInterface())
    manager.route_rosout_log({
        'timestamp': '2026-04-27T00:00:00+00:00',
        'level': 'INFO',
        'name': 'mcu_gateway',
        'message': 'Connected',
        'file': 'gateway.py',
        'function': 'main',
        'line': 7,
    })
    manager.route_rosout_log({
        'timestamp': '2026-04-27T00:00:01+00:00',
        'level': 'INFO',
        'name': 'unknown_node',
        'message': 'Dropped',
        'file': '',
        'function': '',
        'line': 0,
    })

    logs = manager.get_block('/nodes/mcu_gateway').get_logs()

    assert logs['source_type'] == 'node_block_rosout'
    assert logs['lines'] == [
        '2026-04-27T00:00:00+00:00 [INFO] [mcu_gateway] Connected (gateway.py:7)',
    ]
