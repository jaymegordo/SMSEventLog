-- MERGE target_table USING source_table
-- ON merge_condition
-- WHEN MATCHED
--     THEN update_statement
-- WHEN NOT MATCHED 
--     THEN insert_statement
-- WHEN NOT MATCHED BY SOURCE
--     THEN DELETE;

Merge FCSummary t
    Using (SELECT FCNumber, Subject, Classification, Hours, StartDate, EndDate FROM FactoryCampaign
        GROUP BY FCNumber, Subject, Classification, Hours, StartDate, EndDate) as s
    On t.FCNumber = s.FCNumber

When Not Matched by TARGET
    Then INSERT (FCNumber, Subject, Classification, Hours, ReleaseDate, ExpiryDate)
        Values (s.FCNumber, s.Subject, s.Classification, s.Hours, s.StartDate, s.EndDate);

