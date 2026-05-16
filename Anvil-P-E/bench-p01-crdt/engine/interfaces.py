from __future__ import annotations
from dataclasses import dataclass
from typing import Any

__all__ = ["VectorClockData", "CRDTCellData", "CRDTRowData", "EscrowClaim"]

@dataclass
class VectorClockData:
    clock: dict[str, int]

@dataclass
class CRDTCellData:
    value: Any
    clock: VectorClockData
    conflicts: list[tuple[Any, VectorClockData]]

@dataclass
class CRDTRowData:
    cells: dict[str, CRDTCellData]
    tombstone: bool = False
    tombstone_clock: VectorClockData | None = None
    fk_status: str = "ok"
    unique_status: str = "pending"

@dataclass
class EscrowClaim:
    table: str
    col: str
    val: Any
    peer_id: str
    row_pk: Any
