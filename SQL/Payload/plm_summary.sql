-- Select full summary of all plm records in db
-- query can take ~1min for single unit, or ~3-5 for all units

DECLARE
@minesite VARCHAR(50) = 'BaseMine';

WITH t as (
    SELECT
        a.Unit,
        CAST(MIN(a.DateTime) as DATE) as MinDate,
        CAST(MAX(a.DateTime) as DATE) as MaxDate,
        COUNT(*) as TotalLoads,
        COUNT(*) - SUM(a.ExcludeFlags) as Total_ExcludeFlags,
        SUM(CASE WHEN
                a.GrossPayload_pct>1.1 AND
                a.GrossPayload_pct<=1.2 AND
                a.ExcludeFlags=0
            THEN 1 ELSE 0 END) as Total_110,
        SUM(CASE WHEN
                a.GrossPayload_pct>1.1 AND
                a.GrossPayload_pct<=1.2 AND
                a.ExcludeFlags=0 AND
                a.L_HaulDistance<=1
            THEN 1 ELSE 0 END) as Dumped_1KM_110,
        SUM(CASE WHEN
                a.GrossPayload_pct>1.1 AND
                a.GrossPayload_pct<=1.2 AND
                a.ExcludeFlags=0 AND
                a.L_HaulDistance>1 AND
                a.QuickShovelEst_pct<=1.1
            THEN 1 ELSE 0 END) as Lower_110_Shovel,
        
        SUM(CASE WHEN
                a.GrossPayload_pct>1.2 AND
                a.ExcludeFlags=0
            THEN 1 ELSE 0 END) as Total_120,
        SUM(CASE WHEN
                a.GrossPayload_pct>1.2 AND
                a.ExcludeFlags=0 AND
                a.L_HaulDistance<1
            THEN 1 ELSE 0 END) as Dumped_1KM_120,
        SUM(CASE WHEN
                a.GrossPayload_pct>1.2 AND
                a.ExcludeFlags=0 AND
                a.L_HaulDistance>1 AND
                a.QuickShovelEst_pct<=1.1 AND
                a.QuickPayload_pct<=1.2
            THEN 1 ELSE 0 END) as No_GE_Code

    FROM
        viewPLM a
            LEFT JOIN UnitID b on a.Unit=b.Unit
    WHERE
        -- a.DateTime>='2016-11-01' and
        -- a.DateTime BETWEEN '2018-10-22' and '2019-10-22' and -- comment out for full date range
        -- a.Unit = 'F301' and -- comment out for ALL units
        b.MineSite = @minesite and
        b.Model like '980%'

    GROUP BY a.Unit
)

SELECT
    t.*,
    t.Total_110 - t.Dumped_1KM_110 - t.Lower_110_Shovel as Acepted_110,
    t.Total_120 - t.Dumped_1KM_120 - t.No_GE_Code as Accepted_120,
    ROUND(CAST((t.Total_110 - t.Dumped_1KM_110 - t.Lower_110_Shovel) as FLOAT) / t.Total_ExcludeFlags, 3) as Overload_pct_110,
    ROUND(CAST((t.Total_120 - t.Dumped_1KM_120 - t.No_GE_Code) as FLOAT) / t.Total_ExcludeFlags, 3) as Overload_pct_120

FROM t
ORDER BY t.Unit