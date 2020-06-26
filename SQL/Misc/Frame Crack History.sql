select
    a.Unit,
    a.DateAdded,
    a.Title,
    a.SMR,
    a.TSIPartName,
    a.TSIDetails,
    a.WOComments,
    a.TSINumber,
    a.SuncorWO

FROM EventLog a INNER JOIN UnitID b on a.Unit=b.Unit

WHERE
    a.Title like '%crack%' and
    b.MineSite='FortHills'

