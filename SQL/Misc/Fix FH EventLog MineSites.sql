UPDATE a
SET
    a.MineSite=b.MineSite
FROM EventLog a LEFT JOIN UnitID b on a.Unit=b.Unit
WHERE
    a.MineSite='FortHills' and 
    a.MineSite<>b.MineSite