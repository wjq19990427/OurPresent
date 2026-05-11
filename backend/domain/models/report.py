"""Weekly report domain model."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass(slots=True)
class Report:
    report_id: str
    couple_id: str
    window_start: str
    window_end: str
    generated_at: str
    model_version: str
    footprint: dict = field(default_factory=dict)
    weather: dict = field(default_factory=dict)
    resonance: list[dict] = field(default_factory=list)
    suspense: list[dict] = field(default_factory=list)
    status: str = "ready"
    source_session_ids: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> "Report":
        return cls(
            report_id=data["report_id"],
            couple_id=data["couple_id"],
            window_start=data["window_start"],
            window_end=data["window_end"],
            generated_at=data["generated_at"],
            model_version=data.get("model_version", ""),
            footprint=dict(data.get("footprint", {})),
            weather=dict(data.get("weather", {})),
            resonance=list(data.get("resonance", [])),
            suspense=list(data.get("suspense", [])),
            status=data.get("status", "ready"),
            source_session_ids=list(data.get("source_session_ids", [])),
        )

    def to_dict(self) -> dict:
        return asdict(self)
