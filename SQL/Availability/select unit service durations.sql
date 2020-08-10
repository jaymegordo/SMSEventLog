DECLARE @datelower DATE;
set @datelower = '2019-01-01';

WITH c1 as (
    SELECT 
        a.Unit,
        a.CategoryAssigned,
        a.Duration,
        a.StartDate,
        a.EndDate, 
        CASE
            WHEN DATEDIFF(Hour, LAG(a.StartDate, 1) OVER (PARTITION BY a.Unit ORDER BY a.Unit, a.StartDate), a.StartDate) <= 96 THEN 0
            ELSE 1
        END as isstart

    FROM Downtime a INNER JOIN UnitID b ON a.Unit=b.Unit
    WHERE
        (a.CategoryAssigned = 'S4 Service' or a.CategoryAssigned = 'S5 Service') and
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
        MIN(c2.StartDate) as StartDate,
        MAX(c2.EndDate) as EndDate,
        c2.CategoryAssigned,
        SUM(c2.Duration) as Duration,
        c2.grp
    FROM c2
    GROUP BY c2.Unit, c2.CategoryAssigned, c2.grp
)

SELECT
    c3.Unit,
    CAST(c3.StartDate as DATE) as Date,
    c3.StartDate,
    c3.EndDate,
    c3.CategoryAssigned,
    CAST(c3.Duration as INT) as Duration_Category,
    DATEDIFF(Hour, c3.StartDate, c3.EndDate) as Duration_Start_End,
    CASE
        WHEN c3.StartDate > b.AHSStart and b.AHSStart IS NOT NULL
        THEN 'AHS'
        ELSE 'Staffed'
    END as Origin

FROM c3 LEFT JOIN UnitID b on c3.Unit=b.Unit
WHERE c3.Duration > 4
ORDER BY c3.Unit, c3.StartDate