ALTER PROCEDURE [dbo].[updateUnitComponentSMR]

AS

    DECLARE @rowsUpdatedUnit int
    DECLARE @rowsUpdatedComponent int

    EXEC @rowsUpdatedUnit = updateNullUnitSMR;
    EXEC @rowsUpdatedComponent = updateNullComponentSMR;

    SELECT @rowsUpdatedUnit as Unit, @rowsUpdatedComponent as Component;

GO