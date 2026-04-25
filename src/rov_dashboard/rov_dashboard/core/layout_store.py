from __future__ import annotations

from copy import deepcopy
import json
import os
from pathlib import Path
import tempfile
import threading
from typing import Any

from .config_loader import get_package_paths

DEFAULT_LAYOUT: dict[str, Any] = {
    'version': 1,
    'viewport': {
        'zoom': 1.0,
        'pan_x': 0.0,
        'pan_y': 0.0,
    },
    'positions': {},
    'groups': [],
}

_LAYOUT_LOCK = threading.Lock()


def _layout_path() -> Path:
    return get_package_paths().config_directory / 'layout.json'


def _normalize_viewport(value: Any) -> dict[str, float]:
    viewport = deepcopy(DEFAULT_LAYOUT['viewport'])
    if not isinstance(value, dict):
        return viewport

    zoom = value.get('zoom')
    pan_x = value.get('pan_x')
    pan_y = value.get('pan_y')

    if isinstance(zoom, (int, float)) and float(zoom) > 0:
        viewport['zoom'] = float(zoom)
    if isinstance(pan_x, (int, float)):
        viewport['pan_x'] = float(pan_x)
    if isinstance(pan_y, (int, float)):
        viewport['pan_y'] = float(pan_y)

    return viewport


def _normalize_positions(value: Any) -> dict[str, dict[str, float]]:
    if not isinstance(value, dict):
        return {}

    cleaned_positions: dict[str, dict[str, float]] = {}
    for block_id, position in value.items():
        if not isinstance(block_id, str) or not isinstance(position, dict):
            continue

        x_value = position.get('x')
        y_value = position.get('y')
        if isinstance(x_value, (int, float)) and isinstance(y_value, (int, float)):
            cleaned_positions[block_id] = {
                'x': float(x_value),
                'y': float(y_value),
            }

    return cleaned_positions


def _normalize_groups(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []

    groups: list[dict[str, Any]] = []
    for item in value:
        if not isinstance(item, dict):
            continue

        block_ids = item.get('block_ids', [])
        groups.append({
            'id': str(item.get('id', '')).strip(),
            'label': str(item.get('label', '')).strip(),
            'color': str(item.get('color', '#64748b')).strip(),
            'priority': item.get('priority', 0),
            'block_ids': [
                str(block_id)
                for block_id in block_ids
                if isinstance(block_id, str)
            ] if isinstance(block_ids, list) else [],
        })

    return [group for group in groups if group['id']]


def _normalize_layout(value: Any) -> dict[str, Any]:
    layout = deepcopy(DEFAULT_LAYOUT)

    if not isinstance(value, dict):
        return layout

    version = value.get('version')
    if isinstance(version, int) and version > 0:
        layout['version'] = version

    layout['viewport'] = _normalize_viewport(value.get('viewport'))
    layout['positions'] = _normalize_positions(value.get('positions'))
    layout['groups'] = _normalize_groups(value.get('groups'))

    return layout


def _assert_json_serializable(value: Any) -> None:
    try:
        json.dumps(value)
    except (TypeError, ValueError) as error:
        raise ValueError('Layout payload must be JSON-serializable.') from error


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.NamedTemporaryFile(
        mode='w',
        encoding='utf-8',
        dir=path.parent,
        prefix='layout_',
        suffix='.json',
        delete=False,
    ) as temp_file:
        json.dump(payload, temp_file, indent=2)
        temp_file.write('\n')
        temp_path = Path(temp_file.name)

    os.replace(temp_path, path)


def load_layout() -> dict[str, Any]:
    path = _layout_path()
    try:
        with path.open('r', encoding='utf-8') as layout_file:
            loaded_layout = json.load(layout_file)
    except (FileNotFoundError, json.JSONDecodeError):
        return deepcopy(DEFAULT_LAYOUT)

    return _normalize_layout(loaded_layout)


def save_layout(layout_data: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(layout_data, dict):
        raise ValueError('Layout payload must be a JSON object.')

    _assert_json_serializable(layout_data)
    merged_layout = load_layout()
    merged_layout.update(layout_data)
    normalized_layout = _normalize_layout(merged_layout)

    with _LAYOUT_LOCK:
        _atomic_write_json(_layout_path(), normalized_layout)

    return deepcopy(normalized_layout)
