"""AI City Administrator: Deterministic tactical optimizer + optional local Ollama LLM integration."""

from __future__ import annotations

import os
import httpx

from app.models.city import AIAdviceResponse, AIRecommendation, UniverseSnapshot


class AICityAdministrator:
    """Recommends emergency strategies, compares alternatives, and optionally consults local Ollama."""

    def __init__(self, ollama_url: str | None = None, model_name: str | None = None) -> None:
        self.ollama_url = ollama_url or os.getenv("OLLAMA_HOST", "http://localhost:11434")
        self.model_name = model_name or os.getenv("OLLAMA_MODEL", "llama3.2")

    def analyze(self, snapshot: UniverseSnapshot, question: str | None = None) -> AIAdviceResponse:
        """Generate ranked emergency recommendations and optionally enrich via local Ollama."""
        recs: list[AIRecommendation] = []
        m = snapshot.metrics
        cs = snapshot.cs_metrics
        iv = snapshot.interventions

        # Evaluate actionable interventions based on live telemetry
        if not iv.emergency_response_active and (
            m.active_fires > 0 or m.flooded_tiles > 2 or m.blocked_roads > 2 or m.citizens_affected > 200
        ):
            recs.append(
                AIRecommendation(
                    id="rec-emergency",
                    title="Deploy Priority Emergency Response",
                    priority="CRITICAL",
                    action_key="deploy_emergency_response",
                    rationale=(
                        f"{cs.priority_queue_size} high-severity incidents queued (top: {cs.top_priority_incident}). "
                        "Dispatching ambulances and fire crews suppresses active hazards and starts Dijkstra shelter evacuation."
                    ),
                    projected_stability_gain=round(min(32.0, 14.0 + m.active_fires * 2.5 + m.flooded_tiles * 0.8), 1),
                    projected_citizens_saved=max(180, int(m.citizens_affected * 0.48)),
                    tradeoff="Increases municipal emergency fleet load and shelter occupancy immediately.",
                )
            )

        if not iv.alternative_routes_active and (m.avg_congestion > 22.0 or m.blocked_roads > 0):
            recs.append(
                AIRecommendation(
                    id="rec-reroute",
                    title="Activate Dynamic A* Alternative Routes",
                    priority="HIGH",
                    action_key="activate_alternative_routes",
                    rationale=(
                        f"{m.blocked_roads} road blockages and {cs.traffic_queue_total} queued vehicles detected. "
                        "Adaptive traffic signals and congestion-weighted A* rerouting relieve arterial gridlock."
                    ),
                    projected_stability_gain=round(min(22.0, 8.0 + m.blocked_roads * 1.4), 1),
                    projected_citizens_saved=max(90, int(m.citizens_affected * 0.22)),
                    tradeoff="Diverts commuter traffic onto secondary neighborhood avenues.",
                )
            )

        if not iv.load_shedding_active and (m.overloaded_stations > 0 or m.power_coverage < 82.0):
            recs.append(
                AIRecommendation(
                    id="rec-loadshed",
                    title="Enable Critical-First Power Load Shedding",
                    priority="HIGH" if m.overloaded_stations > 0 else "MEDIUM",
                    action_key="toggle_load_shedding",
                    rationale=(
                        f"{m.overloaded_stations} overloaded station(s) and {m.power_coverage:.1f}% grid coverage. "
                        "Shedding non-essential industrial load prevents cascading substation collapse at hospitals & shelters."
                    ),
                    projected_stability_gain=12.5,
                    projected_citizens_saved=max(120, int(m.citizens_affected * 0.18)),
                    tradeoff="Temporarily reduces industrial output to safeguard life-support infrastructure.",
                )
            )

        if m.blocked_roads >= 4:
            recs.append(
                AIRecommendation(
                    id="rec-clear",
                    title="Dispatch Road Rubble Clearance Crews",
                    priority="MEDIUM",
                    action_key="clear_road_blockages",
                    rationale=(
                        f"Restoring {m.blocked_roads} blocked road nodes reconnects cut-off neighborhoods to emergency shelters."
                    ),
                    projected_stability_gain=9.5,
                    projected_citizens_saved=max(80, int(m.citizens_affected * 0.15)),
                    tradeoff="Requires clearing non-flooded road corridors immediately.",
                )
            )

        if not recs:
            recs.append(
                AIRecommendation(
                    id="rec-monitor",
                    title="Maintain Current Stabilization Posture",
                    priority="LOW",
                    action_key=None,
                    rationale=(
                        f"City stability is {m.city_stability:.1f}% with {m.services_active:.1f}% active services. "
                        "Continue monitoring parallel universe divergence or test a higher disaster intensity."
                    ),
                    projected_stability_gain=2.0,
                    projected_citizens_saved=0,
                    tradeoff="No immediate resource trade-off required.",
                )
            )

        summary = (
            f"City Stability {m.city_stability:.1f}% | {m.citizens_affected:,} citizens affected | "
            f"{m.blocked_roads} blocked roads | {m.power_coverage:.1f}% grid coverage. "
            f"Top recommendation: {recs[0].title}."
        )

        answer_text: str | None = None
        source: str = "deterministic-engine"
        detected_model: str | None = None

        # Optional Ollama local LLM enrichment
        ollama_reply, detected_model = self._query_ollama_if_available(snapshot, recs, question)
        if ollama_reply:
            source = "ollama+engine"
            if question:
                answer_text = ollama_reply
            else:
                summary = ollama_reply
        elif question:
            answer_text = self._deterministic_qa(snapshot, recs, question)

        return AIAdviceResponse(
            summary=summary,
            source=source,  # type: ignore[arg-type]
            ollama_model=detected_model,
            recommendations=recs,
            answer=answer_text,
        )

    @staticmethod
    def _deterministic_qa(snapshot: UniverseSnapshot, recs: list[AIRecommendation], question: str) -> str:
        q = question.lower()
        m = snapshot.metrics
        cs = snapshot.cs_metrics
        if "power" in q or "blackout" in q or "grid" in q:
            return (
                f"Power coverage is {m.power_coverage:.1f}% across {cs.bfs_power_components} energized BFS component(s), "
                f"with {cs.dfs_critical_reachable} critical hospital/shelter nodes powered and {m.overloaded_stations} overloaded station(s). "
                + ("Load shedding is protecting critical life-support." if snapshot.interventions.load_shedding_active else "Activating Load Shedding will protect hospitals from cascade trips.")
            )
        if "traffic" in q or "route" in q or "road" in q:
            return (
                f"There are {m.blocked_roads} blocked roads, {cs.traffic_queue_total} queued vehicles, and {m.avg_congestion:.1f}% congestion. "
                f"A* has computed {cs.astar_paths_computed} routes ({cs.astar_nodes_expanded} nodes expanded). "
                + ("Alternative A* corridors are active." if snapshot.interventions.alternative_routes_active else "Activate Alternative Routes to relieve gridlock.")
            )
        if "evac" in q or "shelter" in q or "citizen" in q:
            return (
                f"{m.citizens_affected:,} citizens are currently affected and {m.evacuated_citizens:,} have reached emergency shelters. "
                f"Dijkstra computed {cs.dijkstra_routes_computed} active evacuation corridors (avg cost {cs.dijkstra_avg_cost})."
            )
        return (
            f"At tick {m.tick}, stability is {m.city_stability:.1f}% (5-tick forecast: {cs.ml_predicted_stability_next:.1f}%, "
            f"estimated recovery: {m.recovery_hours}h). Recommended next action: {recs[0].title} — {recs[0].rationale}"
        )

    def _query_ollama_if_available(
        self,
        snapshot: UniverseSnapshot,
        recs: list[AIRecommendation],
        question: str | None,
    ) -> tuple[str | None, str | None]:
        """Try local Ollama server quickly; silently fall back to deterministic engine if offline."""
        try:
            prompt = (
                f"You are the AI City Administrator for Parallel World ({snapshot.city_name}). "
                f"Tick={snapshot.tick}, Stability={snapshot.metrics.city_stability}%, "
                f"Affected={snapshot.metrics.citizens_affected}, BlockedRoads={snapshot.metrics.blocked_roads}, "
                f"Power={snapshot.metrics.power_coverage}%, TopAction={recs[0].title}. "
            )
            if question:
                prompt += f"Answer concisely in 2 sentences: {question}"
            else:
                prompt += "Summarize the top tactical priority and expected consequence in 2 crisp sentences."

            with httpx.Client(timeout=1.2) as client:
                resp = client.post(
                    f"{self.ollama_url}/api/generate",
                    json={"model": self.model_name, "prompt": prompt, "stream": False},
                )
                if resp.status_code == 200:
                    data = resp.json()
                    text = (data.get("response") or "").strip()
                    if text:
                        return text, self.model_name
        except Exception:
            pass
        return None, None
