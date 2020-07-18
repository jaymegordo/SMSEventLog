
CREATE VIEW [dbo].[viewOilSamples]
AS

SELECT
    t4.labTrackingNo,
    t4.unitId as Unit,
    t4.Component,
    t4.Modifier,
    t4.sampleDate,
    t4.meterReading as unitSMR,
    t4.componentSMR,
    a2.oilChanged,
    a2.sampleRank,
    a2.testResults,
    a2.results,
    a2.recommendations,
    a2.comments

FROM (
    SELECT -- t4
        t2.*,
        -- t3.DateAdded,
        -- t3.SMR,
        t2.meterReading - ISNULL(t3.SMR, 0) as componentSMR,
        ROW_NUMBER() OVER(PARTITION BY t2.labTrackingNo ORDER BY t3.DateAdded DESC) as rn -- join on date < date creates multiple records, need to select only most recent

    FROM (
        SELECT -- t2
            a.labTrackingNo,
            a.unitId,
            a.sampleDate,
            a.meterReading,
            b.Floc,
            CASE WHEN b.Component IS NULL THEN a.componentId ELSE b.Component END as Component, -- need to make sure fluidlife components added to ComponentType first
            CASE WHEN b.Modifier IS NULL THEN a.componentLocation ELSE b.Modifier END as Modifier

        FROM
            OilSamples a
            LEFT JOIN ComponentType b ON
                a.componentId=b.componentId AND
                a.componentLocation=b.ComponentLocation

        --     LEFT JOIN UnitID c ON a.unitId=c.Unit
        
        -- WHERE
        --     c.MineSite='FortHills' and
        --     c.Model like '980%' and
        --     a.componentId='wheel hub, spindle'
            
        ) as t2

        -- t3
        LEFT JOIN (
            SELECT d.Unit, d.Floc, d.DateAdded, d.SMR
            FROM EventLog d
            WHERE
                d.ComponentCO=1
            ) AS t3 ON
        t2.Floc=t3.Floc AND
        t2.unitId=t3.Unit AND
        t2.sampleDate>t3.DateAdded) as t4

-- re-join extra columns after unit hrs figured out to avoid reselecting multiple times
LEFT JOIN
    OilSamples a2 ON t4.labTrackingNo=a2.labTrackingNo

WHERE t4.rn=1

-- ORDER BY
--     t4.unitId, t4.Component, t4.Modifier, t4.sampleDate