-- Update missing UIDs for improperly linked FC Events

select a.UID, a.Unit, a.Title, a.CreatedBy, a.DateAdded, a.DateCompleted, SUBSTRING(a.Title, 4, 8) as FCNumber, c.FCNumber, c.UID

From EventLog a
    left join UnitID b on a.unit=b.unit
    left join viewFactoryCampaign c on SUBSTRING(a.Title, 4, 8)=c.FCNumber and a.Unit=c.Unit

where
    b.Minesite='FortHills' and
    a.DateAdded >='2020-08-01' and
    a.Title like '%FC %'

order by a.Unit, a.Title