CREATE PROCEDURE ImportDowntimeTable
AS
Insert Into Downtime
Select b.* 
From DowntimeImport b Left Join Downtime a
    On a.Unit=b.Unit and a.StartDate=b.StartDate
Where a.Unit Is Null;

Delete From DowntimeImport;

GO