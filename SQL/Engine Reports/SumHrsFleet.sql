
SELECT
    '980E' as Model, 
    MONTH(a.DateLower) as [Month], 
    YEAR(a.DateLower) as [Year], 
    a.DateLower as [Date], 
    dbo.udfHoursInPeriodFleet('FortHills', a.DateLower, a.DateUpper) as SumHrs 
FROM (
    SELECT * 
    FROM udf12PeriodRolling('2019-08-31', 'month', 15)) a


