from __future__ import annotations

import os
import signal
import subprocess
import time
from dataclasses import dataclass
from typing import Any


@dataclass
class NodeStartResult:
    success: bool
    message: str
    ros_node_name: str
    package: str
    executable: str
    pid: int | None


@dataclass
class NodeStopResult:
    success: bool
    message: str
    ros_node_name: str
    process_name: str
    pids: list[int]
    force_killed_pids: list[int]


class NodeHandler:
    def __init__(self, terminate_wait_sec: float = 2.0):
        self.terminate_wait_sec = terminate_wait_sec
        self._processes: dict[str, subprocess.Popen] = {}

    # -------------------------
    # Start node
    # -------------------------

    def start_node_from_config(self, node_config: dict[str, Any]) -> NodeStartResult:
        ros_node_name = self._resolve_ros_node_name(node_config)

        package = (
            node_config.get("package")
            or node_config.get("ros_package") 
            or "my_robot_sim"
        )

        executable = (
            node_config.get("executable")
            or node_config.get("ros_executable")
            or ros_node_name.split("/")[-1]
        )

        if not package:
            return NodeStartResult(
                success=False,
                message="Node config missing package / ros_package.",
                ros_node_name=ros_node_name,
                package="",
                executable=str(executable),
                pid=None,
            )

        return self.start_node(
            ros_node_name=ros_node_name,
            package=str(package),
            executable=str(executable),
        )

    def start_node(
        self,
        ros_node_name: str,
        package: str,
        executable: str,
    ) -> NodeStartResult:
        ros_node_name = self._normalize_ros_node_name(ros_node_name)

        if self._ros_node_exists(ros_node_name):
            return NodeStartResult(
                success=True,
                message=f"Node already running: {ros_node_name}",
                ros_node_name=ros_node_name,
                package=package,
                executable=executable,
                pid=None,
            )

        process = subprocess.Popen(
            ["ros2", "run", package, executable],
            start_new_session=True,
        )

        self._processes[ros_node_name] = process

        time.sleep(1)

        if process.poll() is not None:
            return NodeStartResult(
                success=False,
                message=f"Node failed to start: {ros_node_name}",
                ros_node_name=ros_node_name,
                package=package,
                executable=executable,
                pid=process.pid,
            )

        return NodeStartResult(
            success=True,
            message=f"Node started: {ros_node_name}",
            ros_node_name=ros_node_name,
            package=package,
            executable=executable,
            pid=process.pid,
        )

    # -------------------------
    # Stop node
    # -------------------------

    def stop_node_from_config(self, node_config: dict[str, Any]) -> NodeStopResult:
        ros_node_name = self._resolve_ros_node_name(node_config)
        return self.stop_node(ros_node_name)

    def stop_node(self, node_name: str) -> NodeStopResult:
        ros_node_name = self._normalize_ros_node_name(node_name)
        process_name = self._process_name_from_ros_node(ros_node_name)

        if not self._ros_node_exists(ros_node_name):
            return NodeStopResult(
                success=True,
                message=f"Node is not running: {ros_node_name}",
                ros_node_name=ros_node_name,
                process_name=process_name,
                pids=[],
                force_killed_pids=[],
            )

        pids = self._find_process_pids(process_name)

        if not pids:
            return NodeStopResult(
                success=False,
                message=f"ROS node exists, but no process matched: {process_name}",
                ros_node_name=ros_node_name,
                process_name=process_name,
                pids=[],
                force_killed_pids=[],
            )

        for pid in pids:
            self._send_signal(pid, signal.SIGTERM)

        time.sleep(self.terminate_wait_sec)

        still_running = [pid for pid in pids if self._pid_is_running(pid)]
        force_killed_pids: list[int] = []

        if still_running:
            for pid in still_running:
                self._send_signal(pid, signal.SIGKILL)
                force_killed_pids.append(pid)

        self._processes.pop(ros_node_name, None)

        return NodeStopResult(
            success=True,
            message=f"Node stopped: {ros_node_name}",
            ros_node_name=ros_node_name,
            process_name=process_name,
            pids=pids,
            force_killed_pids=force_killed_pids,
        )

    # -------------------------
    # Helpers
    # -------------------------

    def _resolve_ros_node_name(self, node_config: dict[str, Any]) -> str:
        ros_node_name = (
            node_config.get("ros_node")
            or node_config.get("ros_node_name")
        )

        if ros_node_name:
            return self._normalize_ros_node_name(str(ros_node_name))

        node_id = str(node_config["id"])
        return self._normalize_ros_node_name(node_id.split("/")[-1])

    def _normalize_ros_node_name(self, node_name: str) -> str:
        node_name = node_name.strip()

        if not node_name:
            raise ValueError("node_name cannot be empty")

        if not node_name.startswith("/"):
            node_name = f"/{node_name}"

        return node_name

    def _process_name_from_ros_node(self, ros_node_name: str) -> str:
        return ros_node_name.split("/")[-1]

    def _ros_node_exists(self, ros_node_name: str) -> bool:
        result = subprocess.run(
            ["ros2", "node", "list"],
            text=True,
            capture_output=True,
        )

        if result.returncode != 0:
            return False

        running_nodes = result.stdout.strip().splitlines()
        return ros_node_name in running_nodes

    def _find_process_pids(self, process_name: str) -> list[int]:
        result = subprocess.run(
            ["ps", "-eo", "pid=,args="],
            text=True,
            capture_output=True,
        )

        if result.returncode != 0:
            return []

        current_pid = os.getpid()
        pids: list[int] = []

        for line in result.stdout.splitlines():
            line = line.strip()

            if not line:
                continue

            try:
                pid_text, command = line.split(maxsplit=1)
                pid = int(pid_text)
            except ValueError:
                continue

            if pid == current_pid:
                continue

            if self._command_matches_process(command, process_name):
                pids.append(pid)

        return pids

    def _command_matches_process(self, command: str, process_name: str) -> bool:
        return process_name in command

    def _pid_is_running(self, pid: int) -> bool:
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False

    def _send_signal(self, pid: int, sig: signal.Signals) -> None:
        try:
            os.kill(pid, sig)
        except ProcessLookupError:
            pass