from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

PACKAGE_NAME = 'rov_dashboard'

DEFAULT_DASHBOARD_CONFIG: dict[str, Any] = {
    'project_name': 'ROV Dashboard',
    'refresh_rate_ms': 1000,
    'edit_mode_enabled': True,
    'allow_drag': True,
    'allow_save_layout': True,
    'show_connection_labels': True,
    'theme': {
        'background': '#0f172a',
        'panel_background': '#111827',
        'text': '#f8fafc',
        'muted_text': '#94a3b8',
    },
    'colors': {},
    'font_sizes': {},
}

DEFAULT_BLOCKS_CONFIG: dict[str, Any] = {
    'blocks': [],
    'connections': [],
}

DEFAULT_SERVICES_CONFIG: dict[str, Any] = {
    'services': [],
}

try:
    from ament_index_python.packages import (
        PackageNotFoundError,
        get_package_share_directory,
    )
except ImportError:  # pragma: no cover - source mode fallback
    PackageNotFoundError = Exception
    get_package_share_directory = None


@dataclass(frozen=True)
class PackagePaths:
    share_directory: Path
    config_directory: Path
    web_directory: Path


def _source_package_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _looks_like_source_package(path: Path) -> bool:
    return (path / 'config').is_dir() and (path / 'web').is_dir()


def get_package_paths() -> PackagePaths:
    """Return config/web paths in source checkouts and colcon installs."""
    source_root = _source_package_root()

    if _looks_like_source_package(source_root):
        share_directory = source_root
    elif get_package_share_directory is not None:
        try:
            share_directory = Path(get_package_share_directory(PACKAGE_NAME))
        except PackageNotFoundError:
            share_directory = source_root
    else:
        share_directory = source_root

    return PackagePaths(
        share_directory=share_directory,
        config_directory=share_directory / 'config',
        web_directory=share_directory / 'web',
    )


def _load_json_file(path: Path, default_value: dict[str, Any]) -> dict[str, Any]:
    try:
        with path.open('r', encoding='utf-8') as json_file:
            loaded_value = json.load(json_file)
    except (FileNotFoundError, json.JSONDecodeError):
        return deepcopy(default_value)

    if not isinstance(loaded_value, dict):
        return deepcopy(default_value)

    return loaded_value


def load_json_config(filename: str, default_value: dict[str, Any]) -> dict[str, Any]:
    config_path = get_package_paths().config_directory / filename
    return _load_json_file(config_path, default_value)


def load_dashboard_config() -> dict[str, Any]:
    return load_json_config('dashboard_config.json', DEFAULT_DASHBOARD_CONFIG)


def load_blocks_config() -> dict[str, Any]:
    loaded_blocks = load_json_config('blocks.json', DEFAULT_BLOCKS_CONFIG)
    blocks = loaded_blocks.get('blocks')
    connections = loaded_blocks.get('connections')

    return {
        'blocks': blocks if isinstance(blocks, list) else [],
        'connections': connections if isinstance(connections, list) else [],
    }


def load_services_config() -> dict[str, Any]:
    loaded_services = load_json_config('services.json', DEFAULT_SERVICES_CONFIG)
    services = loaded_services.get('services')
    return {
        'services': services if isinstance(services, list) else [],
    }
