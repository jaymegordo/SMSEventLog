ALTER VIEW dbo.viewFactoryCampaign
AS

SELECT
    *,
    CASE WHEN
            a.DateCompleteKA Is NULL AND a.DateCompleteSMS Is NULL
        THEN
            CAST(0 as BIT)
        ELSE
            CAST(1 as BIT)
    END As Complete
FROM FactoryCampaign a
;
