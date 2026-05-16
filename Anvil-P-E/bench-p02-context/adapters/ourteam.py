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
        res_svc = self._resolve(svc)
        
        # Match purely by resolved service
        matches = []
        for past in self.all_incident_signals:
            if past["incident_id"] == signal["incident_id"]:
                continue
            if self._resolve(past.get("service", "")) == res_svc:
                matches.append({
                    "incident_id": past["incident_id"],
                    "similarity":  1.0,
                    "rationale":   "same service",
                })
        
        matches = matches[:5]

        suggestions = []
        seen_actions = set()
        for m in matches:
            rem = self.remediations.get(m["incident_id"])
            if rem and rem["action"] not in seen_actions:
                suggestions.append({
                    "action":             rem["action"],
                    "target":             rem.get("target", svc),
                    "historical_outcome": rem.get("outcome", "unknown"),
                    "confidence":         0.8,
                })
                seen_actions.add(rem["action"])

        return {
            "related_events":         [],
            "causal_chain":           [],
            "similar_past_incidents": matches,
            "suggested_remediations": suggestions,
            "confidence":             0.8,
            "explain":                "brute force",
        }

    def close(self) -> None:
        self.events.clear()
        self.by_resolved_service.clear()
        self.all_incident_signals.clear()
        self.remediations.clear()
        self.renames.clear()
