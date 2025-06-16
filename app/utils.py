# app/utils.py
import time, logging

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


class MockResponse:
    def __init__(self, status_code: int):
        self.status_code = status_code


class ExternalAPIClient:
    def send(self, data):
        """Simulasi API eksternal: selalu ok (dapat di‑mock di test)."""
        return MockResponse(200)


def retry_with_backoff(fn, max_retries: int = 3, base_delay: float = 0.5):
    """
    Jalankan fn().  Ulangi bila HTTP 5xx / exception, memakai back‑off eksponensial.
    """
    for i in range(max_retries + 1):                # 1 panggilan awal + n retries
        try:
            res = fn()
            if 200 <= res.status_code < 300:
                return res
            if 500 <= res.status_code < 600 and i < max_retries:
                delay = base_delay * (2 ** i)
                log.info("Retrying in %.2fs (try %d/%d)", delay, i + 1, max_retries)
                time.sleep(delay)
                continue
            return res                               # 4xx atau 5xx setelah retry habis
        except Exception as exc:                     # pragma: no cover
            log.warning("Error %s, retry=%d", exc, i)
            if i == max_retries:
                raise
            time.sleep(base_delay * (2 ** i))
    return None


# ---------- PATCH: idempoten ----------
def transform_data(data: dict) -> dict:
    """
    Idempoten — `transform(transform(x)) == transform(x)`
    1. Bila input memuat 'raw_value' → gunakan itu.
    2. Bila hanya 'value', asumsikan value = raw*2.
    """
    if "raw_value" in data:
        raw = int(data["raw_value"])
    elif "value" in data:
        raw = int(data["value"]) // 2
    else:
        raise ValueError("Input must contain 'raw_value' or 'value'")

    return {
        "id": data["id"],
        "value": raw * 2,
        "checksum": hash(f"{data['id']}{raw}"),
    }
