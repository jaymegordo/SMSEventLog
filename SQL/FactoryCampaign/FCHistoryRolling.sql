ALTER FUNCTION [dbo].[FCHistoryRolling] (
    @dateupper DATE,
    @minesite VARCHAR(255))

RETURNS TABLE
AS
RETURN

SELECT
    a.DateUpper as Date, b.* From udf12PeriodRolling (@dateupper, 'month', 12) a

CROSS APPLY FCStatusAtDate (DateUpper, 'FortHills') b