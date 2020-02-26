ALTER FUNCTION udfHoursInPeriodFleet(
    @MineSite VARCHAR(255),
    @DateLower DATETIME2(0),
    @DateUpper DATETIME2(0)
)
RETURNS INT
-- RETURNS TABLE
AS
-- RETURN

BEGIN
    Select Unit, dbo.udfHoursInPeriod(UnitID.Unit, @DateLower, @DateUpper) as HrsPeriod From UnitID
    Where MineSite=@MineSite and Model Like '980%'

    RETURN SUM(HrsPeriod)
END