from __future__ import annotations
from engine.vector_clock import VectorClock
from engine.crdt_cell import CRDTCell

class CRDTRow:
    def __init__(
        self,
        cells: dict[str, CRDTCell],
        tombstone: bool = False,
        tombstone_clock: VectorClock | None = None,
        fk_status: str = "ok",
        unique_status: str = "pending"
    ):
        self.cells = cells
        self.tombstone = tombstone
        self.tombstone_clock = tombstone_clock
        self.fk_status = fk_status
        self.unique_status = unique_status

    def merge(self, other: 'CRDTRow') -> 'CRDTRow':
        # Merge cells independently
        merged_cells = {}
        all_cols = set(self.cells.keys()).union(set(other.cells.keys()))
        
        for col in all_cols:
            if col in self.cells and col in other.cells:
                merged_cells[col] = self.cells[col].merge(other.cells[col])
            elif col in self.cells:
                merged_cells[col] = self.cells[col]
            else:
                merged_cells[col] = other.cells[col]
                
        # Tombstone is monotonic
        merged_tombstone = self.tombstone or other.tombstone
        
        # Merge tombstone_clock
        if self.tombstone_clock and other.tombstone_clock:
            merged_tombstone_clock = self.tombstone_clock.merge(other.tombstone_clock)
        else:
            merged_tombstone_clock = self.tombstone_clock or other.tombstone_clock
            
        # fk_status propagation
        merged_fk = "orphaned" if self.fk_status == "orphaned" or other.fk_status == "orphaned" else "ok"
        
        # unique_status resolution
        statuses = {self.unique_status, other.unique_status}
        if "rejected" in statuses:
            merged_unique = "rejected"
        elif "committed" in statuses:
            merged_unique = "committed"
        else:
            merged_unique = "pending"
            
        return CRDTRow(
            cells=merged_cells,
            tombstone=merged_tombstone,
            tombstone_clock=merged_tombstone_clock,
            fk_status=merged_fk,
            unique_status=merged_unique
        )

    def is_visible(self, fk_policy: str = "cascade") -> bool:
        # A row is visible if it's not tombstoned.
        if self.tombstone:
            return False
        
        # If cascading delete is enabled, orphans are hidden.
        if fk_policy == "cascade" and self.fk_status == "orphaned":
            return False
            
        return True

    def snapshot(self, unique_cols: list[str] = None, 
                 fk_cols: list[str] = None, 
                 fk_policy: str = "cascade") -> dict:
        row_dict = {}
        unique_set = set(unique_cols or [])
        fk_set = set(fk_cols or [])
        
        for col, cell in self.cells.items():
            val = cell.winner_value()
            
            # Uniqueness rejection: nullify unique columns
            if self.unique_status == "rejected" and col in unique_set:
                row_dict[col] = None
            # Orphan policy: nullify FK columns if row is orphaned
            elif fk_policy == "orphan" and self.fk_status == "orphaned" and col in fk_set:
                row_dict[col] = None
            else:
                row_dict[col] = val
        return row_dict


if __name__ == '__main__':
    # Unit Tests
    
    vc1 = VectorClock({'A': 1})
    vc2 = VectorClock({'B': 1})
    
    cell_a = CRDTCell("apple", vc1)
    cell_b = CRDTCell("banana", vc2)
    
    # 1. Test cell-merge preserves both updates
    row1 = CRDTRow(cells={"col1": cell_a}, unique_status="committed")
    row2 = CRDTRow(cells={"col2": cell_b}, unique_status="committed")
    
    merged_row = row1.merge(row2)
    assert "col1" in merged_row.cells and "col2" in merged_row.cells, "Cell merge missing columns"
    assert merged_row.cells["col1"].winner_value() == "apple", "Cell merge column 1 failed"
    assert merged_row.cells["col2"].winner_value() == "banana", "Cell merge column 2 failed"
    
    # 2. Test tombstone monotonicity
    row3 = CRDTRow(cells={"col1": cell_a}, tombstone=False)
    row4 = CRDTRow(cells={"col1": cell_a}, tombstone=True, tombstone_clock=vc1)
    
    merged_tombstone = row3.merge(row4)
    assert merged_tombstone.tombstone is True, "Tombstone monotonicity failed (False merge True)"
    
    merged_tombstone_rev = row4.merge(row3)
    assert merged_tombstone_rev.tombstone is True, "Tombstone monotonicity failed (True merge False)"
    
    # 3. Test fk_status propagation
    row5 = CRDTRow(cells={"col1": cell_a}, fk_status="ok")
    row6 = CRDTRow(cells={"col1": cell_a}, fk_status="orphaned")
    
    merged_fk = row5.merge(row6)
    assert merged_fk.fk_status == "orphaned", "fk_status propagation failed"

    print("All CRDTRow unit tests passed!")
