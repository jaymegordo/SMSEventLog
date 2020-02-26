ALTER FUNCTION udf12PeriodRolling (
    @DateUpper DATE,
    @PeriodType VARCHAR(255),
    @nPeriods TINYINT = 12
)

RETURNS @T TABLE (DateLower DATE, DateUpper DATE)
AS

BEGIN

DECLARE @Today DATETIME
-- DECLARE @nPeriods TINYINT
-- DECLARE @StartDate DATE
-- DECLARE @PeriodType VARCHAR(255)

-- SET @nPeriods = 12;
-- SET @PeriodType = 'Week'
-- SET @PeriodType = 'Month'
-- Set @DateUpper = '2019-05-01'

    IF @PeriodType = 'Month'
    BEGIN
        SET @Today = DATEADD(month, (-1) * (@nPeriods - 1), DATEADD(day, 1, @DateUpper));
        
        WITH q AS (
            SELECT  @Today AS datum
            UNION ALL
            SELECT DATEADD(month, 1, datum)
            FROM q WHERE datum + 1 < @DateUpper
        )
        Insert Into @T
        SELECT DATEADD(month, -1, Convert(Date, datum)) StartDate, EOMONTH(DATEADD(month, -1, Convert(Date, datum))) EndDate
        FROM q
    END
    
    ELSE
    BEGIN
        SET @Today = DATEADD(day, (-7) * (@nPeriods - 1), @DateUpper);
        WITH q AS (
            SELECT  @Today AS datum
            UNION ALL
            SELECT DATEADD(day, 7, datum)
            FROM q WHERE datum + 1 < @DateUpper
        )
        Insert Into @T
        SELECT DATEADD(day, -6, Convert(Date, datum)) StartDate, Convert(Date, datum) EndDate
        FROM q
    END
RETURN
END
