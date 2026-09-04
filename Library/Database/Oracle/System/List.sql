SELECT
    SYS_CONTEXT('USERENV', 'CON_NAME') AS "Database",
    u.username AS "Schema",
    t.table_name AS "Table"
FROM all_users u
LEFT JOIN all_tables t ON t.owner = u.username
WHERE SYS_CONTEXT('USERENV', 'CON_NAME') LIKE :database:
  AND u.username LIKE UPPER(CASE WHEN :schema: = '%%' THEN '%%' ELSE :schema: END)
  AND COALESCE(t.table_name, '') LIKE UPPER(CASE WHEN :table: = '%%' THEN '%%' ELSE :table: END)
  AND (:system: = 1 OR (
      u.username NOT IN ('SYS', 'SYSTEM', 'OUTLN', 'CTXSYS', 'XDB', 'AUDSYS', 'APPQOSSYS', 'DBSNMP', 'ORACLE_OCM', 'DBSFWUSER', 'OJVMSYS', 'WMSYS', 'ANONYMOUS', 'GSMCADMIN_INTERNAL', 'GSMADMIN_INTERNAL', 'GSMUSER', 'DIP', 'REMOTE_SCHEDULER_AGENT', 'SYSBACKUP', 'SYSDG', 'SYSKM', 'SYSMAC', 'SYS$UMF')
  ));