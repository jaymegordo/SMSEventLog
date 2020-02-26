Select Unit, Format(Cast(SMR As Int), '#,###') SMR, DateSMR
From
    (select Unit,
                DateSMR,
                SMR,
                row_number() over(partition by Unit order by SMR desc) as rn
        from UnitSMR) a
Where rn=1
Order By Unit Desc