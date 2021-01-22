
with t as (
    SELECT
        a.Unit,
        a.FCNumber,
        a.DateCompleteSMS as date_insp,
        a.SMR as unit_smr_at_insp

    FROM viewFactoryCampaign a
        LEFT JOIN UnitID b on a.Unit=b.Unit

    WHERE
        a.FCNumber in ('17H019-1', '17H019-2') and
        b.MineSite = 'FortHills'
),

t2 as (
    SELECT
        t.*,
        CASE WHEN
            t.FCNumber like '%-1' 
            THEN 'POWRTRN-WHMTLH-ACMOTOR_RH'
            ELSE 'POWRTRN-WHMTLH-ACMOTOR_LH'
        END as Floc

    FROM t),

t_unit_smr as (
    SELECT
        a.Unit,
        MAX(a.SMR) as unit_smr_cur

    FROM UnitSMR a
        LEFT JOIN UnitID b on a.Unit=b.Unit
    
    WHERE
        b.MineSite='FortHIlls'
    
    GROUP BY a.Unit
),

t5 as (
SELECT
    t2.*,
    t3.smr_co_pre_insp,
    t2.unit_smr_at_insp - ISNULL(t3.smr_co_pre_insp, 0) as comp_smr_at_insp,
    t4.unit_smr_last_co,
    t_unit_smr.unit_smr_cur,
    t_unit_smr.unit_smr_cur - ISNULL(t4.unit_smr_last_co, 0) as comp_smr_cur,
    t4.cur_SN

FROM t2

    LEFT JOIN t_unit_smr on t_unit_smr.Unit = t2.Unit

    LEFT JOIN (
        SELECT
            e.Unit,
            e.Floc,
            MAX(e.SMR) AS smr_co_pre_insp,
            MAX(e.DateAdded) as date_added

        FROM EventLog e
        WHERE
            e.ComponentCO='True'
        GROUP BY
            e.Unit,
            e.Floc
            ) AS t3
        
        ON t2.Floc=t3.Floc AND t2.Unit=t3.Unit and t3.date_added < t2.date_insp

    LEFT JOIN (
        SELECT
            e.Unit,
            e.Floc,
            Max(e.SMR) AS unit_smr_last_co,
            e.SNInstalled as cur_sn,
            ROW_NUMBER() OVER (PARTITION BY e.Unit, e.Floc ORDER BY MAX(e.SMR) DESC) as rn

        FROM EventLog e
        WHERE
            e.ComponentCO='True'
            
        GROUP BY
            e.Unit,
            e.Floc,
            e.SNInstalled
            ) AS t4
        
        ON t2.Floc=t4.Floc AND t2.Unit=t4.Unit and t4.rn=1

    ),

t6 as(
    SELECT
        t5.*,
        CASE WHEN t5.comp_smr_cur >= 12000
            THEN t5.comp_smr_cur - t5.comp_smr_at_insp
            ELSE NULL
        END as hrs_since_last_insp

    FROM t5)

SELECT
    t6.Unit,
    t6.FCNumber,
    t6.Floc,
    t6.cur_SN,
    t6.date_insp,
    t6.unit_smr_at_insp,
    t6.smr_co_pre_insp,
    t6.comp_smr_at_insp,
    t6.unit_smr_last_co,
    t6.unit_smr_cur,
    t6.comp_smr_cur,
    t6.hrs_since_last_insp,
    3000 - t6.hrs_since_last_insp as hrs_till_next_insp,
    CAST(DATEADD(day, (3000 - t6.hrs_since_last_insp) / 20, CURRENT_TIMESTAMP) as DATE) as date_next_insp,
    CASE WHEN t6.hrs_since_last_insp > 3000 THEN 'TRUE' ELSE 'FALSE' END as overdue

FROM t6

ORDER BY
    t6.Unit,
    t6.FCNumber