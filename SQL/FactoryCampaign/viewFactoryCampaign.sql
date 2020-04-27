SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
ALTER VIEW [dbo].[viewFactoryCampaign]
AS

SELECT
    a.UID,
    a.Unit,
    a.FCNumber,
    a.Serial,
    a.Model,
    CASE WHEN
            a.DateCompleteKA Is NULL and
            a.DateCompleteSMS Is NULL and
            c.DateCompleted Is NULL
        THEN
            CAST(0 as BIT)
        ELSE
            CAST(1 as BIT)
    END As Complete,
    a.Classification,
    b.Hours,
    CASE WHEN
            b.SubjectShort Is NULL
        THEN
            a.Subject
        ELSE
            b.SubjectShort
    END As Subject,
    CASE WHEN
            a.DateCompleteSMS Is Null
        THEN
            c.DateCompleted
        ELSE
            a.DateCompleteSMS
    END as DateCompleteSMS,
    a.DateCompleteKA,
    c.SMR,
    a.StartDate,
    a.EndDate, 
    a.Notes
FROM FactoryCampaign a
    LEFT JOIN FCSummary b on a.FCNumber=b.FCNumber
        LEFT JOIN EventLog c on a.UID=c.UID
;



GO
