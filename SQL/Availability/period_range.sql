SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
ALTER FUNCTION [dbo].[period_range] (
    @startdate DATE,
    @enddate DATE,
    @period VARCHAR(10))

RETURNS @T TABLE (
    DateLower DATE,
    DateUpper DATE,
    period VARCHAR(20)) AS

BEGIN
-- Return table of period start/end/period_name between start/end dates for either week or month

DECLARE @start DATE

IF @period = 'month'
    BEGIN
        -- Init start date as first day of month
        SET @start = DATEADD(MONTH, DATEDIFF(MONTH, 0, @startdate), 0);
        
        WITH q AS (
            SELECT  @start AS datum
            UNION ALL

            SELECT
                DATEADD(MONTH, 1, datum)
            FROM q
            WHERE DATEADD(MONTH, 1, datum) < @enddate
        )

        Insert Into @T
            SELECT
                DATEADD(MONTH, 0, CONVERT(DATE, datum)) StartDate,
                EOMONTH(DATEADD(MONTH, 0, CONVERT(DATE, datum))) EndDate,
                CAST(YEAR(datum) as VARCHAR) + '-' + CAST(MONTH(datum) as VARCHAR) period
            FROM q
    END

ELSE
    BEGIN
        SET @start = DATEADD(WEEK, DATEDIFF(WEEK, 0, @startdate), 0);

        WITH q AS (
            SELECT  @start AS datum
            UNION ALL

            SELECT
                DATEADD(day, 7, datum)
            FROM q
            WHERE DATEADD(day, 7, datum) < @enddate
        )

        Insert Into @T
        SELECT
            datum StartDate,
            DATEADD(day, 6, datum) EndDate,
            CAST(YEAR(datum) as VARCHAR) + '-' + CAST(DATEPART(wk, datum) as VARCHAR)
        FROM q
    END

RETURN
END

GO
