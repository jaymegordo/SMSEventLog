SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
ALTER PROCEDURE [dbo].[mergeFCImport] 

AS

SET ANSI_WARNINGS OFF;
SET NOCOUNT ON;
DECLARE @SummaryOfChanges TABLE(Change VARCHAR(20));
DECLARE @beforecount INT;
DECLARE @aftercount INT;

SET @beforecount = (select COUNT(DateCompleteKA) FROM FactoryCampaign);

MERGE FactoryCampaign t 
    USING (
        SELECT *
        FROM FactoryCampaignImport) as s
    ON t.FCNumber=s.FCNumber AND t.Unit=s.Unit
    
    WHEN Matched THEN
        UPDATE SET
            t.StartDate = s.StartDate,
            t.EndDate = s.EndDate,
            t.DateCompleteKA = s.DateCompleteKA,
            t.Classification = s.Classification
            -- t.hours = s.hours,
    
    WHEN NOT Matched by TARGET THEN
        INSERT (
            FCNumber, Model, [Serial], Unit, StartDate, EndDate, DateCompleteKA, [Subject], Classification, Branch, [Status])
        VALUES (
            s.FCNumber, s.Model, s.Serial, s.Unit, s.StartDate, s.EndDate, s.DateCompleteKA, s.Subject, s.Classification, s.Branch, s.Status)

    OUTPUT $action INTO @SummaryOfChanges;

TRUNCATE TABLE FactoryCampaignImport;

SET @aftercount = (select count(DateCompleteKA) FROM FactoryCampaign);

SELECT Change, COUNT(*) AS CountPerChange
FROM @SummaryOfChanges
GROUP BY Change
UNION SELECT 'KADatesAdded', @aftercount - @beforecount;


GO
