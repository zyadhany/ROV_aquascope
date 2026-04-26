from __future__ import annotations

import pytest

import rov_dashboard.flowchart.flowchart_manager as flowchart_manager_module
from rov_dashboard.flowchart.flowchart_manager import FlowchartManager


class FakeRosInterface:
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


def test_flowchart_manager_reuses_cached_blocks(monkeypatch: pytest.MonkeyPatch) -> None:
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
        flowchart_manager_module,
        'load_blocks_config',
        fake_load_blocks_config,
    )

    manager = FlowchartManager(FakeRosInterface())

    first_block = manager.get_block('/hardware_1')
    cached_block = manager._get_blocks_by_id()['/hardware_1']
    second_state = manager.get_block_state('/hardware_1')

    assert first_block['id'] == '/hardware_1'
    assert second_state['id'] == '/hardware_1'
    assert manager._get_blocks_by_id()['/hardware_1'] is cached_block


def test_flowchart_manager_rebuilds_cache_after_config_change(
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
        flowchart_manager_module,
        'load_blocks_config',
        fake_load_blocks_config,
    )

    manager = FlowchartManager(FakeRosInterface())

    assert manager.get_block('/block_a')['id'] == '/block_a'
    block_a = manager._get_blocks_by_id()['/block_a']

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

    assert manager.get_block('/block_b')['id'] == '/block_b'
    block_b = manager._get_blocks_by_id()['/block_b']
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
        flowchart_manager_module,
        'load_blocks_config',
        fake_load_blocks_config,
    )

    manager = FlowchartManager(FakeRosInterface())
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
        flowchart_manager_module,
        'load_blocks_config',
        fake_load_blocks_config,
    )

    manager = FlowchartManager(FakeRosInterface())
    state = manager.get_block_state('/hardware/pump')

    assert state['status'] == 'descriptive'
    assert state['controls'] == []
    assert state['data']['interactive'] is False
    assert state['data']['description'] == 'Physical pump controlled through ROS topics.'
