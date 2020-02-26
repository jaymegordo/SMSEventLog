ALTER FUNCTION udfMAReport(
    @DateLower DATE,
    @DateUpper DATE,
    @Model VARCHAR(255),
    @MineSite VARCHAR(255),
    @ExcludeMA BIT = 0
)
-- DECLARE @Model @Model VARCHAR(255) = '980%'
-- DECLARE @MineSite VARCHAR(255) = 'FortHills'
-- DECLARE @DateLower DATETIME2(0) = '2019-05-01';
-- DECLARE @DateUpper DATETIME2(0) = '2019-05-05';

RETURNS TABLE
AS
RETURN

Select d.Model, d.Unit, IsNull(c.Total,0) Total, IsNull(c.SMS,0) SMS, IsNull(c.Suncor,0) Suncor, d.MA Target_MA, 
    IIF(c.SMS Is Null, 1, (d.HrsPeriod-c.SMS)/d.HrsPeriod) SMS_MA,
    IIF(c.Total Is Null, 1, (d.HrsPeriod-c.Total)/d.HrsPeriod) PA, d.HrsPeriod
From (Select UnitID.*, m.MA, dbo.udfHoursInPeriod(UnitID.Unit, @DateLower, @DateUpper) as HrsPeriod
    From UnitID Left Join udfUnitMA(@DateUpper) m On UnitID.Unit=m.Unit
    WHere UnitID.DeliveryDate<@DateUpper 
        And (UnitID.DateOffContract Is Null Or UnitID.DateOffContract>@DateUpper) 
        And M.MA Is Not Null 
        And ((@ExcludeMA=1 And (ExcludeMA<>1 Or ExcludeMA Is Null)) Or (@ExcludeMA=0))) d 

    Left Join (Select b.Unit, Sum(Duration) Total, Sum(SMS) SMS, Sum(Suncor) Suncor 
        From UnitID b Left Join Downtime a on a.Unit=b.Unit  
        Where ShiftDate>=@DateLower And ShiftDate<=@DateUpper And Duration>0.01 
        Group By b.Unit) c On d.Unit=c.Unit 
Where d.MineSite=@MineSite And d.Model Like @Model and d.Active=1
;

