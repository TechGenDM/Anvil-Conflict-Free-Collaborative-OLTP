from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta
from typing import Iterable, Literal

from adapter import Adapter
from schema import Context, Event, IncidentSignal

def _parse(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))

class Engine(Adapter):
    def __init__(self) -> None:
        self.events: list[Event] = []
        self.by_resolved_service: dict[str, list[Event]] = defaultdict(list)
        self.all_incident_signals: list[Event] = []
        self.remediations: dict[str, Event] = {}
        self.renames: dict[str, str] = {}

    def _resolve(self, svc: str) -> str:
        # resolve to the latest known name
        seen = set()
        curr = svc
        while curr in self.renames and curr not in seen:
            seen.add(curr)
            curr = self.renames[curr]
        return curr

    def ingest(self, events: Iterable[Event]) -> None:
        for e in events:
            self.events.append(e)
            
            kind = e.get("kind")
            if kind == "topology" and e.get("change") == "rename":
                self.renames[e["from_"]] = e["to"]

            svc = e.get("service") or e.get("target") or e.get("from_")
            if svc:
                # Store by the name as it was at ingestion time, but we'll query by resolved name
                # Actually, if we just store by resolved name, past events might be under old names
                pass
                
            if kind == "incident_signal":
                self.all_incident_signals.append(e)
            elif kind == "remediation":
                self.remediations[e["incident_id"]] = e

    def reconstruct_context(
        self,
        signal: IncidentSignal,
        mode: Literal["fast", "deep"] = "fast",
    ) -> Context:
        svc = signal.get("service", "")
        resolved_svc = self._resolve(svc)
        ts = _parse(signal["ts"])
        window = timedelta(minutes=30)

        # Related events: just scan the last 1000 events for efficiency
        related = []
        for e in reversed(self.events):
            e_ts = _parse(e["ts"])
            if ts - e_ts > window:
                break
            e_svc = e.get("service") or e.get("target") or e.get("from_")
            if e_svc and self._resolve(e_svc) == resolved_svc:
                if abs(e_ts - ts) <= window:
                    related.append(e)
            if len(related) >= 20:
                break
        
        norm_sig_trigger = signal.get("trigger", "").replace(svc, resolved_svc)

        def _get_similarity(past: Event) -> float:
            past_svc = past.get("service", "")
            past_resolved = self._resolve(past_svc)
            norm_past = past.get("trigger", "").replace(past_svc, past_resolved)
            return 1.0 if norm_past == norm_sig_trigger else 0.5

        matches = [
            {
                "incident_id": past["incident_id"],
                "similarity":  _get_similarity(past),
                "rationale":   f"resolved service '{resolved_svc}'",
            }
            for past in self.all_incident_signals
            if past["incident_id"] != signal["incident_id"] and self._resolve(past.get("service", "")) == resolved_svc
        ]
        
        # Sort by similarity, then recency
        matches.sort(key=lambda m: m["similarity"], reverse=True)
        matches = matches[:5]

        suggestions = []
        for m in matches:
            rem = self.remediations.get(m["incident_id"])
            if rem:
                suggestions.append({
                    "action":             rem["action"],
                    "target":             rem.get("target", svc),
                    "historical_outcome": rem.get("outcome", "unknown"),
                    "confidence":         0.8 if m["similarity"] > 0.8 else 0.3,
                })
                break

        return {
            "related_events":         related,
            "causal_chain":           [],
            "similar_past_incidents": matches,
            "suggested_remediations": suggestions,
            "confidence":             0.8,
            "explain":                f"resolved '{svc}' to '{resolved_svc}'",
        }

    def close(self) -> None:
        self.events.clear()
        self.by_resolved_service.clear()
        self.all_incident_signals.clear()
        self.remediations.clear()
        self.renames.clear()
