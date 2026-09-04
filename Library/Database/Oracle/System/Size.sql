SELECT
    SYS_CONTEXT('USERENV', 'CON_NAME') AS "Database",
    owner AS "Schema",
    table_name AS "Table",
    num_rows * avg_row_len AS "Size",
    CAST(num_rows * avg_row_len AS VARCHAR2(100)) AS "Formatted"
FROM all_tables
WHERE owner LIKE UPPER(:schema:)
  AND table_name LIKE UPPER(:table:)
ORDER BY "Size" DESC;