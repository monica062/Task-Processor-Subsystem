# 🐞 Bug Report: Off-by-One Error pada Retry Logic

## Lingkungan
- Python: 3.12.3
- OS: Windows 10
- Framework: pytest 8.4.0, hypothesis 6.135.10
- Database: SQLite in-memory

## Deskripsi Bug
Fungsi `retry_with_backoff()` dalam file `app/utils.py` memiliki off-by-one error. Jumlah maksimum percobaan ulang (`max_retries`) dihitung tanpa memperhitungkan percobaan awal.

## Langkah Reproduksi
1. Jalankan tes berikut:

```python
from unittest.mock import MagicMock
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
    assert called_times[0] == 3  # Harus dipanggil 3x: 1 original + 2 retries