-- update closest SMR reading less than date, up to max 7 days

CREATE PROCEDURE [dbo].[updateNullUnitSMR]
AS

UPDATE c
Set c.SMR=d.SMR

-- SELECT c.*, d.SMR
FROM (
    SELECT a.Unit, DateAdded, a.SMR, (
        SELECT TOP 1 b.DateSMR
        FROM UnitSMR b
        WHERE 
            b.DateSMR<=a.DateAdded and
            b.DateSMR>=DATEADD(d, -7, a.DateAdded) and
            b.Unit=a.Unit
        ORDER BY b.DateSMR DESC) as [MaxDate]
    FROM EventLog a
    WHERE a.MineSite in ('FortHills', 'BaseMine') and a.SMR is NULL) as c
LEFT JOIN UnitSMR d on c.Unit=d.Unit and c.MaxDate=d.DateSMR
WHERE d.SMR Is Not Null

