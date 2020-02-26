Declare @Cols as varchar(max)

Select @Cols =
Coalesce(@Cols + ', ','') + QUOTENAME(Unit)

From 
(
Select Distinct Unit From UnitID Where MineSite='FortHills' And Model Like '980%'
) as B

PRINT @Cols