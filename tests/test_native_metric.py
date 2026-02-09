import unittest

from backend.native_bridge import metric


class NativeMetricTests(unittest.TestCase):
    def test_same_channel_scores_above_mismatch(self):
        same = metric.score(distance_m=80.0, tx_power_dbm=24.0, noise_floor_dbm=-92.0, same_channel=True)
        diff = metric.score(distance_m=80.0, tx_power_dbm=24.0, noise_floor_dbm=-92.0, same_channel=False)

        self.assertGreater(same, diff)
        self.assertGreaterEqual(same, 0.0)
        self.assertLessEqual(same, 1.0)

    def test_closer_distance_improves_quality(self):
        near = metric.score(distance_m=20.0, tx_power_dbm=24.0, noise_floor_dbm=-92.0, same_channel=True)
        far = metric.score(distance_m=200.0, tx_power_dbm=24.0, noise_floor_dbm=-92.0, same_channel=True)
        self.assertGreater(near, far)


if __name__ == "__main__":
    unittest.main()
