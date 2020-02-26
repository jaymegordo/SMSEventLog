-- Update event's ComponentSMR using Unit SMR from prev CO for same unit + Floc
-- Exclude records where SMR is the same, could be a bit sketch if multiple back to back COs with same Unit SMR which came from
-- UpdateUnitSMR function, when dates are within 7 days. 

ALTER PROCEDURE [dbo].[updateNullComponentSMR] AS

UPDATE c
SET
    c.ComponentSMR = CASE WHEN c.PrevCOSMR Is NULL THEN c.SMR ELSE c.SMR - c.PrevCOSMR END

-- SELECT * 
FROM (
    SELECT a.Unit, a.DateAdded, a.Floc, a.SMR, a.ComponentSMR, (
        SELECT TOP 1 b.SMR
        FROM EventLog b
        WHERE 
            b.Floc=a.Floc and 
            b.Unit=a.Unit and
            b.DateAdded<a.DateAdded and
            b.SMR<a.SMR
        ORDER BY b.DateAdded DESC) as PrevCOSMR
    FROM EventLog a
    WHERE 
        a.MineSite='FortHills' and 
        a.ComponentCO=1 and 
        a.ComponentSMR Is NULL and
        a.SMR Is Not NULL) as c
-- ORDER BY c.Unit, c.DateAdded