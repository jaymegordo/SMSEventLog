-- DECLARE @model VARCHAR = NULL;
-- DECLARE @minesite VARCHAR = NULL;
-- SET @minesite = 'FortHills';

SELECT
    MineSite,
    Customer,
    Model,
    Serial,
    EngineSerial,
    a.Unit, 
    SMR,
    DateSMR,
    DeliveryDate,
    CASE 
        WHEN DATEDIFF(d, DeliveryDate, CURRENT_TIMESTAMP) <= 365 
        THEN 365 - DATEDIFF(d, DeliveryDate, CURRENT_TIMESTAMP)
        ELSE 0
    END as Remaining,
    CASE
        WHEN ISNUMERIC(LEFT(Model, 1)) = 1
        THEN 
            CASE
                WHEN DATEDIFF(d, DeliveryDate, CURRENT_TIMESTAMP) <= 2*365
                THEN 2*365 - DATEDIFF(d, DeliveryDate, CURRENT_TIMESTAMP)
                ELSE 0
            END
        ELSE NULL
    END as GE_Remaining
FROM
    UnitID a Left Join (
        Select
            Unit,
            Max(SMR) as SMR,
            Max(DateSMR) As DateSMR
        From
            UnitSMR
        Group By Unit) b On a.Unit=b.Unit 

WHERE
    a.MineSite = 'FortHills' And
    Model Like '980%'

ORDER BY MineSite, Unit;
