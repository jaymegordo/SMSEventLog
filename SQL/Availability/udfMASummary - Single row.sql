ALTER FUNCTION udfMASummary(
    @DateLower DATE,
    @DateUpper DATE,
    @Model VARCHAR(255),
    @MineSite VARCHAR(255),
    @ExcludeMA BIT
) 
-- DECLARE @DateLower DATE ='2019-04-01'
-- DECLARE @DateUpper DATE = '2019-05-01'
-- DECLARE @Model VARCHAR(255) = '980%'
-- DECLARE @MineSite VARCHAR(255) = 'FortHills'
-- DECLARE @ExcludeMA BIT = 1
RETURNS TABLE
AS
RETURN

Select 
Sum(SMS) SumSMS, 
(Sum(Target_MA * HrsPeriod)) / NULLIF(Sum(HrsPeriod), 0) Target_MA,
(Sum(HrsPeriod) - Sum(SMS)) / NULLIF(Sum(HrsPeriod), 0) SMS_MA

From dbo.udfMAReport (@DateLower, @DateUpper, @Model, @MineSite, @ExcludeMA)

