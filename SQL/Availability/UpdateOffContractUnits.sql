Update b
Set OffContract=1

From udfMaxUnitSMR() a Inner Join UnitID b On a.Unit=b.Unit
Where a.MaxSMR > 70000
