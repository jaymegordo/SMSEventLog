-- list of roles
-- https://docs.microsoft.com/en-us/sql/relational-databases/security/authentication-access/database-level-roles?view=sql-server-ver15
-- DECLARE @user VARCHAR(MAX) = 'jgordon@smsequip.com'

-- print @user
-- CREATE USER [jgordon@smsequip.com] FROM EXTERNAL PROVIDER;
-- need to add user to correct role so they can see tables/query data
-- ALTER ROLE db_datawriter ADD MEMBER [mhonarkhah@smsequip.com];
ALTER ROLE db_owner ADD MEMBER [jgordon@smsequip.com]; 
-- ALTER ROLE db_accessadmin ADD MEMBER [mhonarkhah@smsequip.com];
-- DECLARE @S NVARCHAR(MAX)

-- SET @S = 'ALTER ROLE db_owner ADD MEMBER ' + quotename(@user)

-- EXEC (@S)
