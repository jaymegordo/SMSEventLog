Delete From b From (
Select a.*, ROW_NUMBER() Over (Partition By Unit, [Start Date] Order By Unit, [End Date]) as rn
From DowntimeExport a) b 
Where b.rn > 1