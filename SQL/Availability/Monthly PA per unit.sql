SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO

CREATE VIEW [dbo].[viewPAMonthly]
AS 

SELECT
    d.*,
    DATEDIFF(hh, d.MonthStart, d.MonthEnd) as Hrs_Period,
    1 - (d.Sum_DT / DATEDIFF(hh, d.MonthStart, d.MonthEnd)) as PA
FROM (
    SELECT 
        DATEFROMPARTS(c.Year, c.Month, 1) as MonthStart,
        DATEADD(m, 1, DATEFROMPARTS(c.Year, c.Month, 1)) as MonthEnd,
        c.*
    FROM (
        SELECT 
            YEAR(a.StartDate) as [Year],
            MONTH(a.StartDate) as [Month],
            a.Unit,
            SUM(a.Duration) as Sum_DT

        FROM Downtime a
            LEFT JOIN UnitID b on a.Unit=b.Unit

        WHERE
            a.StartDate>'2018-06-01' and
            b.MineSite='FortHIlls' and
            b.AHSStart Is NOT NULL

        GROUP BY YEAR(a.StartDate), MONTH(a.StartDate), a.Unit) c) d
-- ORDER BY t.Year, t.Month, t.Unit

GO