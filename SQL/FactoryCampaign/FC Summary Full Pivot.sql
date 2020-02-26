Declare @sql as varchar(max)
Declare @Cols as varchar(max)
Select @Cols = Coalesce(@Cols + ', ','') + QUOTENAME(Unit)
From (Select Distinct Unit From UnitID Where MineSite='FortHills' And Model Like '980%') As UnitList

Set @sql= '
Select * From (
    SELECT UnitID.Unit, IIF(FactoryCampaign.Classification="FT","FT",IIf(EventLog.DateCompleted Is Null And FactoryCampaign.DateCompleteSMS Is Null And FactoryCampaign.DateCompleteKA Is Null,"N","Y")) AS calcStatus, FCSummary.FCNumber, IIf(FCSummary.SubjectShort Is Null, FCSummary.Subject, FCSummary.SubjectShort) As CalcSubject, FCSummary.Classification, tFCS.Resp, FCSummary.Hours, FCSummary.PartNumber, tFCS.PartAvailability, tFCS.Comments, FCSummary.ReleaseDate, FCSummary.ExpiryDate, "" As Prog, 0 As ProgPercent
    FROM (SELECT *
        FROM FCSummaryMineSite
        WHERE MineSite="FortHills") as tFCS
            RIGHT JOIN (EventLog 
                RIGHT JOIN (FCSummary 
                    INNER JOIN (UnitID 
                        INNER JOIN FactoryCampaign 
                    ON UnitID.Unit = FactoryCampaign.Unit) 
                ON FCSummary.FCNumber = FactoryCampaign.FCNumber) 
            ON EventLog.UID = FactoryCampaign.UID) 
        ON tFCS.FCNumber = FCSummary.FCNumber
    WHERE UnitID.MineSite="FortHills" And (tFCS.ManualClosed="False" OR tFCS.ManualClosed Is Null)
) as t1'
set @sql = Replace(@sql,'"','''') + '
Pivot (
    Max(calcStatus)
    For t1.Unit In(' + @Cols + ')
) as pTable
ORDER BY Classification DESC, FCNumber'
Exec(@sql)