"""Lightweight NumPy predictive model for stability trajectory and recovery time estimation."""

from __future__ import annotations

import numpy as np

from app.models.city import CityMetrics, InterventionState


class TrafficAndRecoveryPredictor:
    """Uses NumPy linear regression & EWMA over recent simulation history to forecast stability and recovery hours."""

    def predict(
        self,
        history: list[dict[str, float | int]],
        current_metrics: CityMetrics,
        interventions: InterventionState,
    ) -> tuple[float, float]:
        """Return (predicted_stability_in_5_ticks, predicted_recovery_hours)."""
        if len(history) >= 3:
            recent = history[-8:]
            y = np.array([float(item["stability"]) for item in recent], dtype=np.float64)
            x = np.arange(len(y), dtype=np.float64)
            # Linear regression slope via NumPy polyfit
            slope, intercept = np.polyfit(x, y, 1)
            next_stability = float(np.clip(intercept + slope * (len(y) + 4), 5.0, 100.0))
        else:
            next_stability = current_metrics.city_stability

        # Recovery time heuristic calibrated via weighted linear model
        damage_gap = max(0.0, 100.0 - current_metrics.city_stability)
        road_factor = current_metrics.blocked_roads * 1.45
        fire_factor = current_metrics.active_fires * 2.2
        flood_factor = current_metrics.flooded_tiles * 0.7
        mitigation = 1.0
        if interventions.emergency_response_active:
            mitigation *= 0.42
        if interventions.alternative_routes_active:
            mitigation *= 0.72
        if interventions.load_shedding_active:
            mitigation *= 0.85

        raw_hours = (damage_gap * 0.55 + road_factor + fire_factor + flood_factor) * mitigation
        recovery_hours = round(float(np.clip(raw_hours, 0.5 if damage_gap > 1 else 0.0, 96.0)), 1)
        return round(next_stability, 1), recovery_hours
