import re
import sqlglot

def _extract_literal_value(expr):
    if isinstance(expr, sqlglot.exp.Literal):
        if expr.is_string:
            return expr.this
        else:
            try:
                return float(expr.this) if '.' in expr.this else int(expr.this)
            except ValueError:
                return expr.this
    elif isinstance(expr, sqlglot.exp.Null):
        return None
    elif isinstance(expr, sqlglot.exp.Boolean):
        return expr.this
    else:
        return expr.name

def parse_sql(sql: str, params: tuple = ()) -> dict:
    # Handle ? substitution BEFORE parsing
    parts = sql.split('?')
    if len(parts) - 1 != len(params):
        raise ValueError("Number of ? placeholders does not match number of parameters.")
    
    substituted_sql = parts[0]
    for i, param in enumerate(params):
        if isinstance(param, str):
            val = f"'{param.replace(chr(39), chr(39)+chr(39))}'"
        elif param is None:
            val = "NULL"
        else:
            val = str(param)
        substituted_sql += val + parts[i+1]
        
    sql_stmt = substituted_sql.strip()

    # Regex fallback for CREATE TABLE
    if sql_stmt.upper().startswith("CREATE TABLE"):
        match = re.match(r"CREATE\s+TABLE\s+(\w+)\s*\((.*)\)", sql_stmt, re.IGNORECASE | re.DOTALL)
        if match:
            table_name = match.group(1)
            columns_str = match.group(2)
            
            # Simple split by comma (assuming no commas inside parens in column defs)
            col_defs = [c.strip() for c in columns_str.split(',')]
            columns = []
            for cdef in col_defs:
                if not cdef:
                    continue
                c_parts = cdef.split()
                name = c_parts[0]
                type_str = c_parts[1] if len(c_parts) > 1 else "VARCHAR"
                cdef_upper = cdef.upper()
                primary_key = "PRIMARY KEY" in cdef_upper
                unique = "UNIQUE" in cdef_upper
                not_null = "NOT NULL" in cdef_upper
                
                references = None
                ref_match = re.search(r"REFERENCES\s+(\w+)", cdef, re.IGNORECASE)
                if ref_match:
                    references = ref_match.group(1)
                
                columns.append({
                    "name": name,
                    "type": type_str,
                    "primary_key": primary_key,
                    "unique": unique,
                    "not_null": not_null,
                    "references": references
                })
            return {
                "op": "create_table",
                "table": table_name,
                "columns": columns
            }

    # Regex fallback for CREATE INDEX
    if sql_stmt.upper().startswith("CREATE INDEX"):
        match = re.match(r"CREATE\s+INDEX\s+(\w+)\s+ON\s+(\w+)\s*\((.*?)\)", sql_stmt, re.IGNORECASE)
        if match:
            idx_name = match.group(1)
            table_name = match.group(2)
            cols = [c.strip() for c in match.group(3).split(',')]
            return {
                "op": "create_index",
                "index_name": idx_name,
                "table": table_name,
                "columns": cols
            }

    # Use sqlglot for INSERT / UPDATE / DELETE
    try:
        expr = sqlglot.parse_one(sql_stmt)
    except Exception as e:
        raise ValueError(f"Failed to parse SQL: {sql_stmt} - {e}")

    if isinstance(expr, sqlglot.exp.Insert):
        table = expr.find(sqlglot.exp.Table).name
        cols = []
        schema = expr.find(sqlglot.exp.Schema)
        if schema:
            cols = [c.name for c in schema.expressions]
            
        values = []
        tuple_expr = expr.find(sqlglot.exp.Tuple)
        if tuple_expr:
            for v in tuple_expr.expressions:
                values.append(_extract_literal_value(v))
                
        return {
            "op": "insert",
            "table": table,
            "columns": cols,
            "values": values
        }

    elif isinstance(expr, sqlglot.exp.Update):
        table = expr.find(sqlglot.exp.Table).name
        set_clauses = {}
        for set_expr in expr.expressions:
            col = set_expr.left.name
            val = _extract_literal_value(set_expr.right)
            set_clauses[col] = val
            
        where = expr.find(sqlglot.exp.Where)
        where_pk = None
        if where:
            cond = where.this
            if isinstance(cond, sqlglot.exp.EQ):
                where_pk = _extract_literal_value(cond.right)
                
        return {
            "op": "update",
            "table": table,
            "set_clauses": set_clauses,
            "where_pk": where_pk
        }

    elif isinstance(expr, sqlglot.exp.Delete):
        table = expr.find(sqlglot.exp.Table).name
        where = expr.find(sqlglot.exp.Where)
        where_pk = None
        if where:
            cond = where.this
            if isinstance(cond, sqlglot.exp.EQ):
                where_pk = _extract_literal_value(cond.right)
                
        return {
            "op": "delete",
            "table": table,
            "where_pk": where_pk
        }

    raise ValueError(f"Unsupported SQL operation: {sql_stmt}")


if __name__ == '__main__':
    # Tests
    
    # CREATE TABLE
    ct_sql = "CREATE TABLE users (id varchar primary key, email varchar unique, org_id varchar references orgs)"
    res = parse_sql(ct_sql)
    assert res['op'] == 'create_table'
    assert res['table'] == 'users'
    assert len(res['columns']) == 3
    assert res['columns'][0]['name'] == 'id'
    assert res['columns'][0]['primary_key'] is True
    assert res['columns'][2]['references'] == 'orgs'

    # CREATE INDEX
    ci_sql = "CREATE INDEX idx_email ON users (email)"
    res = parse_sql(ci_sql)
    assert res['op'] == 'create_index'
    assert res['table'] == 'users'
    assert res['columns'] == ['email']

    # INSERT
    ins_sql = "INSERT INTO users (id, email) VALUES (?, ?)"
    res = parse_sql(ins_sql, ("u1", "u1@example.com"))
    assert res['op'] == 'insert'
    assert res['table'] == 'users'
    assert res['columns'] == ['id', 'email']
    assert res['values'] == ['u1', 'u1@example.com']

    # UPDATE
    upd_sql = "UPDATE users SET email=? WHERE id=?"
    res = parse_sql(upd_sql, ("new@example.com", "u1"))
    assert res['op'] == 'update'
    assert res['set_clauses'] == {'email': 'new@example.com'}
    assert res['where_pk'] == 'u1'

    # DELETE
    del_sql = "DELETE FROM users WHERE id=?"
    res = parse_sql(del_sql, ("u1",))
    assert res['op'] == 'delete'
    assert res['table'] == 'users'
    assert res['where_pk'] == 'u1'

    print("All SQL Parser unit tests passed!")
