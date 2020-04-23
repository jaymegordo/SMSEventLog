SELECT * FROM (
    SELECT
        a.FCNumber,
        a.Unit,
        a.Serial,
        a.Model,
        ROW_NUMBER() OVER (
            Partition By a.FCNumber, a.Unit
            ORDER BY a.FCNumber, a.Unit) as rn
    FROM FactoryCampaign a) b
WHERE b.rn > 1