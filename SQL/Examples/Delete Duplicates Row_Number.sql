DELETE FROM b 
    FROM (
    SELECT
        a.*,
        ROW_NUMBER() OVER (Partition By Unit, [Start Date] Order By Unit, [End Date]) as rn
    FROM DowntimeExport a) b 
WHERE b.rn > 1