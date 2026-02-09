from __future__ import annotations

import ctypes
from pathlib import Path


class LinkMetric:
    def __init__(self) -> None:
        self._fn = None
        lib_path = Path(__file__).resolve().parent.parent / "native" / "liblink_quality.so"
        if lib_path.exists():
            lib = ctypes.CDLL(str(lib_path))
            fn = lib.link_quality_score
            fn.argtypes = [ctypes.c_double, ctypes.c_double, ctypes.c_double, ctypes.c_int]
            fn.restype = ctypes.c_double
            self._fn = fn

    @staticmethod
    def _python_fallback(distance_m: float, tx_power_dbm: float, noise_floor_dbm: float, same_channel: bool) -> float:
        if not same_channel:
            return 0.0

        distance = max(distance_m, 1.0)
        path_loss = 20.0 * __import__("math").log10(distance)
        snr_like = tx_power_dbm - noise_floor_dbm - path_loss
        quality = 1.0 / (1.0 + __import__("math").exp(-(snr_like - 12.0) / 5.0))
        return min(max(quality, 0.0), 1.0)

    def score(self, distance_m: float, tx_power_dbm: float, noise_floor_dbm: float, same_channel: bool) -> float:
        if self._fn is None:
            return self._python_fallback(distance_m, tx_power_dbm, noise_floor_dbm, same_channel)
        return float(self._fn(distance_m, tx_power_dbm, noise_floor_dbm, 1 if same_channel else 0))


metric = LinkMetric()
