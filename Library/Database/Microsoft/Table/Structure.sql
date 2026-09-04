WITH expected_structure(column_name, data_type, is_pk, is_fk) AS (
    SELECT v.column_name, v.data_type, v.is_pk, v.is_fk
    FROM (VALUES
    ::definitions::
    ) AS v(column_name, data_type, is_pk, is_fk)
),
actual_structure AS (
    SELECT
        c.column_name,
        c.data_type,
        CASE WHEN pk.COLUMN_NAME IS NOT NULL THEN 1 ELSE 0 END AS is_pk,
        CASE WHEN fk.COLUMN_NAME IS NOT NULL THEN 1 ELSE 0 END AS is_fk
    FROM information_schema.columns c
    LEFT JOIN (
        SELECT kcu.COLUMN_NAME
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu
          ON tc.CONSTRAINT_NAME = kcu.CONSTRAINT_NAME
         AND tc.TABLE_SCHEMA = kcu.TABLE_SCHEMA
        WHERE tc.CONSTRAINT_TYPE = 'PRIMARY KEY'
          AND tc.TABLE_SCHEMA = '::schema::'
          AND tc.TABLE_NAME = '::table::'
    ) pk ON c.column_name = pk.COLUMN_NAME
    LEFT JOIN (
        SELECT kcu.COLUMN_NAME
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu
          ON tc.CONSTRAINT_NAME = kcu.CONSTRAINT_NAME
         AND tc.TABLE_SCHEMA = kcu.TABLE_SCHEMA
        WHERE tc.CONSTRAINT_TYPE = 'FOREIGN KEY'
          AND tc.TABLE_SCHEMA = '::schema::'
          AND tc.TABLE_NAME = '::table::'
    ) fk ON c.column_name = fk.COLUMN_NAME
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
