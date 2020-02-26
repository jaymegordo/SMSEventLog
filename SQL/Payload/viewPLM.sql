SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO

ALTER VIEW [dbo].[viewPLM]
AS 

    SELECT
        a.Unit,
        a.DateTime,
        a.Payload,
        a.StatusFlag,
        a.L_HaulDistance,
        ROUND(a.Payload_Gross / c.TargetPayload, 3) AS GrossPayload_pct,
        ROUND((a.Payload_Quick + a.Carryback) / c.TargetPayload, 3) AS QuickPayload_pct,
        ROUND((a.Payload_Est + a.Carryback) / c.TargetPayload, 3) AS QuickShovelEst_pct,
        CASE WHEN
            a.StatusFlag LIKE '%B%' OR
            a.StatusFlag LIKE '%C%' OR
            a.StatusFlag LIKE '%D%' OR
            a.StatusFlag LIKE '%N%' OR
            a.StatusFlag LIKE '%L%'
        THEN 1 ELSE 0 END as ExcludeFlags

    FROM (PLM a
        INNER JOIN UnitID b ON a.Unit=b.Unit) 
            LEFT JOIN EquipType c ON b.Model=c.Model

GO
