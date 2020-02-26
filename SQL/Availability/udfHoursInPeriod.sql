ALTER FUNCTION udfHoursInPeriod(
    @Unit VARCHAR(255),
    @DateLower DATETIME2(0),
    @DateUpper DATETIME2(0)
)
RETURNS INT

AS

BEGIN
    DECLARE @DeliveryDate DATETIME2(0);
    DECLARE @Hours Int
    SELECT @DeliveryDate=DeliveryDate FROM UnitID WHERE Unit=@Unit;
    
    IF @DeliveryDate<@DateLower
    BEGIN
        SET @Hours = DATEDIFF(hour, @DateLower, @DateUpper);
    END
    ELSE
    BEGIN
        SET @Hours = DATEDIFF(hour, @DeliveryDate, @DateUpper);
        IF @Hours<0
        BEGIN
            SET @Hours = 0;
        END
    END
    RETURN @Hours + 24
END