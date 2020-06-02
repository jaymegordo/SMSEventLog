SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
ALTER FUNCTION [dbo].[udfMASummary](
    @DateLower DATE,
    @DateUpper DATE,
    @Model VARCHAR(255),
    @MineSite VARCHAR(255),
    @ExcludeMA BIT = 0,
    @AHSActive BIT = 0,
    @SplitAHS BIT = 1
) 
-- DECLARE @DateLower DATE ='2019-04-01'
-- DECLARE @DateUpper DATE = '2019-05-01'
-- DECLARE @Model VARCHAR(255) = '980%'
-- DECLARE @MineSite VARCHAR(255) = 'FortHills'
-- DECLARE @ExcludeMA BIT = 1
RETURNS TABLE
AS
RETURN

SELECT 
    a.*,
    ROUND((a.SMS_MA - a.Target_MA) * HrsPeriod_MA, 0) Target_Hrs_Variance

FROM ( 
    SELECT
        Sum(SMS) SumSMS,
        (Sum(Target_MA * HrsPeriod_MA)) / NULLIF(Sum(HrsPeriod_MA), 0) Target_MA,
        (Sum(HrsPeriod_MA) - Sum(SMS)) / NULLIF(Sum(HrsPeriod_MA), 0) SMS_MA,
        Sum(HrsPeriod_MA) HrsPeriod_MA,
        (Sum(HrsPeriod_PA) - Sum(Total)) / NULLIF(Sum(HrsPeriod_PA), 0) PA,
        Sum(HrsPeriod_PA) HrsPeriod_PA

    FROM dbo.udfMAReport (@DateLower, @DateUpper, @Model, @MineSite, @ExcludeMA, @AHSActive, @SplitAHS)) as a

GO
