from typing import Any

class FKEnforcer:
    def on_parent_delete(self, store, table: str, pk: Any) -> None:
        # Find all tables that have a FK referencing 'table'
        for child_table, schema_info in store.schema.items():
            fk_cols = schema_info.get("fk_cols", {})
            for fk_col, parent_table in fk_cols.items():
                if parent_table == table:
                    # Scan all rows in child table
                    child_rows = store.tables.get(child_table, {})
                    for child_pk, row in list(child_rows.items()):
                        if fk_col in row.cells:
                            if row.cells[fk_col].winner_value() == pk:
                                row.fk_status = "orphaned"
                                store.upsert_row(child_table, child_pk, row)

    def on_child_insert(self, store, table: str, row_dict: dict) -> None:
        schema_info = store.schema.get(table, {})
        fk_cols = schema_info.get("fk_cols", {})
        
        if not fk_cols:
            return
            
        for fk_col, parent_table in fk_cols.items():
            if fk_col in row_dict:
                parent_pk = row_dict[fk_col]
                
                # Check if parent exists and is tombstoned
                parent_rows = store.tables.get(parent_table, {})
                parent_row = parent_rows.get(parent_pk)
                
                if parent_row is not None and parent_row.tombstone:
                    pk_col = schema_info.get("pk_col")
                    if not pk_col and row_dict:
                        pk_col = list(row_dict.keys())[0]
                        
                    if pk_col and pk_col in row_dict:
                        child_pk = row_dict[pk_col]
                        child_row = store.tables.get(table, {}).get(child_pk)
                        if child_row:
                            child_row.fk_status = "orphaned"
                            store.upsert_row(table, child_pk, child_row)

    def recheck_all(self, store) -> None:
        # After sync, re-validate all FK relationships for out-of-order arrivals
        for child_table, schema_info in store.schema.items():
            fk_cols = schema_info.get("fk_cols", {})
            if not fk_cols:
                continue
                
            child_rows = store.tables.get(child_table, {})
            for fk_col, parent_table in fk_cols.items():
                parent_rows = store.tables.get(parent_table, {})
                
                for child_pk, child_row in list(child_rows.items()):
                    if fk_col in child_row.cells:
                        parent_pk = child_row.cells[fk_col].winner_value()
                        parent_row = parent_rows.get(parent_pk)
                        
                        if parent_row is not None and parent_row.tombstone:
                            if child_row.fk_status != "orphaned":
                                child_row.fk_status = "orphaned"
                                store.upsert_row(child_table, child_pk, child_row)
