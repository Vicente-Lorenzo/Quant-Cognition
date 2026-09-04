SELECT
    sys.dm_exec_sessions.session_id AS [Id],
    DB_NAME(sys.dm_exec_sessions.database_id) AS [Database],
    sys.dm_exec_sessions.login_name AS [User],
    sys.dm_exec_sessions.status AS [State],
    sys.dm_exec_requests.text AS [Query]
FROM sys.dm_exec_sessions
LEFT JOIN sys.dm_exec_requests ON sys.dm_exec_sessions.session_id = sys.dm_exec_requests.session_id
WHERE DB_NAME(sys.dm_exec_sessions.database_id) LIKE :database: AND sys.dm_exec_sessions.session_id <> @@SPID;