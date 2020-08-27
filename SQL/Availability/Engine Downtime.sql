WITH t1 as (
    SELECT
        YEAR(a.StartDate) as [Year],
        MONTH(a.StartDate) as [Month],
        SUM(a.Duration) as Total

    FROM Downtime a

    WHERE
        a.CategoryAssigned = 'Engine' and
        a.StartDate >= '2018-01-01'

    GROUP BY YEAR(a.StartDate), MONTH(a.StartDate))

SELECT
    CONCAT_WS('-', t1.Year, t1.Month) as Period,
    t1.Total

FROM t1

ORDER BY
    t1.Year, t1.Month