SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
ALTER FUNCTION [dbo].[udfHoursInPeriod](
    @Unit VARCHAR(255),
    @DateLower DATETIME2(0),
    @DateUpper DATETIME2(0)
)
RETURNS INT

AS

-- * NOT USED ANYMORE

BEGIN
    DECLARE @DeliveryDate DATETIME2(0)
    DECLARE @MinDate DATETIME2(0)
    DECLARE @Hours Int
    DECLARE @ExcludeHours Int

    -- Select delivery date as variable
    SELECT
        @DeliveryDate = DeliveryDate
    FROM
        UnitID
    WHERE
        Unit = @Unit;
   
    SET @MinDate = CASE WHEN @DeliveryDate > @DateLower THEN @DeliveryDate ELSE @DateLower END;
    
    SET @Hours = DATEDIFF(hour, @MinDate, @DateUpper) + 24;  -- kinda sketch

    IF @Hours < 0
        BEGIN
            SET @Hours = 0;
        END

    RETURN @Hours
END
GO
