Attribute VB_Name = "Cummins_Import"
'Function CumminsExport() As String
'    Dim wbNew As Workbook
'    Dim wsNew As Worksheet
'    Dim rngNew As Range
'    Set wbNew = Workbooks.add
'    Set wsNew = wbNew.Sheets(1)
'    Set tbl = Sheet1.ListObjects(1)
'    Set dbr = tbl.DataBodyRange
'    Dim rngCopy As Range
'
'    'Get passover range from event log and export to new workbook
'    Set rngCopy = dbr.Rows(1).Resize(tbl.ListColumns(2).Range.End(xlDown).row - tbl.HeaderRowRange.row)
'    Set rngNew = wsNew.Cells(1, 1).Resize(rngCopy.Rows.Count, rngCopy.Columns.Count)
'    rngNew.value = rngCopy.value
'
'    'Save temp workbook and return save location string to email function
'    sPath = Environ$("temp") & "\Cummins Export-v2.xlsx"
'    wbNew.SaveAs sPath
'    wbNew.Close
'    CumminsExport = sPath
'
'End Function
'
'Sub importCummins()
'    disableCummins
'    On Error GoTo errHandle
'    Dim WBC As Workbook
'    Dim WSC As Worksheet
'    Dim Version As Integer
'    Application.ScreenUpdating = False
'
'    'Get selected email and import
'    Dim objOL As Object 'Outlook.Application
'    Dim objAttachments As Object 'Outlook.Attachments
'    Dim objSelection As Object 'Outlook.Selection
'
'    TempFilePath = Environ$("temp") & "\"
'
'    Set objOL = CreateObject("Outlook.Application")
'    Set objSelection = objOL.ActiveExplorer.Selection
'
'    If objSelection.Count < 1 Then
'        MsgBox "No emails selected in Outlook, try again dummy!", vbExclamation
'        End
'    End If
'
'    'Save attachment to temp file
'    Set objAttachments = objSelection(1).Attachments
'    strFile = objAttachments.Item(1).fileName
'    strFile = TempFilePath & Left(strFile, Len(strFile) - 5) & Format(Now, "yyyy-mm-dd-hh-mm-nn") & ".xlsx"
'    objAttachments.Item(1).SaveAsFile strFile
'
'    If strFile Like "*v2*" Then
'        Version = 2
'        'Debug.Print "Version: " & Version
'        Else
'        Version = 1
'    End If
'
'    aDatabase = getTable
'    MineSite = getMineSite
'    loadDB
'
'    Set WBC = Workbooks.Open(strFile)
'    Set WSC = WBC.Worksheets(1)
'
'    Select Case Version
'        Case 1
'            Set dbr = WSC.ListObjects(1).DataBodyRange
'        Case 2
'            Set dbr = WSC.Cells(1, 1).Resize(WSC.Columns(1).End(xlDown).row, 14)
'            Set rs = db.OpenRecordset(aDatabase, dbOpenTable)
'            rs.Index = "PrimaryKey"
'    End Select
'
'    Countrows = dbr.Rows.Count
'
'    For i = 1 To Countrows
'        Select Case Version
'            Case 1 'Old Version
'                With dbr
'                    aStatusEvent = .Cells(i, 2)
'                    aUnit = .Cells(i, 3)
'                    aTitle = .Cells(i, 4)
'                    aDescription = .Cells(i, 5)
'                    aRequired = .Cells(i, 6)
'                    aDateAdded = .Cells(i, 7)
'                    aDateCompleted = .Cells(i, 8)
'                    aIssueCategory = .Cells(i, 9)
'                    aSubCategory = .Cells(i, 10)
'                    aCause = .Cells(i, 11)
'                End With
'
'                If aTitle Like "*'*" Then aTitle = Replace(aTitle, "'", "") 'remove apostrophe from title
'
'                aQuery = "SELECT * From " & aDatabase & " WHERE Unit = '" & aUnit & "' AND Title = '" & aTitle & "' AND DateAdded = #" & aDateAdded & "#"
'                Set rs = db.OpenRecordset(aQuery, dbOpenDynaset)
''                With rs
''                    .MoveLast
''                    .MoveFirst
''                End With
'
'                Select Case rs.RecordCount
'                    Case 0 'add new
'                        rs.Close
'                        Set rs = db.OpenRecordset(aDatabase, dbOpenTable)
'                        If aUID = Null Then
'                            aUID = 1 & Format(Now, "ddhhnnssms")
'                            Else
'                            aUID = 1 & Format(Now + (0.001 * i), "ddhhnnssms")
'                        End If
'
'                        With rs
'                            .AddNew
'                            !UID = aUID
'                            !MineSite = MineSite
'                            !PassoverSort = "x"
'                            !StatusEvent = aStatusEvent
'                            !Unit = aUnit
'                            !Title = aTitle
'                            !Description = aDescription
'                            !Required = aRequired
'                            !DateAdded = aDateAdded
'                            !DateCompleted = aDateCompleted
'                            !IssueCategory = aIssueCategory
'                            !SubCategory = aSubCategory
'                            !Cause = aCause
'                            !CreatedBy = "Cummins"
'                            !TimeCalled = aTimeCalled
'                            .Update
'                            .Close
'                        End With
'                        UnitNew = UnitNew & aUnit & ", "
'
'                    Case 1 'edit
'                        With rs
'                            .Edit
'                            !StatusEvent = aStatusEvent
'                            !Description = aDescription
'                            !Required = aRequired
'                            !DateCompleted = aDateCompleted
'                            !IssueCategory = aIssueCategory
'                            !SubCategory = aSubCategory
'                            !Cause = aCause
'                            !TimeCalled = aTimeCalled
'                            .Update
'                            .Close
'                        End With
'                        UnitUpdate = UnitUpdate & aUnit & ", "
'
'                    Case Else
'                        Debug.Print aQuery
'                        Debug.Print "something's wack, too many records"
'                End Select
'
'            Case 2 'New Version
'                With dbr
'                    aUID = .Cells(i, 1)
'                    aStatusEvent = .Cells(i, 3)
'                    aUnit = .Cells(i, 4)
'                    aTitle = .Cells(i, 5)
'                    aDescription = .Cells(i, 6)
'                    aRequired = .Cells(i, 7)
'                    aDateAdded = .Cells(i, 8)
'                    aDateCompleted = .Cells(i, 9)
'                    aIssueCategory = .Cells(i, 10)
'                    aSubCategory = .Cells(i, 11)
'                    aCause = .Cells(i, 12)
'                    aTimeCalled = .Cells(i, 14)
'                End With
'
'                With rs
'                    .Seek "=", aUID
'                    If .NoMatch = True Then
'                        .AddNew
'                        !UID = aUID
'                        !MineSite = MineSite
'                        !PassoverSort = "x"
'                        !Unit = aUnit
'                        !Title = aTitle
'                        !DateAdded = aDateAdded
'                        !DateCompleted = aDateCompleted
'                        !CreatedBy = "Cummins"
'
'                        UnitNew = UnitNew & aUnit & ", "
'
'                        Else
'                        .Edit
'                        !DateCompleted = aDateCompleted
'
'                        UnitUpdate = UnitUpdate & aUnit & ", "
'                    End If
'
'                    !TimeCalled = aTimeCalled
'                    !IssueCategory = aIssueCategory
'                    !SubCategory = aSubCategory
'                    !Cause = aCause
'                    !Required = aRequired
'                    !Description = aDescription
'                    !StatusEvent = aStatusEvent
'                    .Update
'                End With
'        End Select
'
'RecordCheck:
'        'Debug.Print "i :" & i & " RecordCount: " & RecordCount
'    Next i
'
'    WBC.Close False
'
'    If UnitNew = "" Then
'        NewMessage = "No new events added."
'        Else
'        NewMessage = "New event(s) added for unit(s): " & UnitNew & "."
'    End If
'
'    If UnitUpdate = "" Then
'        UpdateMessage = "No existing events updated."
'        Else
'        UpdateMessage = "Event(s) updated for unit(s): " & UnitUpdate & "."
'    End If
'
'    MsgBox "New events added: " & UnitNew & vbNewLine & vbNewLine & "Existing events Updated: " & UnitUpdate
'    Sheet1.Activate
'    RefreshTable
'
'cleanup:
'    On Error Resume Next
'    Kill strFile
'    Application.EnableEvents = True
'    cleanupDB
'    Exit Sub
'errHandle:
'    If Err.Number = 3021 Then
'        RecordCount = 0
'        Resume RecordCheck
'    End If
'    'No current record
'    If Err.Number = 440 Then ErrMsg = "No 'Cummins Export' file in selected email message."
'    sendErrMsg ErrMsg & "Not able to import Cummins events. | CumminsImport"
'    Resume cleanup
'End Sub
'
'Sub test()
'aTitle = "Egt's"
'If aTitle Like "*'*" Then aTitle = Replace(aTitle, "'", "")
'Debug.Print aTitle
'
'End Sub
