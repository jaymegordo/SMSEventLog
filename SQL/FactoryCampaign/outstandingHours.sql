Select
    a.Unit,
    COUNT(c.Hours) as NumOutstanding,
    SUM(c.Hours) as SumHours,
    MAX(c.Hours) as MaxHours,
    MAX(c.Hours) * 1.5 as MaxHours_x_1pt5

FROM
    viewFactoryCampaign a
    LEFT JOIN FCSummaryMineSite b on a.FCNumber=b.FCNumber
        LEFT JOIN FCSummary c on b.FCNumber=c.FCNumber
            LEFT JOIN UnitID d on a.Unit=d.Unit

WHERE
    a.Complete=0 and
    d.MineSite='FortHills' and
    b.ManualClosed=0 and
    a.Classification='M'

GROUP BY a.Unit
ORDER BY a.Unit