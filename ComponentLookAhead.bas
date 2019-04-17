Attribute VB_Name = "ComponentLookAhead"
Option Compare Text

Sub refreshLookAhead()
    RefreshTable
End Sub
Sub emailLookAhead()
    On Error GoTo errHandle
    setTblVars 12
    
    Set outlookApp = CreateObject("Outlook.Application")
    Set outMail = outlookApp.CreateItem(olMailItem)
    
    aWeek = Application.WorksheetFunction.Min(tbl.ListColumns(1).DataBodyRange)
    
    strbody = "Good " & getGreeting & ", " & dLine & "The component look ahead has been categorized starting at week " & aWeek _
            & ". Please view the info using the SMS Event Log."
    
    With outMail
        .To = getEmailList("PRP")
        .Subject = "Component Look Ahead - Week " & aWeek
        .body = strbody
        .display
    End With
    
cleanup:
    On Error Resume Next
    Exit Sub
errHandle:
    sendErrMsg "emailLookAhead"
    Resume cleanup
End Sub
Sub updateLookAheadRow(Target)
    On Error GoTo errHandle
    Application.ScreenUpdating = False
    setTblVars 12
    If Intersect(tbl.ListColumns(12).DataBodyRange, Target) Is Nothing And Intersect(tbl.ListColumns(9).DataBodyRange, Target) Is Nothing Then Exit Sub
    
    i = Target.row - tbl.HeaderRowRange.row
    aSuncorWO = dbr.Cells(i, 8)
    loadDB
    
    aQuery = "SELECT * FROM ComponentLookAhead WHERE SuncorWO = " & aSuncorWO
    Set rs = db.OpenRecordset(aQuery, dbOpenDynaset)
    With rs
        .Edit
        !SMSWO = dbr.Cells(i, 9)
        !Category = dbr.Cells(i, 12)
        .Update
    End With
    
cleanup:
    On Error Resume Next
    cleanupDB
    Exit Sub
errHandle:
    sendErrMsg "updateLookAheadRow"
    Resume cleanup
End Sub
Sub importLookAhead()
    On Error GoTo errHandle
    Application.ScreenUpdating = False
    Dim myFile As String
    DuplicateRec = 0
    NoRec = 0
    delRec = 0
    
    ImpFolder = "P:\Regional\SMS West Mining\SMS Event Log\Import Component Look Ahead\"
    
    ans = MsgBox("Please ensure one 'MEM Look Ahead' excel file is located in: " & Line & ImpFolder & dLine _
            & "Would you like to begin the import?", vbYesNo, "Import Location")
    If ans = vbNo Then GoTo cleanup
    
    myFile = Dir(ImpFolder & "*.xls*")
    Set wb = Workbooks.Open(fileName:=ImpFolder & myFile)
    Set ws = wb.Sheets(1)
    DoEvents
    
    loadDB
    Set rs = db.OpenRecordset("ComponentLookAhead", dbOpenTable)
    With rs
        .Index = "SuncorWO"
        .MoveLast
        .MoveFirst
        beforecount = .RecordCount
        
'        'Mark current records as old to be removed after new import
'        .MoveFirst
'        Do While .EOF <> True
'            .Edit
'            !old = True
'            .Update
'            .MoveNext
'        Loop
    End With
    
    FirstRow = 3
    LastRow = ws.Cells(Rows.Count, 1).End(xlUp).row
    TotalRows = LastRow - FirstRow + 1
    
    For i = FirstRow To LastRow
        If (Left(ws.Cells(i, 13), 3) <> "F03" And Left(ws.Cells(i, 13), 3) <> "F02") Or ws.Cells(i, 11) Like "*TRS*" Then
            ExcludeRec = ExcludeRec + 1
            GoTo NextRecord
        End If
RetryUpdate:
        With rs
            .Seek "=", ws.Cells(i, 10)
            If .NoMatch = False Then
                .Edit
                !old = False
                UpdateRec = UpdateRec + 1
                Else
                .AddNew
            End If
            !Week = CInt(Right(ws.Cells(i, 1), Len(ws.Cells(i, 1)) - InStr(1, ws.Cells(i, 1), "/")))
            !Status = ws.Cells(i, 5)
            !StartDate = ws.Cells(i, 9)
            !SuncorWO = ws.Cells(i, 10)
            !MainWC = ws.Cells(i, 11)
            !Description = ws.Cells(i, 12)
            If ws.Cells(i, 12) Like "*FC*" Then !Category = "FC"
            If ws.Cells(i, 12) Like "*cummins*" Then !Category = "Cummins"
            !Floc = ws.Cells(i, 13)
            !DueDate = ws.Cells(i, 15)
            !WOType = ws.Cells(i, 16)
            If ws.Cells(i, 16) = "MPRG" Then !Category = "Service"
            !DueWeek = CInt(Right(ws.Cells(i, 17), Len(ws.Cells(i, 17)) - InStr(1, ws.Cells(i, 17), "/")))
            .Update
        End With
NextRecord:
    Next i
    
'    'Delete all old records
'    With rs
'        .MoveFirst
'        Do While .EOF <> True
'            If !old = True Then
'                .Delete
'                delRec = delRec + 1
'            End If
'            .MoveNext
'        Loop
'    End With
    
    wb.Close SaveChanges:=False
    rowsadded = rs.RecordCount - beforecount
    
    strFinal = "Total rows in excel file: " & TotalRows & Line _
            & "Records added to access database: " & rowsadded & Line _
            & "Rows excluded (non trucks): " & ExcludeRec & Line _
            & "Existing records updated: " & UpdateRec & Line
            '& "Old records deleted: " & delRec
    MsgBox strFinal
    
cleanup:
    On Error Resume Next
    cleanupDB
    Exit Sub
errHandle:
    Select Case Err.Number
        Case 3021 'no record found
            Resume NextRecord
        Case 3022 'duplicate record
            DuplicateRec = DuplicateRec + 1
            Resume NextRecord
        Case 13 'Type mismatch
            Resume NextRecord
        Case Else
            sendErrMsg "importLookAhead | Row: " & i
            Resume cleanup
    End Select
End Sub
