#test/test_retry_logic.py
from unittest.mock import MagicMock
import pytest
from app.utils import retry_with_backoff


def test_retry_count_off_by_one():
    mock_api = MagicMock()
    mock_api.send.side_effect = [
        type('obj', (object,), {'status_code': 500}),
        type('obj', (object,), {'status_code': 500}),
        type('obj', (object,), {'status_code': 200})
    ]

    called_times = [0]

    def api_call():
        called_times[0] += 1
        return mock_api.send({})

    result = retry_with_backoff(api_call, max_retries=2)
    assert result.status_code == 200
    assert called_times[0] == 3  # Harus dipanggil 3x: 1 original + 2 retries