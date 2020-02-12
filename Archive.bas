Attribute VB_Name = "Archive"


'Sub Basic_Web_Query()
''"URL;https://docs.google.com/spreadsheet/ccc?key=0Ah4Bis8FTYfCdDJILVdYOG1EZEYtc1N3NF96dHZSYkE&usp=sharing#gid=0", Destination:=Range("$A$1"))
'    With ActiveSheet.QueryTables.Add(Connection:= _
'        "URL;https://docs.google.com/spreadsheets/d/1cSV85R5fsza9-ylOGTiQ-KmVX6J_VEYE79DD7tGl5Fo/edit#gid=187683052", Destination:=Range("$A$1"))
'        .Name = "q?s=goog_2"
'        .FieldNames = True
'        .RowNumbers = False
'        .FillAdjacentFormulas = False
'        .PreserveFormatting = True
'        .RefreshOnFileOpen = False
'        .BackgroundQuery = True
'        .RefreshStyle = xlInsertDeleteCells
'        .SavePassword = False
'        .SaveData = True
'        .AdjustColumnWidth = True
'        .RefreshPeriod = 0
'        .WebSelectionType = xlSpecifiedTables
'        .WebFormatting = xlWebFormattingNone
'        .WebTables = "1,2"
'        .WebPreFormattedTextToColumns = True
'        .WebConsecutiveDelimitersAsOne = True
'        .WebSingleBlockTextImport = False
'        .WebDisableDateRecognition = False
'        .WebDisableRedirections = False
'        .Refresh BackgroundQuery:=False
'    End With
'End Sub


'----------------Email folder search stuff
'Sub msgtest()
'    Dim outlookApp As Object 'Outlook.Application
'    Dim olNs As Object ' Outlook.Namespace
'    Dim Fldr As Object 'Outlook.MAPIFolder
'    Dim olMail As Variant
'    Dim objMsg As Object 'Outlook.MailItem
'    Dim objAttach As Object 'Outlook.Attachment
'
'    Set outlookApp = CreateObject("Outlook.Application")
'    Set olNs = outlookApp.GetNamespace("MAPI")
'    Set Fldr = olNs.GetDefaultFolder(6).Parent.Folders("Wo Request") '6 = olFolderInbox
'    Set Items = Fldr.Items
'    MsgCount = Items.Count
'    Debug.Print "msgcount", MsgCount
'
'    Set objMsg = Fldr.Items(MsgCount)
'    aEmail = objMsg.Subject
'
''    Debug.Print aEmail
'End Sub

'Sub updateRecordOld(Target As Range) 'accept target cell and sheet number, check for intersect
'    On Error GoTo errHandle
'    setTblVars iws
'
'    If Intersect(Target, dbr) Is Nothing Then Exit Sub
'    WriteCheck
'    Application.EnableEvents = False
'    i = getActiveRow(tbl, Target)
'    aUID = dbr.Cells(i, 1)
'
'    loadDB
'    Set rs = db.OpenRecordset(getUIDQuery, dbOpenDynaset)
'    DoEvents
'
'    Select Case iws
'        Case 1
'            With rs
'                .Edit
'                !PassoverSort = dbr.Cells(i, 2)
'                !StatusEvent = dbr.Cells(i, 3)
'                If dbr.Cells(i, 3) = "Complete" And !WarrantyYN = "No" Then !StatusWO = "Closed" 'Auto close non warranty WOs on Event close
'                !Unit = dbr.Cells(i, 4)
'                If getMineSite = "BaseMine" Then !Title = dbr.Cells(i, 5)
'                !Description = dbr.Cells(i, 6)
'                !Required = dbr.Cells(i, 7)
'                !DateAdded = dbr.Cells(i, 8)
'                !DateCompleted = dbr.Cells(i, 9)
'                !IssueCategory = dbr.Cells(i, 10)
'                !SubCategory = dbr.Cells(i, 11)
'                !Cause = dbr.Cells(i, 12)
'                !CreatedBy = dbr.Cells(i, 13)
'                !TimeCalled = dbr.Cells(i, 14)
'                .Update
'            End With
'
'        Case 2
''            If Target.value = "Closed" Then 'this would overwrite if it already had a date value
''                If dbr.Cells(i, 15) = "" Then dbr.Cells(i, 15) = DateValue(Now)
''            End If
'            With rs
'                .Edit
'                !StatusWO = dbr.Cells(i, 2)
'                !WarrantyYN = dbr.Cells(i, 3)
'                !WorkOrder = dbr.Cells(i, 4)
'                !Seg = dbr.Cells(i, 5)
'                !SuncorWO = dbr.Cells(i, 6)
'                !SuncorPO = dbr.Cells(i, 7)
'                !Unit = dbr.Cells(i, 8)
'                If getMineSite = "BaseMine" Then !Title = dbr.Cells(i, 10)
'                !PartNumber = dbr.Cells(i, 11)
'                !SMR = dbr.Cells(i, 12)
'                !DateAdded = dbr.Cells(i, 13)
'                !DateCompleted = dbr.Cells(i, 14)
'                !CreatedBy = dbr.Cells(i, 15)
'                !WOComments = dbr.Cells(i, 16)
'                !ComponentCO = dbr.Cells(i, 17)
''                !Downloads = dbr.Cells(i, 18)
''                !Pictures = dbr.Cells(i, 19)
''                !CCOS = dbr.Cells(i, 20)
'                .Update
'            End With
'
'        Case 10
'            With rs
'                .Edit
'                !StatusTSI = dbr.Cells(i, 2)
'                !DateInfo = dbr.Cells(i, 4)
'                !DateTSISubmission = dbr.Cells(i, 5)
'                !TSINumber = dbr.Cells(i, 6)
'                !WorkOrder = dbr.Cells(i, 7)
'                !SMR = dbr.Cells(i, 11)
'                !ComponentSMR = dbr.Cells(i, 12)
'                !TSIPartName = dbr.Cells(i, 13)
'                !PartNumber = dbr.Cells(i, 14)
'                !SNRemoved = dbr.Cells(i, 15)
'                !TSIDetails = dbr.Cells(i, 16)
'                !TSIAuthor = dbr.Cells(i, 17)
'                .Update
'            End With
'
'        Case Else
'            GoTo errHandle
'    End Select
'
'cleanup:
'    On Error Resume Next
'    rs.Close
'    Set rs = Nothing
'    If dbClose Then cleanupDB
'    Application.EnableEvents = True
'    Exit Sub
'errHandle:
'    sendErrMsg "Uh oh, something went wrong!" & dLine & "Not able to update record in Access Database. Ensure new rows " _
'            & "have been added with the built in function so a UID is generated. | updateRecords "
'    Resume cleanup
'End Sub


'Sub UpdateFlags(iws, Optional iws2 As Integer)
'    On Error GoTo errHandle
'    If (getSaveCount(1).value > 0 Or getSaveCount(2).value > 0) And getWriteMode = "Write" Then
'        UpdatingChanges.Show vbModeless
'    DoEvents
'
'LoopAgain:
'    setTblVars iws
'
'        For i = 1 To dbr.Rows.Count
'            Set Target = dbr.Cells(i, 1)
'            If Target.Interior.Color = RGB(255, 0, 0) Then
'                updateRecord Target, iws, False
'                Target.Interior.Color = xlNone
'                'Debug.Print "Updated: " & Target
'            End If
'        Next i
'        Set SaveCount = getSaveCount(iws)
'        SaveCount = 0
'
'        If iws2 > 0 Then
'            iws = iws2
'            iws2 = -1
'            GoTo LoopAgain 'loops through EventLog and WorkOrders if savecount > 0 in either and TSI???
'        End If
'
'cleanup:
'    On Error Resume Next
'    UpdatingChanges.Hide
'    Application.ScreenUpdating = True
'End If
'    Exit Sub
'errHandle:
'    sendErrMsg "Hmm, something went wrong!" & dLine & "Couldn't update row(s) in database. | UpdateFlags "
'    Resume cleanup
'End Sub
