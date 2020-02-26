ALTER FUNCTION udfMASummaryTable (
    @Model VARCHAR(255),
    @MineSite VARCHAR(255),
    @DateUpper VARCHAR(255),
    @PeriodType VARCHAR(255)
)

RETURNS TABLE
AS
RETURN
-- DECLARE @Model VARCHAR(255) = '980%'
-- DECLARE @MineSite VARCHAR(255) = 'FortHills'
-- DECLARE @ExcludeMA BIT = 1

Select * From udf12PeriodRolling (@DateUpper, @PeriodType) a

CROSS APPLY udfMASummary (DateLower, DateUpper, @Model, @MineSite, 1)