declare @checkdate DATE
set @checkdate = '2020-05-31'

select FCNumber, Subject, COUNT(*) as Outstanding, SUM(Hours) as OutstandingHours

FROM (
SELECT
    -- COUNT(*) as TotalReleased,
    a.*
    -- COUNT(CASE WHEN (a.DateCompleteSMS IS NULL OR a.DateCompleteSMS > @checkdate) THEN 1 ELSE NULL END) as Outstanding,
    -- SUM(Hours) as TotalReleasedHours,
    -- CONVERT(INT, SUM(CASE WHEN (a.DateCompleteSMS IS NULL OR a.DateCompleteSMS > @checkdate) THEN a.Hours ELSE NULL END)) as OutstandingHours

FROM 
    viewFactoryCampaign a 
        INNER JOIN UnitID b on a.Unit=b.Unit
        INNER JOIN FCSummaryMineSite c on a.FCNumber=c.FCNumber
WHERE
    c.ManualClosed=0 and
    b.MineSite='FortHills' and
    a.Classification='M' and
    a.StartDate < @checkdate and
    ((a.DateCompleteSMS IS NULL and a.DateCompleteKA IS NULL) OR 
        IIF(a.DateCompleteSMS < a.DateCompleteKA, a.DateCompleteSMS, a.DateCompleteKA) > @checkdate)) as t

GROUP BY FCNumber, Subject
ORDER BY FCNumber