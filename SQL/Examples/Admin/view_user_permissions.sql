SELECT
    pr.name,
	pr.type_desc,
	r.name AS role_name,
	r.authentication_type_desc,
	pe.state_desc,
	pe.permission_name
FROM sys.database_principals AS pr
LEFT JOIN sys.database_role_members AS rm
	ON rm.member_principal_id = pr.principal_id
LEFT JOIN sys.database_principals AS r
	ON r.principal_id = rm.role_principal_id
LEFT JOIN sys.database_permissions AS pe
	ON pe.grantee_principal_id = pr.principal_id
WHERE pr.type NOT IN ('R', 'G')
ORDER BY pr.type_desc DESC,
	pr.name
