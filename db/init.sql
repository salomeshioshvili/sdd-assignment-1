IF DB_ID(N'log_db') IS NULL
    CREATE DATABASE log_db;
GO

IF DB_ID(N'insights_db') IS NULL
    CREATE DATABASE insights_db;
GO

IF NOT EXISTS (SELECT 1 FROM sys.sql_logins WHERE name = N'log_user')
    CREATE LOGIN log_user WITH PASSWORD = N'Log_Passw0rd1';
GO

IF NOT EXISTS (SELECT 1 FROM sys.sql_logins WHERE name = N'insights_user')
    CREATE LOGIN insights_user WITH PASSWORD = N'Insights_Passw0rd1';
GO

USE log_db;
GO
IF NOT EXISTS (SELECT 1 FROM sys.database_principals WHERE name = N'log_user')
BEGIN
    CREATE USER log_user FOR LOGIN log_user;
    ALTER ROLE db_owner ADD MEMBER log_user;
END
GO

USE insights_db;
GO
IF NOT EXISTS (SELECT 1 FROM sys.database_principals WHERE name = N'insights_user')
BEGIN
    CREATE USER insights_user FOR LOGIN insights_user;
    ALTER ROLE db_owner ADD MEMBER insights_user;
END
GO
