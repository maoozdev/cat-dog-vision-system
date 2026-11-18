"""
Structured (JSON) logging.

Every log line is one JSON object, e.g.
{"time": "...", "level": "INFO", "logger": "app.request", "message": "request",
 "method": "POST", "path": "/predict", "status": 200, "duration_ms": 41.2, "request_id": "..."}
Machines (log tools) can search and filter these easily.
"""

import json
import logging
import sys
from datetime import datetime, timezone

# Fields we allow to be attached via logger.info(..., extra={...})
EXTRA_FIELDS = ("method", "path", "status", "duration_ms", "request_id", "user_id",
                "label", "confidence", "model_version", "event", "client_ip")


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        data = {
            "time": datetime.fromtimestamp(record.created, timezone.utc).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for field in EXTRA_FIELDS:
            if hasattr(record, field):
                data[field] = getattr(record, field)
        if record.exc_info:
            data["exception"] = self.formatException(record.exc_info)
        return json.dumps(data, default=str)


def setup_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers[:] = [handler]
    root.setLevel(level.upper())
    # uvicorn prints its own access log; ours is richer, so silence the duplicate.
    logging.getLogger("uvicorn.access").handlers[:] = []
    logging.getLogger("uvicorn.access").propagate = False
