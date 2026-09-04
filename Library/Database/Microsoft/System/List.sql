SELECT
    d.name AS [Database],
    t.table_schema AS [Schema],
    t.table_name AS [Table]
FROM sys.databases d
LEFT JOIN information_schema.tables t ON t.table_catalog = d.name
WHERE d.name LIKE :database:
  AND (t.table_schema LIKE :schema: OR (:schema: = '%%' AND t.table_schema IS NULL))
  AND (t.table_name LIKE :table: OR (:table: = '%%' AND t.table_name IS NULL))
  AND (:system: = 1 OR (
      d.name NOT IN ('master', 'tempdb', 'model', 'msdb')
      AND COALESCE(t.table_schema, '') NOT IN ('sys', 'INFORMATION_SCHEMA', 'guest', 'db_owner', 'db_securityadmin', 'db_accessadmin', 'db_backupoperator', 'db_ddladmin', 'db_datawriter', 'db_datareader', 'db_denydatawriter', 'db_denydatareader')
  ));