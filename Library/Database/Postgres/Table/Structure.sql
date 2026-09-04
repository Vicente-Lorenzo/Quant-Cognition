WITH expected_structure(column_name, data_type, is_pk, is_fk) AS (
    VALUES
    ::definitions::
),
actual_structure AS (
    SELECT
        c.column_name,
        c.data_type,
        CASE WHEN pk.column_name IS NOT NULL THEN 1 ELSE 0 END AS is_pk,
        CASE WHEN fk.column_name IS NOT NULL THEN 1 ELSE 0 END AS is_fk
    FROM information_schema.columns c
    LEFT JOIN (
        SELECT kcu.column_name
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu
          ON tc.constraint_name = kcu.constraint_name
         AND tc.table_schema = kcu.table_schema
        WHERE tc.constraint_type = 'PRIMARY KEY'
          AND tc.table_schema = '::schema::'
          AND tc.table_name = '::table::'
    ) pk ON c.column_name = pk.column_name
    LEFT JOIN (
        SELECT kcu.column_name
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu
          ON tc.constraint_name = kcu.constraint_name
         AND tc.table_schema = kcu.table_schema
        WHERE tc.constraint_type = 'FOREIGN KEY'
          AND tc.table_schema = '::schema::'
          AND tc.table_name = '::table::'
    ) fk ON c.column_name = fk.column_name
    WHERE c.table_schema = '::schema::'
      AND c.table_name   = '::table::'
)
SELECT
    e.column_name AS expected_column_name,
    e.data_type   AS expected_data_type,
    a.column_name AS actual_column_name,
    a.data_type   AS actual_data_type
FROM expected_structure e
FULL OUTER JOIN actual_structure a
  ON e.column_name = a.column_name
 AND e.data_type   = a.data_type
 AND e.is_pk       = a.is_pk
 AND e.is_fk       = a.is_fk
WHERE a.column_name IS NULL OR e.column_name IS NULL;
