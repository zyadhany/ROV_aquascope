from __future__ import annotations

from typing import Any

from .base_block import BaseBlock


class CameraBlock(BaseBlock):
    def get_data(self) -> dict[str, Any]:
        media = self._dict_config('media')
        topic = str(media.get('topic', '')).strip()
        data = super().get_data()
        media_payload = {
            **media,
            'topic': topic,
            'available': bool(media.get('stream_url') or topic),
            'message': (
                'Camera media source configured.'
                if media.get('stream_url') or topic
                else 'No camera media source configured.'
            ),
        }

        if topic:
            watch_result = self.ros_interface.watch_topic(
                topic,
                str(media.get('message_type', '')).strip(),
            )
            topic_info = self.ros_interface.get_topic_info(topic)
            media_payload.update({
                'status': (
                    topic_info.get('status', 'unknown')
                    if watch_result.get('success', False)
                    else 'error'
                ),
                'message_type': topic_info.get('message_type', ''),
                'publishers_count': topic_info.get('publishers_count', 0),
                'subscribers_count': topic_info.get('subscribers_count', 0),
                'frequency_hz': topic_info.get('frequency_hz', 0.0),
                'last_received_at': topic_info.get('last_received_at'),
                'message': (
                    topic_info.get('message', media_payload['message'])
                    if watch_result.get('success', False)
                    else watch_result.get('message', media_payload['message'])
                ),
            })

        data['media'] = media_payload
        return data
