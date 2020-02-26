ALTER FUNCTION udfServiceCount (
    @DateLower DATE
)

RETURNS TABLE
AS
RETURN

With C1 AS (
    Select a.Unit, CategoryAssigned, Duration, StartDate, EndDate, 
        CASE
            WHEN DATEDIFF(Hour, LAG(StartDate, 1) OVER (Partition By a.Unit Order By a.Unit, StartDate), StartDate) <= 48 THEN 0
            ELSE 1
        END As isstart
    From Downtime a Inner Join UnitID b On a.Unit=b.Unit
    Where CategoryAssigned Like '%Service%' and StartDate>=@DateLower and StartDate < DATEADD(DAY, -7, CONVERT(DATE, GETDATE())) and b.MineSite='FortHills'
),
C2 AS (
    Select *,
        SUM(isstart) OVER (Partition By Unit Order By Unit, StartDate ROWS UNBOUNDED PRECEDING) As grp
    From C1
), 
C3 AS (
    Select Unit, CategoryAssigned, SUM(Duration) as Duration, grp
    From C2
    Group By Unit, CategoryAssigned, grp
)
Select Unit, SUM(CASE WHEN CategoryAssigned='S4 Service' THEN 1 ELSE 0 END) As S4, SUM(CASE WHEN CategoryAssigned='S5 Service' THEN 1 ELSE 0 END) As S5 
From C3
Group By Unit
;