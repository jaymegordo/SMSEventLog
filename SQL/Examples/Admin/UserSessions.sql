SELECT resource_type, resource_associated_entity_id,
    request_status,request_session_id, o.object_id, o.name, o.type_desc 
FROM sys.dm_tran_locks l, sys.objects o
WHERE l.resource_associated_entity_id = o.object_id
    and resource_database_id = DB_ID() and o.name='UserSettings'
order by request_session_id