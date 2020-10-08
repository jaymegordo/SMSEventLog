SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
ALTER PROCEDURE [dbo].[ImportPLM]

AS

-- Drop duplicates before final import in case anything failed or got imported at the same time
WITH t as (
    SELECT
        *,
        ROW_NUMBER() OVER (PARTITION BY b.unit, b.datetime ORDER BY b.unit, b.datetime) as RN

    FROM PLMImport b)

Insert Into PLM
SELECT
    t.Unit,
    t.DateTime,
    t.Payload,
    t.Swingloads,
    t.StatusFlag,
    t.Carryback,
    t.CycleTime,
    t.L_HaulDistance,
    t.L_MaxSpeed,
    t.E_MaxSpeed,
    t.MaxSprung,
    t.TruckType,
    t.SprungWeight,
    t.Payload_Est,
    t.Payload_Quick,
    t.Payload_Gross

FROM t
    LEFT JOIN PLM a
    ON a.Unit=t.Unit and a.datetime=t.datetime

WHERE
    a.Unit IS NULL and
    RN = 1;

TRUNCATE TABLE PLMImport;

GO
