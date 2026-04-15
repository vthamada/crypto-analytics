from __future__ import annotations

import json
import logging
from urllib import request


class HTTPLogHandler(logging.Handler):
    """Send structured logs to an external HTTP endpoint."""

    def __init__(self, url: str, token: str = "") -> None:
        super().__init__()
        self.url = url
        self.token = token

    def emit(self, record: logging.LogRecord) -> None:
        payload = {
            "logger": record.name,
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "funcName": record.funcName,
            "lineno": record.lineno,
            "created": record.created,
        }
        data = json.dumps(payload).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        req = request.Request(self.url, data=data, headers=headers, method="POST")
        try:
            with request.urlopen(req, timeout=2):
                return
        except Exception:
            self.handleError(record)
