Select a.Unit, FCNumber, StartDate, Month(StartDate) as MonthRelease, YEAR(StartDate) as YearRelease, EndDate, Subject, 

IIF(c.DateCompleted Is Null, IIF(DateCompleteKA Is Null, DateCompleteSMS, DateCompleteKA), c.DateCompleted) as DateComplete, 

YEAR(CompletionDate) as YearComplete, MONTH(CompletionDate) as MonthComplete, [Hours], Classification, Notes
From (FactoryCampaign a Inner Join UnitID b on a.Unit=b.Unit) Left Join EventLog c on a.UID=c.UID
Where b.MineSite='FortHills' And Classification='M' And StartDate>='2017-01-01'