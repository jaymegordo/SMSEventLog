-- Select Unit, Year-Month, Max date in database, Num PLM records

-- Init variables
DECLARE
@minesite VARCHAR(50) = 'BaseMine',
@startdate DATE = '2019-01-01',
@enddate DATE = '2021-01-01',
@maxrecords INT = 0; -- change this to define rows with max records shown per month (set to high number eg 10_000 to show all)

-- Generate range of months/unit to join on and ensure no missing days
WITH t1 AS (
    SELECT CONVERT(DATE, @startdate) AS Dates

    UNION ALL

    SELECT DATEADD(MONTH, 1, Dates)

    FROM t1
    WHERE
        CONVERT(DATE, Dates) < CONVERT(DATE, @enddate)),

t2 as (
    SELECT
        CAST(YEAR(Dates) as VARCHAR(4)) + '-' + CAST(MONTH(Dates) as VARCHAR(2)) as Period
    FROM t1),

-- merge units with year-month range
t3 as (
    SELECT
        a.Unit,
        t2.Period
    FROM UnitID a
    CROSS JOIN t2
    
    WHERE
        -- a.Unit='301' and
        a.MineSite = @minesite and
        a.Model like '980%'),

-- this is the count data from PLM table
t4 as (
    SELECT
        a.Unit,
        CAST(YEAR(a.DateTime) as VARCHAR(4)) + '-' + CAST(MONTH(a.DateTime) as VARCHAR(2)) as Period,
        COUNT(*) as NumRecords

    FROM
        PLM a
            LEFT JOIN UnitID b on a.Unit=b.Unit

    WHERE
        a.DateTime >= @startdate and
        b.MineSite = @minesite

    GROUP BY
        a.Unit,
        YEAR(a.DateTime),
        Month(a.DateTime))

SELECT
    t3.Unit,
    t3.Period,
    ISNULL(t4.NumRecords, 0) as NumRecords

FROM t3
    LEFT JOIN t4 on t3.Unit=t4.Unit and t3.Period=t4.Period

WHERE
    ISNULL(t4.NumRecords, 0) <= @maxrecords

ORDER BY
    t3.Unit