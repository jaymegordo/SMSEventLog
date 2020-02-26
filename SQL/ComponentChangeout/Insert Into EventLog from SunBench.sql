Insert Into EventLog(UID, MineSite, StatusEvent, StatusWO, Unit, Title, SMR, DateAdded, WarrantyYN, WorkOrder, Seg, PartNumber, SuncorWO, SuncorPO, ComponentCO, Floc, GroupCO, ComponentSMR, SNRemoved, CapUSD, RemovalReason, SunCOReason)

Select a.UID, a.MineSite, 'Complete' StatusEvent, 'Closed' StatusWO, a.Unit, IIF(a.Modifier Is Null, a.Component + ' - CO', a.Component + ', ' + a.Modifier + ' - CO') Title, a.SMR, a.DateAdded, a.Warranty, a.WorkOrder, '1' Seg, a.Part_Num, a.SuncorWO, a.PO, 1 ComponentCO, a.Floc, a.Group_CO, a.ComponentSMR, a.SNRemoved, a.CapUSD, a.Notes, a.Sun_CO_Reason
From SunBench a Left Join EventLog b on a.UID=b.UID
Where b.UID Is Null