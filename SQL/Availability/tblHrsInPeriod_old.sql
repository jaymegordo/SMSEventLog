SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
ALTER FUNCTION [dbo].[tblHrsInPeriod](
    @DateLower DATE,
    @DateUpper DATE,
    @MineSite VARCHAR(255))

RETURNS TABLE
AS
RETURN

-- Return Unit and sum of total hrs in system and excluded from system within specified period

SELECT
    t.Unit,
    DATEDIFF(hour, t.MinDate, @DateUpper) - t.ExcludeHours_MA + 24 as HrsPeriod_MA,
    t.ExcludeHours_MA,
    DATEDIFF(hour, t.MinDate, @DateUpper) - t.ExcludeHours_PA + 24 as HrsPeriod_PA,
    t.ExcludeHours_PA

FROM (
    SELECT
        a.Unit,
        CASE WHEN @DateLower < a.DeliveryDate THEN a.DeliveryDate ELSE @DateLower END as MinDate,
        ISNULL(b.ExcludeHours_MA, 0) as ExcludeHours_MA,
        ISNULL(b.ExcludeHours_PA, 0) as ExcludeHours_PA

    FROM UnitID a
        LEFT JOIN (
            SELECT 
                c.Unit,
                SUM(IIF(c.MA = 1, c.Hours, 0)) as ExcludeHours_MA,
                SUM(c.Hours) as ExcludeHours_PA
            FROM
                DowntimeExclusions c
            WHERE
                c.Date BETWEEN @DateLower AND @DateUpper
            GROUP BY c.Unit
        ) b on a.Unit=b.Unit

    WHERE
        a.MineSite = @MineSite
    ) t
GO