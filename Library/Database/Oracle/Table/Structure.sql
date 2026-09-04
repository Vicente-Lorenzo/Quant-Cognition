WITH expected_structure AS (
    ::definitions::
),
actual_structure AS (
    SELECT
        c.column_name,
        c.data_type,
        CASE WHEN pk.column_name IS NOT NULL THEN 1 ELSE 0 END AS is_pk,
        CASE WHEN fk.column_name IS NOT NULL THEN 1 ELSE 0 END AS is_fk
    FROM all_tab_columns c
    LEFT JOIN (
        SELECT cc.column_name
        FROM all_constraints ac
        JOIN all_cons_columns cc ON ac.constraint_name = cc.constraint_name AND ac.owner = cc.owner
        WHERE ac.constraint_type = 'P'
          AND ac.owner = UPPER('::schema::')
          AND ac.table_name = UPPER('::table::')
    ) pk ON c.column_name = pk.column_name
    LEFT JOIN (
        SELECT cc.column_name
        FROM all_constraints ac
        JOIN all_cons_columns cc ON ac.constraint_name = cc.constraint_name AND ac.owner = cc.owner
        WHERE ac.constraint_type = 'R'
          AND ac.owner = UPPER('::schema::')
          AND ac.table_name = UPPER('::table::')
    ) fk ON c.column_name = fk.column_name
    WHERE c.owner      = UPPER('::schema::')
      AND c.table_name = UPPER('::table::')
)
SELECT
    e.column_name AS expected_column_name,
    e.data_type   AS expected_data_type,
    a.column_name AS actual_column_name,
    a.data_type   AS actual_data_type
FROM expected_structure e
FULL OUTER JOIN actual_structure a
  ON UPPER(e.column_name) = UPPER(a.column_name)
 AND UPPER(e.data_type)   = UPPER(a.data_type)
 AND e.is_pk              = a.is_pk
 AND e.is_fk              = a.is_fk
WHERE a.column_name IS NULL OR e.column_name IS NULL;
