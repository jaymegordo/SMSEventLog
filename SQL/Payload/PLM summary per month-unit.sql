select Unit, MONTH(DateTime) as Month, CAST(Max(DateTime) as DATE) as MaxDate, COUNT(*) as Count
From PLM
WHERE DateTime>='2020-01-01'
Group By Unit, Month([DateTime])
Order By Unit