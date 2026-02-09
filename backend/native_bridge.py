from __future__ import annotations

import ctypes
import math
from pathlib import Path


class LinkMetric:
    def __init__(self) -> None:
        self._score_fn = None
        self._capacity_fn = None
        lib_path = Path(__file__).resolve().parent.parent / "native" / "liblink_quality.so"
        if lib_path.exists():
            lib = ctypes.CDLL(str(lib_path))
            score_fn = lib.link_quality_score
            score_fn.argtypes = [ctypes.c_double, ctypes.c_double, ctypes.c_double, ctypes.c_int]
            score_fn.restype = ctypes.c_double
            self._score_fn = score_fn

            if hasattr(lib, "link_capacity_mbps"):
                capacity_fn = lib.link_capacity_mbps
                capacity_fn.argtypes = [ctypes.c_double, ctypes.c_double, ctypes.c_int]
                capacity_fn.restype = ctypes.c_double
                self._capacity_fn = capacity_fn

    @staticmethod
    def _python_fallback(distance_m: float, tx_power_dbm: float, noise_floor_dbm: float, same_channel: bool) -> float:
        if not same_channel:
            return 0.0

        distance = max(distance_m, 1.0)
        path_loss = 20.0 * math.log10(distance)
        snr_like = tx_power_dbm - noise_floor_dbm - path_loss
        quality = 1.0 / (1.0 + math.exp(-(snr_like - 12.0) / 5.0))
        return min(max(quality, 0.0), 1.0)

    def score(self, distance_m: float, tx_power_dbm: float, noise_floor_dbm: float, same_channel: bool) -> float:
        if self._score_fn is None:
            return self._python_fallback(distance_m, tx_power_dbm, noise_floor_dbm, same_channel)
        return float(self._score_fn(distance_m, tx_power_dbm, noise_floor_dbm, 1 if same_channel else 0))

    def capacity_mbps(self, quality: float, channel_width_mhz: float = 20.0, mimo_streams: int = 2) -> float:
        bounded_quality = min(max(quality, 0.0), 1.0)
        if self._capacity_fn is None:
            spectral_eff = 0.5 + 4.5 * bounded_quality
            return max(channel_width_mhz, 1.0) * spectral_eff * max(mimo_streams, 1) * 0.45
        return float(self._capacity_fn(bounded_quality, channel_width_mhz, max(mimo_streams, 1)))


metric = LinkMetric()
