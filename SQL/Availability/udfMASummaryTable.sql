SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
ALTER FUNCTION [dbo].[udfMASummaryTable] (
    @Model VARCHAR(255),
    @MineSite VARCHAR(255),
    @DateUpper VARCHAR(255),
    @PeriodType VARCHAR(255), 
    @AHSActive BIT = 0,
    @SplitAHS BIT = 1)

RETURNS TABLE
AS
RETURN
-- DECLARE @Model VARCHAR(255) = '980%'
-- DECLARE @MineSite VARCHAR(255) = 'FortHills'
-- DECLARE @ExcludeMA BIT = 1
-- this function DOES split the AHS out now

Select * From udf12PeriodRolling (@DateUpper, @PeriodType, 12) a

CROSS APPLY udfMASummary (DateLower, DateUpper, @Model, @MineSite, 1, @AHSActive, @SplitAHS)

GO
