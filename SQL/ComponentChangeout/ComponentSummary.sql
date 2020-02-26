select Component, Count(Component) as 'Count Changeouts'
From UnitID Inner Join (EventLog Inner Join ComponentType On EventLog.Floc=ComponentType.Floc) On UnitID.Unit=EventLog.Unit
Where DateAdded Between '2019-01-01' And '2019-04-01' And UnitID.MineSite='FortHills'
Group By Component