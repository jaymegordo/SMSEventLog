-- PARAMETERS aUnit Text ( 255 ), StartDate DateTime, EndDate DateTime;
DECLARE @unit varchar(50) = 'F301'
DECLARE @StartDate Datetime2 = '2019-01-01'
DECLARE @EndDate Datetime2 = '2019-10-01'

SELECT
    a.Unit,
    a.DateTime,
    Payload,
    StatusFlag,
    L_HaulDistance,
    ROUND(Payload_Gross/TargetPayload,3) AS GrossPayload_pct,
    ROUND((Payload_Quick + Carryback)/c.TargetPayload,3) AS QuickPayload_pct,
    ROUND((Payload_Est + Carryback)/c.TargetPayload,3) AS QuickShovelEst_pct,
    CASE WHEN
        StatusFlag LIKE '%B%' OR
        StatusFlag LIKE '%C%' OR
        StatusFlag LIKE '%D%' OR
        StatusFlag LIKE '%N%' OR
        StatusFlag LIKE '%L%'
    THEN 1 ELSE 0 END as Exclude

FROM (PLM a
    INNER JOIN UnitID b ON a.Unit=b.Unit) 
        LEFT JOIN EquipType c ON b.Model=c.Model

WHERE 
    a.Unit=@unit AND
    a.DateTime Between @StartDate And @EndDate
