from __future__ import annotations

from typing import Literal

RouteStatus = Literal["parsed", "geocoding", "routing", "optimizing", "optimized", "failed"]
RunStatus = Literal["queued", "running", "completed", "failed"]
