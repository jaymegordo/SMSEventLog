ALTER FUNCTION udfServiceCount (
    @DateLower DATE
)

RETURNS TABLE
AS
RETURN

WITH c1 as (
    SELECT 
        a.Unit,
        a.CategoryAssigned,
        a.Duration,
        a.StartDate,
        a.EndDate, 
        CASE
            WHEN DATEDIFF(Hour, LAG(a.StartDate, 1) OVER (PARTITION BY a.Unit ORDER BY a.Unit, a.StartDate), a.StartDate) <= 48 THEN 0
            ELSE 1
        END as isstart

    FROM Downtime a INNER JOIN UnitID b ON a.Unit=b.Unit
    WHERE
        a.CategoryAssigned Like '%Service%' and
        a.StartDate >= @DateLower and
        a.StartDate < DATEADD(DAY, -7, CONVERT(DATE, GETDATE())) and
        b.MineSite = 'FortHills'
),
c2 as (
    SELECT
        *,
        SUM(c1.isstart) OVER (PARTITION BY c1.Unit ORDER BY c1.Unit, c1.StartDate ROWS UNBOUNDED PRECEDING) as grp
    From c1
), 
c3 as (
    SELECT
        c2.Unit,
        c2.CategoryAssigned,
        SUM(c2.Duration) as Duration,
        c2.grp
    FROM c2
    GROUP BY c2.Unit, c2.CategoryAssigned, c2.grp
)
SELECT c3.Unit, SUM(CASE WHEN c3.CategoryAssigned='S4 Service' THEN 1 ELSE 0 END) as S4, SUM(CASE WHEN c3.CategoryAssigned='S5 Service' THEN 1 ELSE 0 END) as S5 
From c3
Group By c3.Unit
;