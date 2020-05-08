SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
ALTER FUNCTION [dbo].[udfMAReport](
    @DateLower DATE,
    @DateUpper DATE,
    @Model VARCHAR(255),
    @MineSite VARCHAR(255),
    @ExcludeMA BIT = 0, -- exclude F300
    @AHSActive BIT = 0,
    @SplitAHS BIT = 1)

-- DECLARE @Model @Model VARCHAR(255) = '980%'
-- DECLARE @MineSite VARCHAR(255) = 'FortHills'
-- DECLARE @DateLower DATETIME2(0) = '2019-05-01';
-- DECLARE @DateUpper DATETIME2(0) = '2019-05-05';

RETURNS TABLE
AS
RETURN

SELECT
    d.Model,
    d.Unit,
    ISNULL(c.Total,0) Total,
    ISNULL(c.SMS,0) SMS,
    ISNULL(c.Suncor,0) Suncor,
    d.MA Target_MA,
    ROUND(IIF(c.SMS IS NULL, 1, (d.HrsPeriod_MA - c.SMS) / d.HrsPeriod_MA), 4) SMS_MA,
    d.HrsPeriod_MA,
    ROUND(IIF(c.Total IS NULL, 1, (d.HrsPeriod_PA - c.Total) / d.HrsPeriod_PA), 4) PA,
    d.HrsPeriod_PA

FROM (
    -- Join MA target table to get target MA for period based on unit age in months, and
    -- tblHrsInPeriod to get hours in period with out of system hrs excluded
    SELECT
        a.*,
        m.MA,
        h.HrsPeriod_MA,
        h.HrsPeriod_PA

    FROM UnitID a
        LEFT JOIN dbo.udfUnitMA(@DateUpper) m ON m.Unit=a.Unit
        LEFT JOIN dbo.tblHrsInPeriod(@DateLower, @DateUpper, @MineSite) h ON h.Unit=a.Unit

    WHERE
        a.DeliveryDate<@DateUpper AND
        (a.DateOffContract IS NULL OR a.DateOffContract>@DateUpper) AND
        m.MA IS NOT NULL AND
        ((@SplitAHS=1 AND a.AHSActive=@AHSActive) OR (@SplitAHS=0 AND (a.AHSActive=1 OR a.AHSActive=0))) AND
        ((@ExcludeMA=1 AND (a.ExcludeMA<>1 OR a.ExcludeMA IS NULL)) OR (@ExcludeMA=0))) d 

    LEFT JOIN (
        SELECT
            b.Unit,
            SUM(Duration) Total,
            SUM(SMS) SMS,
            SUM(Suncor) Suncor

        FROM UnitID b
            LEFT JOIN Downtime e ON e.Unit=b.Unit  

        WHERE
            ShiftDate >= @DateLower AND
            ShiftDate <= @DateUpper AND
            Duration > 0.01

        GROUP BY b.Unit) c ON d.Unit=c.Unit

WHERE
    d.MineSite = @MineSite AND
    d.Model Like @Model AND
    d.Active = 1;

GO
