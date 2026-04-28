import os
import signal
import subprocess
import time


def terminate_ros_node(node_name: str) -> bool:
    """
    Example:
        terminate_ros_node("/mcu_gateway")
        terminate_ros_node("mcu_gateway")
    """

    ros_node_name = node_name if node_name.startswith("/") else f"/{node_name}"
    process_name = ros_node_name.split("/")[-1]

    # 1. Check ROS2 node exists
    result = subprocess.run(
        ["ros2", "node", "list"],
        text=True,
        capture_output=True,
    )

    if result.returncode != 0:
        print("Failed to read ROS2 node list")
        print(result.stderr)
        return False

    nodes = result.stdout.strip().splitlines()

    if ros_node_name not in nodes:
        print(f"ROS node not found: {ros_node_name}")
        return False

    # 2. Find matching Linux process
    result = subprocess.run(
        ["ps", "-eo", "pid=,args="],
        text=True,
        capture_output=True,
    )

    current_pid = os.getpid()
    pids = []

    for line in result.stdout.splitlines():
        line = line.strip()
        if not line:
            continue

        pid_text, command = line.split(maxsplit=1)
        pid = int(pid_text)

        if pid == current_pid:
            continue

        if process_name in command:
            pids.append(pid)

    if not pids:
        print(f"ROS node exists, but no process matched: {process_name}")
        return False

    print(f"Found {ros_node_name} process IDs: {pids}")

    # 3. Graceful terminate
    for pid in pids:
        print(f"Sending SIGTERM to PID {pid}")
        os.kill(pid, signal.SIGTERM)

    time.sleep(2)

    # 4. Force kill if still running
    still_running = []

    for pid in pids:
        try:
            os.kill(pid, 0)
            still_running.append(pid)
        except OSError:
            pass

    if still_running:
        print(f"Still running, force killing: {still_running}")
        for pid in still_running:
            os.kill(pid, signal.SIGKILL)

    print(f"Terminated {ros_node_name}")
    return True

terminate_ros_node("mcu_gateway")

"""
write me short and direct promt for codex

edit node api to have end point of run and terminate node. if there is end point with name start or close just change thiare names.

for run node first it will check node status if running it will do noting,
"""