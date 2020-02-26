CREATE FUNCTION udfMonthsRolling (
    @Month DATE
)
RETURNS TABLE
AS
RETURN

-- DECLARE @Month DATE
-- Set @Month = '2019-04-01'

select
    BeginDate = dateadd(month, -1, dateadd(day, 1, eomonth(@Month, -Offset.X))),
    EndDate = dateadd(day, 1, eomonth(@Month, -Offset.X))
from
    (values (0),(1),(2),(3),(4),(5),(6),(7),(8),(9),(10),(11)) Offset(X)