ALTER PROCEDURE [dbo].[mergeFCImport] AS

DECLARE @SummaryOfChanges TABLE(Change VARCHAR(20));

-- Count DateCompleteKA before/after to return count of changed values
DECLARE @beforecount INT;
DECLARE @aftercount INT;

SET @beforecount = (select count(DateCompleteKA) FROM FactoryCampaign);

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
            t.hours = s.hours,
            t.Classification = s.Classification
    
    WHEN NOT Matched by TARGET THEN
        INSERT (
            FCNumber, Model, [Serial], Unit, StartDate, EndDate, DateCompleteKA, [Subject], Classification, [Hours], Distributor, Branch, [Safety], [Status])
        VALUES (
            s.FCNumber, s.Model, s.Serial, s.Unit, s.StartDate, s.EndDate, s.DateCompleteKA, s.Subject, s.Classification, s.Hours, s.Distributor, s.Branch, s.Safety, s.Status)

    OUTPUT $action INTO @SummaryOfChanges;


SET @aftercount = (select count(DateCompleteKA) FROM FactoryCampaign);

SELECT Change, COUNT(*) AS CountPerChange
FROM @SummaryOfChanges
GROUP BY Change
UNION SELECT 'KA Dates Added', @aftercount - @beforecount;

TRUNCATE TABLE FactoryCampaignImport;
GO