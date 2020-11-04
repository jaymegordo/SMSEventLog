SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
ALTER FUNCTION [dbo].[tblHrsInPeriod](
    @DateLower DATE,
    @DateUpper DATE,
    @MineSite VARCHAR(255),
    @period VARCHAR(10) = 'month')

RETURNS TABLE
AS
RETURN

-- Return Unit and sum of total hrs in system and excluded from system within specified period

SELECT
    -- need min and max date per group

    CASE WHEN @period = 'month' THEN
        CAST(YEAR(c.Date) as VARCHAR) + '-' + CAST(MONTH(c.Date) as VARCHAR)
        ELSE
        CAST(YEAR(c.Date) as VARCHAR) + '-' + CAST(DATEPART(week, c.Date) as VARCHAR)
    END as Period,

    c.Unit,
    ROUND(SUM(IIF(c.MA = 1, c.Hours, 0)), 0) as ExcludeHours_MA,
    ROUND(SUM(c.Hours), 0) as ExcludeHours_PA

FROM
    DowntimeExclusions c
    LEFT JOIN UnitID a on a.Unit=c.Unit

WHERE
    c.Date BETWEEN @DateLower AND @DateUpper and
    a.MineSite = @MineSite

GROUP BY
    c.Unit,

    CASE WHEN @period = 'month' THEN
        CAST(YEAR(c.Date) as VARCHAR) + '-' + CAST(MONTH(c.Date) as VARCHAR)
        ELSE
        CAST(YEAR(c.Date) as VARCHAR) + '-' + CAST(DATEPART(week, c.Date) as VARCHAR)
    END


GO
