SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
ALTER PROCEDURE [dbo].[mergeFCSummary]

AS

SET ANSI_WARNINGS OFF;
SET NOCOUNT ON;
DECLARE @SummaryOfChanges TABLE(Change VARCHAR(20), [FCNumber] VARCHAR(100), [Subject] VARCHAR(200));

MERGE FCSummary t 
    USING (
        SELECT * 
        FROM (
            SELECT 
                a.FCNumber,
                a.Subject, 
                a.Classification, 
                a.Hours, 
                a.StartDate, 
                a.EndDate, 
                ROW_NUMBER() OVER(
                    PARTITION BY a.FCNumber 
                    ORDER BY a.FCNumber, a.Hours DESC, a.EndDate DESC) RN 
            FROM FactoryCampaign a
            GROUP BY 
                a.FCNumber, a.Subject, a.Classification, a.Hours, a.StartDate, a.EndDate) a
        WHERE a.RN=1) as s
    On t.FCNumber = s.FCNumber
    
    WHEN Matched THEN
        UPDATE SET
            t.Subject = s.Subject,
            t.Hours = CASE WHEN s.Hours > t.Hours THEN s.Hours ELSE t.Hours END,
            t.ReleaseDate = s.StartDate,
            t.ExpiryDate = CASE WHEN s.EndDate > t.ExpiryDate THEN s.EndDate ELSE t.ExpiryDate END
    
    WHEN NOT Matched by TARGET THEN
        INSERT (
            FCNumber, [Subject], Classification, [Hours], ReleaseDate, ExpiryDate)
        VALUES (
            s.FCNumber, s.Subject, s.Classification, s.Hours, s.StartDate, s.EndDate)
        
    OUTPUT 
        -- Can't figure out why, but 'Deleted' seems to work fine for $action='UPDATE' too
        $action,
        CASE WHEN $action = 'INSERT' THEN Inserted.FCNumber ELSE Deleted.FCNumber END,
        CASE WHEN $action = 'INSERT' THEN Inserted.Subject ELSE Deleted.Subject END
    INTO @SummaryOfChanges;

-- Return two cursors to be used to display confirmation to user
SELECT Change, COUNT(*) AS CountPerChange
FROM @SummaryOfChanges
GROUP BY Change;

SELECT FCNumber, [Subject] From @SummaryOfChanges
WHERE Change='INSERT'
ORDER BY FCNumber;

GO

-- TODO: Remove 'udfMergeFCSummary' file once change to python is complete