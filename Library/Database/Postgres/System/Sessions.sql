SELECT
    pid AS "Id",
    datname AS "Database",
    usename AS "User",
    state AS "State",
    query AS "Query"
FROM pg_stat_activity
WHERE datname LIKE :database: AND pid <> pg_backend_pid();