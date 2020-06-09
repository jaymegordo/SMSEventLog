DECLARE @DateLower DATE = '2016-01-01'
DECLARE @DateUpper DATE = '2020-06-01'

SELECT
    b.MineSite, 
    a.Unit,
    '980' as Model, 
    c.Component, 
    c.Modifier, 
    a.SuncorWO, 
    a.DateAdded, 
    YEAR(a.DateAdded) as [Year], 
    FORMAT(a.DateAdded, 'yyyy-MM') as [Year-Month],
    CASE WHEN a.Reman Is NULL THEN NULL ELSE
        CASE WHEN a.Reman=1 THEN 'Reman' ELSE 'New' END
    END as Reman,
    a.SMR as [Unit SMR],
    a.ComponentSMR as [Component SMR],
    c.BenchSMR, 
    a.SunCOReason as [Reason for CO],
    ROUND(CAST(a.ComponentSMR as FLOAT) / BenchSMR, 4) as [%BM],
    '' as [Range of BM],
    a.SNRemoved as ComponentSerial
FROM (
    EventLog a INNER JOIN UnitID b on a.Unit=b.Unit) 
        LEFT JOIN ComponentType c on a.Floc=c.Floc
WHERE
    b.MineSite='FortHills' and 
    c.Component <> 'Engine' and 
    c.Major=1 and 
    a.ComponentCO=1 and 
    b.Model like '980%' and 
    a.DateAdded>=@DateLower and
    a.DateAdded<=@DateUpper