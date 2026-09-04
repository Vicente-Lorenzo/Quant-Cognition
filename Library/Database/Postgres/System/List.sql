SELECT
    d.datname AS "Database",
    t.table_schema AS "Schema",
    t.table_name AS "Table"
FROM pg_database d
LEFT JOIN information_schema.tables t ON t.table_catalog = d.datname
WHERE d.datname LIKE :database:
  AND (t.table_schema LIKE :schema: OR (:schema: = '%%' AND t.table_schema IS NULL))
  AND (t.table_name LIKE :table: OR (:table: = '%%' AND t.table_name IS NULL))
  AND (:system: = 1 OR (
      d.datname NOT IN ('postgres') AND d.datname NOT LIKE 'template%%'
      AND COALESCE(t.table_schema, '') NOT IN ('pg_catalog', 'information_schema')
  ));