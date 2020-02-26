CREATE FUNCTION udfMaxUnitSMR ()

RETURNS TABLE
AS
RETURN

Select Unit, Max(SMR) as MaxSMR From UnitSMR
Group By Unit