Select a.* From dbo.udfUnitMA ('2018-11-01') a Inner Join UnitID b On a.Unit=b.Unit
Where b.MineSite='FortHills'
Order By a.Unit