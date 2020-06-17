-- MineSite, Model, Unit, Component, Side, BenchSMR, Current Unit SMR, SMR at last CO, Current Component SMR, Predicted CO date, Life Remaining (days)
-- Only components where Unit's model's EquipClass = ComponentType.EquipClass

-- @Model
-- @Unit
-- @MineSite
-- @Floc
-- @Date

SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO

ALTER VIEW [dbo].[viewPredictedCO]
AS 

SELECT 
    t4.*,
    DATEDIFF(day, CURRENT_TIMESTAMP, t4.PredictedCODate) as LifeRemaining
FROM 
    (SELECT
        t3.MineSite,
        t3.Model,
        t3.Unit,
        t3.Component,
        t3.Modifier,
        t3.BenchSMR,
        t3.CurrentUnitSMR,
        t2.LastCO as SMRLastCO, 
        t3.CurrentUnitSMR - ISNULL(t2.LastCO, 0) as CurrentComponentSMR,
        CAST(DATEADD(day, (t3.BenchSMR - (t3.CurrentUnitSMR - ISNULL(t2.LastCO, 0))) / 20, CURRENT_TIMESTAMP) as DATE) as PredictedCODate
    
    FROM 
        (SELECT 
            u.MineSite,
            u.Model,
            u.Unit,
            c.Component,
            c.Modifier,
            c.Floc,
            c.BenchSMR,
            t1.CurrentUnitSMR

        FROM ComponentType c, 
            (SELECT
                u2.Unit,
                -1 * (DATEDIFF(day, CURRENT_TIMESTAMP, MAX(s.DateSMR)) * 20) + Max(s.SMR) AS CurrentUnitSMR

            FROM UnitID u2
                INNER JOIN UnitSMR s ON u2.Unit=s.Unit
            GROUP BY u2.Unit) t1
            
            INNER JOIN (UnitID u 
                INNER JOIN EquipType e on u.Model=e.Model) ON t1.Unit=u.Unit
        
        WHERE 
            u.Active=1 and
            c.BenchSMR IS NOT NULL and
            c.Major=1 and
            c.EquipClass=e.EquipClass) as t3 

        LEFT JOIN (
            SELECT EventLog.Unit, EventLog.Floc, Max(EventLog.SMR) AS LastCO 
            FROM EventLog
            WHERE ComponentCO='True'
            GROUP BY EventLog.Unit, EventLog.Floc) AS t2 ON t2.Floc=t3.Floc AND t2.Unit=t3.Unit
    ) as t4
    -- ORDER BY t3.Unit, t3.Floc
GO