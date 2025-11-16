# relay.py
from datetime import datetime
from threading import Lock
from typing import Dict, List, Any


# In-memory store: channel_id -> list of messages
# Each message: { "seq": int, "sender_id": int, "text": str, "timestamp": str }
_channels: Dict[str, List[Dict[str, Any]]] = {}

# Protects access to _channels for thread safety
_lock = Lock()


def _get_channel_list(channel_id: str) -> List[Dict[str, Any]]:
    """
    Internal helper: return the list for a given channel_id, creating if needed.
    """
    with _lock:
        if channel_id not in _channels:
            _channels[channel_id] = []
        return _channels[channel_id]


def relay_post_message(channel_id: str, sender_id: int, text: str) -> Dict[str, Any]:
    """
    Append a new message to a channel and return the stored message dict.
    """
    messages = _get_channel_list(channel_id)

    with _lock:
        seq = len(messages) + 1
        msg = {
            "seq": seq,
            "sender_id": sender_id,
            "text": text,
            "timestamp": datetime.utcnow().isoformat(timespec="seconds"),
        }
        messages.append(msg)

    return msg


def relay_get_messages_since(channel_id: str, last_seq: int) -> List[Dict[str, Any]]:
    """
    Return all messages in the channel with seq > last_seq.
    """
    messages = _get_channel_list(channel_id)

    with _lock:
        # Copy slice so we don't leak internal list
        new_msgs = [m for m in messages if m["seq"] > last_seq]

    return new_msgs
