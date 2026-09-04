SELECT
    DB_NAME() AS [Database],
    s.name AS [Schema],
    t.name AS [Table],
    SUM(a.total_pages) * 8192 AS [Size],
    CAST(SUM(a.total_pages) * 8 / 1024.0 AS NVARCHAR(100)) + ' MB' AS [Formatted]
FROM sys.tables t
JOIN sys.schemas s ON t.schema_id = s.schema_id
JOIN sys.indexes i ON t.object_id = i.object_id
JOIN sys.partitions p ON i.object_id = p.object_id AND i.index_id = p.index_id
JOIN sys.allocation_units a ON p.partition_id = a.container_id
WHERE s.name LIKE :schema:
  AND t.name LIKE :table:
GROUP BY s.name, t.name
ORDER BY [Size] DESC;