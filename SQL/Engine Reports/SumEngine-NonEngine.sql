Select Year(StartDate) as [Year], Month(StartDate) as [Month], Sum(Duration) as Duration, 

Sum(case when CategoryAssigned<>'Engine' then SMS else 0 END) as SMS_NonEngine, 
Sum(case when CategoryAssigned<>'Engine' then Suncor else 0 END) as Suncor_NonEngine,
Sum(case when CategoryAssigned='Engine' then SMS else 0 END) as SMS_Engine, 
Sum(case when CategoryAssigned='Engine' then Suncor else 0 END) as Suncor_Engine

From Downtime a Inner Join UnitID b on a.Unit=b.Unit
Where b.MineSite='FortHills'
Group By Year(StartDate), Month(StartDate)
Order By Year(StartDate), Month(StartDate)