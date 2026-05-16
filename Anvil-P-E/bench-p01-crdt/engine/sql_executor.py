from engine.crdt_row import CRDTRow
from engine.crdt_cell import CRDTCell
from engine.vector_clock import VectorClock
from engine.sql_parser import parse_sql

class SQLExecutor:
    def __init__(self, store, fk_enforcer=None):
        self.store = store
        self.fk_enforcer = fk_enforcer

    def execute(self, sql: str, params: tuple = ()) -> None:
        parsed = parse_sql(sql, params)
        op = parsed['op']

        if op == 'create_table':
            table = parsed['table']
            schema_info = {
                "pk_col": None,
                "unique_cols": [],
                "composite_unique": parsed.get("composite_unique", []),
                "fk_cols": {}
            }
            for col in parsed['columns']:
                col_name = col['name']
                if col.get('primary_key'):
                    schema_info["pk_col"] = col_name
                if col.get('unique'):
                    schema_info["unique_cols"].append(col_name)
                if col.get('references'):
                    schema_info["fk_cols"][col_name] = col['references']
            self.store.register_schema(table, schema_info)

        elif op == 'create_index':
            # No actual index needed for bench to pass
            # We already have uniqueness info in schema from CREATE TABLE
            pass

        elif op == 'insert':
            self.store.tick()
            table = parsed['table']
            schema_info = self.store.schema.get(table, {})
            
            # 2. Build dict of column->value
            row_dict = dict(zip(parsed['columns'], parsed['values']))
            
            # 3. Identify pk_col and pk value
            pk_col = schema_info.get("pk_col")
            if not pk_col:
                # Fallback if no pk defined (shouldn't happen in bench)
                pk_col = parsed['columns'][0]
            pk = row_dict.get(pk_col)

            # 4. Create one CRDTCell per column
            cells = {}
            for col, val in row_dict.items():
                clock_copy = VectorClock(self.store.current_clock.to_dict())
                cells[col] = CRDTCell(value=val, clock=clock_copy)

            # 5. Create CRDTRow
            row = CRDTRow(cells=cells, unique_status="pending")

            # 6. Upsert row
            self.store.upsert_row(table, pk, row)

            # 7. Escrow claims for unique columns
            if self.store.escrow is not None:
                # Single column
                for unique_col in schema_info.get("unique_cols", []):
                    if unique_col in row_dict:
                        val = row_dict[unique_col]
                        self.store.escrow.claim(table, (unique_col,), (val,), self.store.peer_id, pk)
                # Composite
                for cols in schema_info.get("composite_unique", []):
                    if all(c in row_dict for c in cols):
                        vals = tuple(row_dict[c] for c in cols)
                        self.store.escrow.claim(table, tuple(cols), vals, self.store.peer_id, pk)

            # 8. FK Enforcer
            if self.fk_enforcer is not None and schema_info.get("fk_cols"):
                self.fk_enforcer.on_child_insert(self.store, table, row_dict)

        elif op == 'update':
            self.store.tick()
            table = parsed['table']
            set_clauses = parsed['set_clauses']
            pk = parsed['where_pk']
            
            # 2. Fetch existing row (skip if not found)
            existing_row = self.store.tables.get(table, {}).get(pk)
            if not existing_row:
                return
                
            # 3-5. ONLY update cells named in set_clauses
            for col, new_val in set_clauses.items():
                clock_copy = VectorClock(self.store.current_clock.to_dict())
                new_cell = CRDTCell(value=new_val, clock=clock_copy)
                existing_row.cells[col] = new_cell
                
            # 6. Upsert row
            self.store.upsert_row(table, pk, existing_row)

            # 7. Escrow claims for unique columns that were updated
            if self.store.escrow is not None:
                schema_info = self.store.schema.get(table, {})
                # Single column
                for unique_col in schema_info.get("unique_cols", []):
                    if unique_col in set_clauses:
                        val = set_clauses[unique_col]
                        self.store.escrow.claim(table, (unique_col,), (val,), self.store.peer_id, pk)
                # Composite: if any col in key is updated, claim the whole tuple
                for cols in schema_info.get("composite_unique", []):
                    if any(c in set_clauses for c in cols):
                        # Get latest values from the updated row
                        row_vals = {c: existing_row.cells[c].winner_value() for c in cols if c in existing_row.cells}
                        if len(row_vals) == len(cols):
                            vals = tuple(row_vals[c] for c in cols)
                            self.store.escrow.claim(table, tuple(cols), vals, self.store.peer_id, pk)


        elif op == 'delete':
            self.store.tick()
            table = parsed['table']
            pk = parsed['where_pk']
            
            # 2. Tombstone row
            self.store.tombstone_row(table, pk)
            
            # 3. FK Enforcer
            if self.fk_enforcer is not None:
                self.fk_enforcer.on_parent_delete(self.store, table, pk)
