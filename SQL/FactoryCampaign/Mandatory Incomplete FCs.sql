Select *
From viewFactoryCampaign a
    LEFT JOIN FCSummaryMinesite c on a.FCNumber=c.FCNumber
        LEFT JOIN UnitID b on a.Unit=b.Unit
Where 
-- Unit in ('F317', 'F318', 'F320', 'F303', 'F326', 'F319', 'F324', 'F327', 'F321', 'F323', 'F325', 'F328', 'F329', 'F330', 'F322')and
    b.MineSite='FortHills' and
    Complete=0 and
    Classification='M' and UID Is NULL and
    c.ManualClosed=0
ORDER BY a.FCNumber, a.Unit