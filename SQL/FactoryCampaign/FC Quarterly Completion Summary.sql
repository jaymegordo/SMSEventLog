Select FactoryCampaign.FCNumber, IIF(FCSummary.SubjectShort Is Null, FCSummary.Subject, FCSummary.SubjectShort) as 'Subject', Count(FactoryCampaign.FCNumber) as 'FCs Completed'
From UnitID Inner Join (EventLog Right Join (FactoryCampaign Left Join FCSummary on FCSummary.FCNumber=FactoryCampaign.FCNumber) On EventLog.UID=FactoryCampaign.UID) On UnitID.Unit=FactoryCampaign.Unit
Where UnitID.MineSite='FortHills' and (FactoryCampaign.DateCompleteSMS Between '2019-01-01' and '2019-04-01' or EventLog.DateCompleted Between '2019-01-01' and '2019-04-01')
Group By FactoryCampaign.FCNumber, IIF(FCSummary.SubjectShort Is Null, FCSummary.Subject, FCSummary.SubjectShort)
