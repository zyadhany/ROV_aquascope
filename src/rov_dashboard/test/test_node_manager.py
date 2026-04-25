from __future__ import annotations

import pytest

import rov_dashboard.services.node_manager as node_manager_module
from rov_dashboard.services.node_manager import NodeManager


class FakeRosInterface:
    def __init__(self) -> None:
        self.status_by_node: dict[str, str] = {}

    def get_node_info(self, node_name: str) -> dict[str, object]:
        return {
            'node': node_name,
            'status': self.status_by_node.get(node_name, 'not_found'),
        }


class FakeProcess:
    def __init__(self, pid: int = 12345) -> None:
        self.pid = pid
        self._running = True

    def poll(self) -> int | None:
        return None if self._running else 0

    def wait(self, timeout: float | None = None) -> int:
        self._running = False
        return 0


def configure_services(
    monkeypatch: pytest.MonkeyPatch,
    services: list[dict[str, object]],
) -> None:
    monkeypatch.setattr(
        node_manager_module,
        'load_services_config',
        lambda: {'services': services},
    )


def test_node_manager_status_supports_alias(monkeypatch: pytest.MonkeyPatch) -> None:
    configure_services(
        monkeypatch,
        [
            {
                'id': 'depth_hold',
                'node_name': '/hold_depth',
                'aliases': ['depth_hold_node'],
                'start_command': 'ros2 run rov_control depth_hold',
            },
        ],
    )
    ros_interface = FakeRosInterface()
    ros_interface.status_by_node['/hold_depth'] = 'active'
    manager = NodeManager(ros_interface)

    status = manager.get_status('depth_hold_node')

    assert status['running'] is True
    assert status['status'] == 'running'
    assert status['node_name'] == '/hold_depth'


def test_node_manager_start_tracks_process(monkeypatch: pytest.MonkeyPatch) -> None:
    configure_services(
        monkeypatch,
        [
            {
                'id': 'depth_hold',
                'node_name': '/hold_depth',
                'start_command': 'ros2 run rov_control depth_hold',
            },
        ],
    )
    ros_interface = FakeRosInterface()
    manager = NodeManager(ros_interface)
    fake_process = FakeProcess()
    started_commands: list[list[str]] = []

    def fake_popen(*args: object, **kwargs: object) -> FakeProcess:
        started_commands.append(list(args[0]))
        return fake_process

    monkeypatch.setattr(node_manager_module.subprocess, 'Popen', fake_popen)

    result = manager.start_node('depth_hold')

    assert result['success'] is True
    assert result['tracked'] is True
    assert started_commands == [['ros2', 'run', 'rov_control', 'depth_hold']]


def test_node_manager_stop_is_idempotent(monkeypatch: pytest.MonkeyPatch) -> None:
    configure_services(
        monkeypatch,
        [
            {
                'id': 'depth_hold',
                'node_name': '/hold_depth',
                'start_command': 'ros2 run rov_control depth_hold',
            },
        ],
    )
    ros_interface = FakeRosInterface()
    manager = NodeManager(ros_interface)
    fake_process = FakeProcess()
    kill_calls: list[tuple[int, int]] = []

    def fake_popen(*args: object, **kwargs: object) -> FakeProcess:
        return fake_process

    def fake_killpg(pid: int, sig: int) -> None:
        kill_calls.append((pid, sig))
        fake_process.wait()

    monkeypatch.setattr(node_manager_module.subprocess, 'Popen', fake_popen)
    monkeypatch.setattr(node_manager_module.os, 'killpg', fake_killpg)

    manager.start_node('depth_hold')
    first_stop = manager.stop_node('depth_hold')
    second_stop = manager.stop_node('depth_hold')

    assert first_stop['success'] is True
    assert second_stop['success'] is True
    assert len(kill_calls) == 1
