
ALTER FUNCTION [dbo].[FCStatusAtDate](
    @checkdate DATE,
    @minesite VARCHAR(255)
)

-- incomplete at time checkdate = startdate < checkdate (is released) AND DateCompleteSMS IS NULL (incomplete)
-- declare @checkdate DATE
-- set @checkdate = '2020-03-01'


RETURNS TABLE
AS
RETURN

SELECT
    COUNT(*) as Outstanding,
    SUM(t.Hours) as OutstandingHours

FROM (
    SELECT
        a.Hours
        -- COUNT(*) as TotalReleased,
        -- COUNT(CASE WHEN (a.DateCompleteSMS IS NULL OR a.DateCompleteSMS > @checkdate) THEN 1 ELSE NULL END) as Outstanding,
        -- SUM(Hours) as TotalReleasedHours,
        -- CONVERT(INT, SUM(CASE WHEN (a.DateCompleteSMS IS NULL OR a.DateCompleteSMS > @checkdate) THEN a.Hours ELSE NULL END)) as OutstandingHours

    FROM 
        viewFactoryCampaign a 
            INNER JOIN UnitID b on a.Unit=b.Unit
            INNER JOIN FCSummaryMineSite c on a.FCNumber=c.FCNumber
    WHERE
        c.ManualClosed=0 and
        b.MineSite=@minesite and
        a.Classification='M' and
        a.StartDate < @checkdate and
        ((a.DateCompleteSMS IS NULL and a.DateCompleteKA IS NULL) OR 
            IIF(a.DateCompleteSMS < a.DateCompleteKA, a.DateCompleteSMS, a.DateCompleteKA) > @checkdate)
) t