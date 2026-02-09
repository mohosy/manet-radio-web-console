#include <math.h>

// Returns a normalized link quality score in [0, 1].
double link_quality_score(double distance_m, double tx_power_dbm, double noise_floor_dbm, int same_channel) {
    if (!same_channel) {
        return 0.0;
    }

    if (distance_m < 1.0) {
        distance_m = 1.0;
    }

    // Simple Friis-inspired decay with logistic compression.
    double path_loss = 20.0 * log10(distance_m);
    double snr_like = tx_power_dbm - noise_floor_dbm - path_loss;
    double quality = 1.0 / (1.0 + exp(-(snr_like - 12.0) / 5.0));

    if (quality < 0.0) {
        return 0.0;
    }
    if (quality > 1.0) {
        return 1.0;
    }
    return quality;
}
