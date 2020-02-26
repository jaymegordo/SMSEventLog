ALTER FUNCTION udfUnitMA (
    @DateMA DATE
)
RETURNS TABLE
AS
RETURN
-- Check date must be day before upper date passed --> DATEADD(Day, -1, @DateMA)

Select c.Unit, d.MA From (
        Select a.*, Min(MaxAge) as MaxAge From (
            Select Unit, DATEDIFF(MONTH, DeliveryDate, DATEADD(day, -1, @DateMA)) as AgeMonth From UnitID
            Where DeliveryDate Is Not Null) a 
        Left Join MAGuarantee b On a.AgeMonth < b.MaxAge
        Group By a.Unit, a.AgeMonth) c
Left Join MAGuarantee d on c.MaxAge=d.MaxAge
