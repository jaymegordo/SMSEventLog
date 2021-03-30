SELECT schema_name(tab.schema_id) + '.' + tab.name AS [table],
	cast(sum(spc.used_pages * 8) / 1024.00 AS NUMERIC(36, 2)) AS used_mb,
	cast(sum(spc.total_pages * 8) / 1024.00 AS NUMERIC(36, 2)) AS allocated_mb
FROM sys.tables tab
INNER JOIN sys.indexes ind
	ON tab.object_id = ind.object_id
INNER JOIN sys.partitions part
	ON ind.object_id = part.object_id
		AND ind.index_id = part.index_id
INNER JOIN sys.allocation_units spc
	ON part.partition_id = spc.container_id
GROUP BY schema_name(tab.schema_id) + '.' + tab.name
ORDER BY sum(spc.used_pages) DESC
