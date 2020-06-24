select
    b.MineSite,
    a.Unit,
    a.DateAdded,
    a.Title,
    a.SMR,
    a.TSIPartName,
    a.TSIDetails,
    a.WOComments,
    a.TSINumber

FROM EventLog a INNER JOIN UnitID b on a.Unit=b.Unit

WHERE
    a.Title like '%crack%' and
    b.MineSite='FortHills'

