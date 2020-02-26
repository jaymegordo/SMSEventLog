Merge FactoryCampaign t
    Using (Select a.Unit, Serial, Model, FCNumber, Status, Classification, Subject, DateCompleteSMS, Note From tempFC a Inner Join UnitID b on a.Unit=b.Unit) as s
    On t.Unit=s.Unit and t.FCNumber=s.FCNumber

When Matched
    Then Update SET
    t.Status = s.Status,
    t.Classification = s.Classification,
    t.subject = s.subject,
    t.DateCompleteSMS = s.DateCompleteSMS,
    t.Notes = s.Note

When Not Matched by TARGET
    Then INSERT (Unit, Serial, Model, FCNumber, Status, Classification, Subject, DateCompleteSMS, Notes)
        Values (s.Unit, s.serial, s.model, s.FCNumber, s.Status, s.Classification, s.Subject, s.DateCompleteSMS, s.Note);