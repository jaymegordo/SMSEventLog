SELECT UID, MineSite, StatusEvent, Unit, Title, DateAdded, RemovalReason, Floc, ComponentCO, GroupCO, ComponentSMR, SNRemoved, SNInstalled, CapUSD FROM EventLog
Where ComponentCO=1 and MineSite='BaseMine'
order By RemovalReason