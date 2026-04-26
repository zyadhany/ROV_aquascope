from __future__ import annotations

from typing import Any

from .base_block import BaseBlock


class PumpBlock(BaseBlock):
    MODE_LABELS = {
        0: 'off',
        1: 'fill',
        2: 'drain',
    }

    def get_status(self) -> dict[str, Any]:
        status = super().get_status()
        mode = status.get('value')
        try:
            mode = int(mode)
        except (TypeError, ValueError):
            pass
        status['mode'] = mode
        status['mode_label'] = self.MODE_LABELS.get(mode)
        status['mode_labels'] = self.MODE_LABELS
        if status['mode_label']:
            status['state'] = status['mode_label']
        return status

    def get_data(self) -> dict[str, Any]:
        data = super().get_data()
        data['mode_labels'] = self.MODE_LABELS
        for source in data.get('values', {}).values():
            if not isinstance(source, dict):
                continue
            try:
                mode = int(source.get('value'))
            except (TypeError, ValueError):
                continue
            source['label'] = self.MODE_LABELS.get(mode)
        return data
