Attribute VB_Name = "FactoryCampaigns"
Option Compare Text
Sub RefreshUnit_Show()
    refreshUnit
End Sub
Sub ReOpenFC()

    ans = MsgBox("This will unlink the selected FC from the work order and clear 'Date Complete SMS'. " _
            & dLine & "Are you sure you would like to continue?", vbYesNo + vbQuestion, "ReOpen FC")
    If ans <> vbYes Then Exit Sub
    
    Set e = createEventTable(ActiveCell)
'    e.PrintVars
    e.unlinkFC True
    
End Sub
Sub deleteFC()
    updateRecord_FC ActiveCell, Delete:=True
End Sub
Sub showFCList()
    Dim aFCSelector As New FCSelector
    aFCSelector.tag = "FCNum"
    aFCSelector.Show
End Sub
Sub SummaryPage_FC()
    viewFCDetials False
End Sub
Sub SummaryPage_Unit()
    viewFCDetials True
End Sub
Sub ButtonViewFCDetails()
    ViewFCDetails.Show
End Sub
Sub viewFCFolder()
    On Error GoTo errHandle
    
    iws = getWSInt(ActiveSheet.CodeName)
    
    Select Case iws
        Case 8 'FC Summary
            loadKeyVars iws, ActiveCell
        Case Else 'Use cEvent
            Set e = createEventTable(ActiveCell)
            aFCNumber = e.FCNumber
    End Select
    
    BasePath = "P:\Regional\SMS West Mining\Factory Campaigns"
    FullPath = BasePath & "\" & aFCNumber
    setFso
view:
    If FSO.FolderExists(FullPath) Then
        ThisWorkbook.FollowHyperlink FullPath
        Else
        ans = MsgBox("Can't find folder:" & dLine & FullPath & dLine & "Create now?", vbExclamation + vbYesNo)
        If ans = vbYes Then
            FSO.createFolder (FullPath)
            GoTo view
        End If
    End If

cleanup:
    Application.ScreenUpdating = True
    Application.EnableEvents = True
    Exit Sub
errHandle:
    sendErrMsg "viewFCFolder"
    Resume cleanup
End Sub

Sub closeFC()
    updateSingleFCSummary ActiveCell, True
End Sub
Sub updateSingleFCSummary(Target, Optional CloseOnly As Boolean = False)
    On Error GoTo errHandle
    iws = 8
    loadKeyVars iws, Target 'Should get rid of this to cEvent >this whole sub is sketch
    
    If CloseOnly Then
        ans = MsgBox("Are you sure you want to close FC " & aFCNumber _
            & "?", vbYesNo + vbQuestion, "Close FC")
        If ans <> vbYes Then GoTo cleanup
    End If
    
SetQuery:
    If numErrs > 1 Then Err.Raise 1234, "FCSummaryMineSite table could not be updated." 'stop sub from looping on errors
    
    Query = "SELECT FCSummaryMineSite.FCNumber, FCSummary.Classification, FCSummary.Hours, FCSummary.PartNumber, " _
                & "FCSummaryMineSite.PartAvailability, FCSummary.ReleaseDate, " _
                & "FCSummary.ExpiryDate, FCSummaryMineSite.Resp, " _
                & "FCSummaryMineSite.Comments, FCSummaryMineSite.ManualClosed, FCSummaryMineSite.MineSite " _
            & "FROM FCSummary LEFT JOIN FCSummaryMineSite " _
            & "ON FCSummary.FCNumber=FCSummaryMineSite.FCNumber " _
            & "WHERE FCSummary.FCNumber='" & aFCNumber _
            & "' AND FCSummaryMineSite.MineSite='" & getMineSite(True) & "'"
            
    
    Dim db As New cDB
    db.OpenConn
    db.rs.Open Query, db.conn, adOpenKeyset, adLockOptimistic
    'db.printRs
    
    If db.rs.RecordCount = 1 Then 'First try to update record in FCSummaryMineSite table
        'Debug.Print Query
        With db.rs
            .MoveFirst
            If CloseOnly Then
                !ManualClosed = True
                Else
                !Classification = dbr.Cells(i, 3) 'v sketch updating
                !Resp = dbr.Cells(i, 4)
                !Hours = dbr.Cells(i, 5)
                !PartNumber = dbr.Cells(i, 6)
                !PartAvailability = dbr.Cells(i, 7)
                !Comments = dbr.Cells(i, 8)
                !ReleaseDate = dbr.Cells(i, 9)
                !ExpiryDate = dbr.Cells(i, 10)
            End If
            .Update
        End With
        
        Else 'If no record in FCSummaryMineSite table, then add new one
        numErrs = numErrs + 1
        rs.Close
        db.rs.Open "FCSummaryMineSite", db.conn, adOpenKeyset, adLockOptimistic
        With db.rs
            .AddNew
            If CloseOnly Then
                !ManualClosed = True
                Else
                !FCNumber = aFCNumber
                !MineSite = getMineSite(True)
                !Resp = dbr.Cells(i, 4)
                !Comments = dbr.Cells(i, 8)
            End If
            .Update
        End With
        GoTo SetQuery
    End If
    
    If CloseOnly Then MsgBox "FC successfully closed."
    
cleanup:
    On Error Resume Next
    db.rs.Close
    Exit Sub
errHandle:
    sendErrMsg "updateSingleFCSummary"
    Resume cleanup
End Sub
Sub openWOfromFC()
    On Error GoTo errHandle
    'Open 'add new work order' form and fill FC details
    Set tbl = Sheet7.ListObjects("FC_Data")
    Set dbr = tbl.DataBodyRange
    
    IntersectCheck dbr
    
    i = ActiveCell.row - tbl.HeaderRowRange.row
    aUnit = dbr.Cells(i, 1)
    aFC = dbr.Cells(i, 2)
    
    Sheet2.Activate
    Set aAddEvent = New AddEvent
    With aAddEvent
        .tag = "x" 'set this property to stop AddEvent from launching the unit FC query
        .TextBox_Unit.value = aUnit
        .CheckBox_FC.value = True
        .TextBox_Title.value = "FC " & aFC & " - "
        .Show
    End With
    
    Exit Sub
errHandle:
    sendErrMsg "openWOfromFC"
End Sub

Sub updateRecord_FC(Target As Range, Optional Delete As Boolean = False) ' this should probably all be moved to cEvent
    On Error GoTo errHandle
    Application.ScreenUpdating = False
    Dim e As cEvent
    
    If Delete Then
        ans = MsgBox("Are you sure you want to delete the selected FC?", vbYesNo + vbQuestion, "Delete FC")
        If ans <> vbYes Then GoTo cleanup
    End If

    Application.EnableEvents = False
    
    Set e = createEventTable(Target)
    With e.rsFC(False)
        beforecount = .RecordCount
        Debug.Print beforecount
        If Delete Then
            .Delete
            MsgBox Abs(.RecordCount - beforecount) & " record deleted from database."
            GoTo cleanup
        End If
        
        !DateCompleteSMS = e.val("Date Complete SMS")
        !Notes = e.val("Notes")
        .Update
    End With
    
cleanup:
    On Error Resume Next
Cleanup2:
    Application.EnableEvents = True
    Exit Sub
errHandle:
    sendErrMsg "Uh oh, something went wrong!" & dLine _
                & "Not able to update record in Access Database. | updateRecord_FC" _

    Resume cleanup
End Sub

Sub importFC()
    On Error GoTo errHandle
    Application.ScreenUpdating = False
    Dim myFile As String 'actually a collection of strings i think?
    Dim ImpFolder As String
    rCount = 0
    DuplicateRec = 0
    NoRec = 0
    
    ImpFolder = "P:\Regional\SMS West Mining\SMS Event Log\Import FC\"
    myFile = Dir(ImpFolder & "*.xls*")
    
    loadDB
    Set rs = db.OpenRecordset(getTable(True), dbOpenTable)
    With rs
        beforecount = .RecordCount
        .Index = "PrimaryKey"
    End With
    
    'load secondary recordset for serial > unit number conversion
    Set rs2 = db.OpenRecordset("UnitID", dbOpenTable)
    With rs2
        .MoveLast 'do i need this...?
        .MoveFirst
        .Index = "ModelSerial"
    End With
    
    'Loop through each Excel file in folder
    Do While myFile <> ""
        Debug.Print myFile
        'GoTo next_file
        
        Set wb = Workbooks.Open(fileName:=ImpFolder & myFile)
        Set ws = wb.Sheets(1)
        DoEvents
        
        FirstRow = ws.Range("A:A").find("FC Number-Seq").row + 1 'find header row, changest sometimes
        LastRow = ws.Cells(Rows.Count, 2).End(xlUp).row
        TotalRows = LastRow - FirstRow + 1 + TotalRows
        
        For i = FirstRow To LastRow
            aUnit = ""
'            If i Mod 10 = 0 Then
'                Debug.Print i
'                DoEvents
'            End If
            aModel = getModel(ws.Cells(i, 4)) 'convert incorect model (eg double, 9.8E-2) to string. Only converts if temp model is a double. String is unchanged.
            aSerial = ws.Cells(i, 5)
            
            With rs2
                .Seek "=", aModel, aSerial
                If .NoMatch Then
                    NoRec = NoRec + 1
                    If Not (MissingSerials Like "*" & aSerial & "*") Then
                        MissingSerials = MissingSerials & aSerial & "; "
                        'Debug.Print "aSerial: " & aSerial & " | row: " & i
                    End If
                    GoTo NextRecord 'Could also check if serial exists in UnitID in case model no is different, would have to set different index each time tho
                    
                    Else
                    aUnit = !Unit
                End If
            End With
            
            aFCNumber = ws.Cells(i, 1)
            
            With rs
                .Seek "=", aFCNumber, aUnit 'LOL the order of these is important
                If .NoMatch Then
                    .AddNew
                    !Unit = aUnit
                    !FCNumber = aFCNumber
                    !Distributor = CInt(ws.Cells(i, 2))
                    !Branch = ws.Cells(i, 3)
                    !Model = aModel
                    !Serial = aSerial
                    !Safety = ws.Cells(i, 6)
                    !Subject = ws.Cells(i, 9)
                    
                    Else
                    DuplicateRec = DuplicateRec + 1
                    If IsNull(!DateCompleteKA) And IsDate(ws.Cells(i, 12)) Then dateKA = dateKA + 1
                    .Edit
                End If
                
                'Only edits some of the fields to save time
                !StartDate = Trim(ws.Cells(i, 7))
                !EndDate = Trim(ws.Cells(i, 8))
                    '!ClaimNumber = ws.Cells(i, 10) 'maybe don't need?
                    '!Completion SMR = ws.Cells(i, 11)
                !DateCompleteKA = ws.Cells(i, 12)
                    '!Status = ws.Cells(i, 13) 'Calculated field
                !Hours = ws.Cells(i, 14)
                !ServiceLetterdate = ws.Cells(i, 15)
                !Classification = ws.Cells(i, 16)
                .Update
            End With
NextRecord:
        Next i
        
        rCount = rCount + 1
        wb.Close SaveChanges:=False
        DoEvents
next_file:
        'Get next file name
        myFile = Dir
    Loop
    
    'GoTo cleanup
    
    rowsadded = rs.RecordCount - beforecount
    
    'Add new FCs to FC summary
    rowsAdded2 = appendFCSummary
    
    strFinal = "Reports opened: " & rCount & Line _
            & "Total FC rows in excel file(s): " & TotalRows & Line _
            & "Records added to access database: " & rowsadded & Line _
            & "Duplicate records updated: " & DuplicateRec & Line _
            & "KA completion dates added: " & dateKA & Line _
            & "Rows not matched to a unit number: " & NoRec & Line _
            & "New FCs added to FC Summary table: " & rowsAdded2
    If MissingSerials <> "" Then strFinal = strFinal & dLine & "(Check serials: " & MissingSerials & ")"
    MsgBox strFinal
    
cleanup:
    On Error Resume Next
    cleanupDB
    Exit Sub
errHandle:
    Select Case Err.Number
        Case 3021 'no current record
            Debug.Print aUnit, aFCNumber, "Error: " & Err.Number, Err.Description
            Resume NextRecord
        Case 3022 'duplicate record
            DuplicateRec = DuplicateRec + 1
            Debug.Print aUnit, aFCNumber, "Error: " & Err.Number, Err.Description
            Resume NextRecord
        Case Else
            sendErrMsg "ImportFC | Row: " & i
            Resume cleanup
    End Select
End Sub

Sub createCustomFieldTest()
    Dim strInput As String
    Dim aStr As String
    Dim testArr() As String
    Dim finalColl As New Collection
    FHUnits = False
    
    'Get string of units and parse into collection of all units
    strInput = "F301, F302, F303 - F314"
    strInput = InputBox("Input units separated by a comma for individuals, or dash for a range of units, eg: " & dLine & strInput & Line, "Input Units")
    If strInput = "" Then GoTo cleanup
    testArr = splitMultiDelims(strInput, ",")
    
    For i = 0 To UBound(testArr, 1)
        aStr = testArr(i)
        If aStr Like "*-*" Then 'split dash into range of individual units
            If aStr Like "*F*" Then FHUnits = True
            testArr2 = splitMultiDelims(aStr, "-")
            
            'extract unit number to create range, this only works with FH and BaseMine units
            aLower = Right(Trim(testArr2(0)), 3)
            aUpper = Right(Trim(testArr2(1)), 3)
            
            For y = aLower To aUpper
                ReDim Preserve testArr(0 To UBound(testArr, 1) + 1)
                If FHUnits = True Then addChar = "F"
                testArr(UBound(testArr, 1)) = CStr(addChar & y)
            Next y
        End If
    Next i
    
    For i = 0 To UBound(testArr, 1) 'Trim and eliminate dashes
        If Not testArr(i) Like "*-*" Then finalColl.add Trim(testArr(i))
    Next i
    
    Set finalColl = sortCollection(finalColl)
    
    For Each b In finalColl
        strCheckUnits = strCheckUnits & b & Line
    Next b
    
    ans = MsgBox("Would you like to add a custom field test for: " & Line & strCheckUnits, vbYesNo + vbQuestion, "Confirm Units")
    If ans = vbNo Then GoTo cleanup
    
    'Get details for custom FC and save to DB
    CustomFC.Show
    
    'Save to FCSummary table first > need to check for errors here first
'    Set rs = db.OpenRecordset("FCSummary", dbOpenTable)
    
    
    With rs
        .Index = "PrimaryKey"
        .Seek "=", aFCNumber
        If .NoMatch Then 'FC doesn't exist
            .AddNew
            !FCNumber = aFCNumber
            !Subject = aSubject
            !Classification = aClassification
            .Update
            
            Else 'FC already exists > dont change anything currently, but could edit the fields that user inputs?
            ans = MsgBox("FC already exists for some units, continue to add?", vbYesNo + vbQuestion)
            If ans <> vbYes Then GoTo cleanup
        End If
    End With
    rs.Close
    
    loadSerialRecordset
    Set rs = db.OpenRecordset("FactoryCampaign", dbOpenTable)
    With rs
        beforecount = .RecordCount
        .Index = "PrimaryKey"
        For i = 1 To finalColl.Count
            aUnit = finalColl(i)
            .Seek "=", aFCNumber, aUnit
            If .NoMatch = True Then
                .AddNew
                !Unit = aUnit
                !FCNumber = aFCNumber
                !Serial = getUnitSerial(finalColl(i))
                !Classification = aClassification
                !Subject = aSubject
                !Model = getUnitModel(finalColl(i))
                !Safety = "N"
                !ServiceLetterdate = aReleaseDate
                !EndDate = aExpiryDate
                .Update
            End If
        Next i
        aftercount = .RecordCount - beforecount
    End With
    
    MsgBox "Custom FC for " & aftercount & " unit(s) successfully added."
    
cleanup:
    On Error Resume Next
    cleanupDB
    Exit Sub
errHandle:
    If Err.Number = 3021 Then
    End If
    sendErrMsg "createCustomFieldTest"
    Resume cleanup
End Sub


Function appendFCSummary() As Integer
    Dim rs4 As DAO.Recordset
    rowsAdded2 = 0
    
    On Error GoTo errHandle
    'Add new FCs to FC summary > would rather this be an "INSERT INTO" but couldnt figure out how to ignore errors
    aQuery = "SELECT FCNumber, Subject, Classification, Hours, StartDate, EndDate FROM FactoryCampaign " _
            & "GROUP BY FCNumber, Subject, Classification, Hours, StartDate, EndDate"
    Set rs3 = db.OpenRecordset(aQuery, dbOpenDynaset)
    Set rs4 = db.OpenRecordset("FCSummary", dbOpenTable)
    With rs4
        .Index = "PrimaryKey"
        beforecount = .RecordCount
    End With
    
    With rs3
        .MoveFirst
        Do While .EOF <> True
            rs4.Seek "=", !FCNumber
            If rs4.NoMatch Then
                rs4.AddNew
                rs4!FCNumber = !FCNumber
                rs4!Subject = !Subject
                rs4!Classification = !Classification
                rs4!Hours = !Hours
                rs4!ReleaseDate = !StartDate
                rs4!ExpiryDate = !EndDate
                rs4.Update
                
                Else 'Check for different Hrs?
                
            End If
next_rec:
            .MoveNext
        Loop
    End With
    
    appendFCSummary = rs4.RecordCount - beforecount
    
cleanup:
    On Error Resume Next
    rs4.Close
    Set rs4 = Nothing
    rs3.Close
    Set rs3 = Nothing
    Exit Function
errHandle:
    If Err.Number = 3022 Then 'duplicate record
        Resume next_rec
    End If
    sendErrMsg "appendFCSummary"
    Resume cleanup
End Function
Sub addFCSelectedUnit()
    On Error GoTo errHandle
    setTblVars (8)
    IntersectCheck dbr, ActiveCell
    aRow = ActiveCell.row
    aUnit = Cells(tbl.HeaderRowRange.row, ActiveCell.Column)
    aFCNumber = Cells(aRow, tbl.HeaderRowRange(1).Column)
    
    ans = MsgBox("Add selected FC?" & dLine & "Unit: " & aUnit & Line & "FC: " & aFCNumber, vbYesNo + vbQuestion)
    If ans <> vbYes Then GoTo cleanup
    
    'load secondary recordset for serial > unit number conversion
    Set rs2 = db.OpenRecordset("UnitID", dbOpenTable)
    With rs2
        .MoveLast
        .MoveFirst
        .Index = "Unit"
        .Seek "=", aUnit
        If .NoMatch = False Then
            aSerial = !Serial
            aModel = !Model
            Else
            Err.Raise 444, "Unit not found in UnitID table."
        End If
    End With
    
    Set rs = db.OpenRecordset("FactoryCampaign", dbOpenTable)
    With rs 'Need to adjust column numbers if they change!! > bad coding, oh well too lazy
        .AddNew
        !Subject = Cells(aRow, 2)
        !EndDate = Cells(aRow, 10)
        !Unit = aUnit
        !FCNumber = aFCNumber
        !Serial = aSerial
        !Classification = Cells(aRow, 3)
        !Model = aModel
'        !Distributor = ""
'        !Branch = ""
'        !Safety = ""
'        !StartDate = ""
'        !ClaimNumber = ""
'        !Technician = ""
        !Hours = Cells(aRow, 5)
        !ServiceLetterdate = Cells(aRow, 9)
        .Update
    End With
    
cleanup:
    On Error Resume Next
    cleanupDB
    Exit Sub
errHandle:
    sendErrMsg "addFCSelectedUnit"
    Resume cleanup
End Sub
Sub viewFCDetials(refUnit As Boolean)
    On Error GoTo errHandle
    Dim e As cEvent
    Set e = createEventTable(ActiveCell)
    Dim f As New cFilter
    
    If Not refUnit Then
        f.Filter2.add "FactoryCampaign.FCNumber=", e.FCNumber
        
        Else
        aCol = ActiveCell.Column
        If aCol < 11 Then
            MsgBox "Please select a unit."
            GoTo cleanup
        End If
        f.Filter2.add "FactoryCampaign.Unit=", e.tbl.HeaderRowRange(1, aCol)
    End If
    
    RefreshTable iws:=7, f:=f
    Sheet7.Activate
    Sheet7.Cells(5, 1).Activate
    
cleanup:
    On Error Resume Next
    Exit Sub
errHandle:
    sendErrMsg "viewFCDetials"
    Resume cleanup
End Sub
Function loadFCRecords() As ADODB.Recordset
    On Error GoTo errHandle
    Application.ScreenUpdating = False
    
    Query = "SELECT Distinct FactoryCampaign.FCNumber, t.calcSubj " _
            & "FROM  (Select FCNumber, IIF(SubjectShort Is Null, Subject, SubjectShort) as calcSubj From FCSummary) as t " _
            & "RIGHT JOIN FactoryCampaign on t.FCNumber=FactoryCampaign.FCNumber "
    
    Dim db As New cDB
    db.OpenConn
    db.rs.Open Query, db.conn, adOpenStatic, adLockReadOnly
    
    Set loadFCRecords = db.rs

cleanup:
    On Error Resume Next
'    db.closeConn
    Exit Function
errHandle:
    sendErrMsg "loadFCRecords"
    Resume cleanup
End Function
Sub refreshFCSummaryButton()
    ViewFC.Show
End Sub
Sub refreshFCSummary(f As cFilter)
    On Error GoTo errHandle
    Application.ScreenUpdating = False
    Application.EnableEvents = False
    Set tbl = Sheet8.ListObjects(1)
    Set dbr = tbl.DataBodyRange
    
    UnitCol = 13
    rowState = getState("row")
            
    Query = "Declare @sql as varchar(max) " _
            & "Declare @Cols as varchar(max) " _
            & "Select @Cols = Coalesce(@Cols + ', ','') + QUOTENAME(Unit) " _
            & "From (Select Distinct Unit From UnitID " _
                & f.FilterSpecific("MineSite, Model", True) & ") As UnitList " _
            & "Set @sql='" _

            replaceQuery = "Select * From (" _
                & "SELECT UnitID.Unit, IIF(FactoryCampaign.Classification='FT','FT',IIf(EventLog.DateCompleted Is Null And " _
                & "FactoryCampaign.DateCompleteSMS Is Null And FactoryCampaign.DateCompleteKA Is Null,'N','Y')) AS calcStatus, " _
                & "FCSummary.FCNumber, IIf(FCSummary.SubjectShort Is Null, FCSummary.Subject, FCSummary.SubjectShort) As CalcSubject, " _
                & "FCSummary.Classification, tFCS.Resp, FCSummary.Hours, FCSummary.PartNumber, tFCS.PartAvailability, tFCS.Comments, " _
                & "FCSummary.ReleaseDate, FCSummary.ExpiryDate, '' As Prog, 0 As ProgPercent " _
                & "FROM (SELECT * " _
                & "From FCSummaryMineSite " & f.FilterSpecific("MineSite", True) & ") as tFCS " _
                & "RIGHT JOIN (EventLog RIGHT JOIN (FCSummary INNER JOIN (UnitID INNER JOIN FactoryCampaign ON UnitID.Unit = FactoryCampaign.Unit) " _
                & "ON FCSummary.FCNumber = FactoryCampaign.FCNumber) ON EventLog.UID = FactoryCampaign.UID) " _
                & "ON tFCS.FCNumber = FCSummary.FCNumber " _
            & f.Filter & ") as t1 " _
            
            Query = Query & Replace(replaceQuery, "'", "''") _
            & " Pivot (" _
                & "Max (calcStatus) " _
                & "For t1.Unit In(' + @Cols + ') " _
            & ") as pTable " _
            & "ORDER BY Classification DESC, FCNumber' Exec(@sql)"
            
    'Debug.Print Query
    Loading.Show vbModeless
    DoEvents
    
    Dim db As New cDB
    With db
        .OpenConn
        .rs.Open Query, db.conn, adOpenStatic, adLockReadOnly
    End With
    
    'Dynamically adjust the table columns based on query result. Typically will only change btwn minesites or when new units are added.
    LastCol = tbl.ListColumns.Count
    rsFieldCount = db.rs.Fields.Count
    If rsFieldCount <> LastCol Then
        If rsFieldCount > LastCol Then
            For y = 1 To rsFieldCount - LastCol
                tbl.ListColumns.add (LastCol - 1)
            Next y
            Else
            For y = LastCol - 1 To rsFieldCount Step -1
                tbl.ListColumns(y).Delete
            Next y
        End If
        
        For i = UnitCol To tbl.ListColumns.Count
            tbl.HeaderRowRange(1, i) = db.rs.Fields(i - 1).Name
        Next i
    End If
    
    db.loadToTable tbl
    For i = 1 To CLng(db.rs.RecordCount)
        yCount = 0
        nCount = 0
        For y = UnitCol To dbr.Columns.Count
            Select Case dbr.Cells(i, y)
                Case "Y", "FT"
                    yCount = yCount + 1
                Case "N"
                    nCount = nCount + 1
                    Select Case dbr.Cells(i, 3)
                        Case "M"
                            nCountM = nCountM + 1
                        Case Else
                            nCountElse = nCountElse + 1
                    End Select
            End Select
        Next y
        Total = yCount + nCount
        dbr.Cells(i, 11) = yCount & " / " & Total
        dbr.Cells(i, 12) = yCount / Total
    Next i
    
    Sheet8.Cells(1, 3) = nCountM
    Sheet8.Cells(2, 3) = nCountElse
    
cleanup:
    On Error Resume Next
    expandCollapseRows True, CBool(rowState)
    Application.EnableEvents = True
    Loading.Hide
    Exit Sub
errHandle:
    sendErrMsg "refreshFCSummary"
    Resume cleanup
End Sub

Function getModel(aModel)
    On Error GoTo errHandle
    If IsNumeric(aModel) = True Then
        Select Case aModel
            Case 0.098
                getModel = "980E-4"
            Case 0.093
                getModel = "930E-4"
            Case 0.93
                getModel = "930E-3"
            Case 0.0000073
                getModel = "730E-8"
            Case "9.3E-23"
                getModel = "930E-23"
            Case "9.3E-21"
                getModel = "930E-21"
            Case Else
                getModel = ""
                'Err.Raise 123, Description:="Couldn't convert model properly."
        End Select
        Else
        getModel = aModel
    End If

cleanup:
    On Error Resume Next
    Exit Function
errHandle:
    sendErrMsg "getModel | aModel: " & aModel
    Resume cleanup
End Function

Sub emailFCSummary()
    On Error GoTo errHandle
    Application.ScreenUpdating = False
    Application.EnableEvents = False
    iws = 8
    setTblVars iws
    
    Dim wbe As New cwbExport
    With wbe
        .createWb "FC Summary - " & Format(Now, "yyyy-mm-dd") & ".xlsm"
        .addWs ThisWorkbook.Worksheets("FC Details")  'Details
        .addWs ThisWorkbook.Worksheets("FC Summary") 'Summary
        .wbDest.Sheets(1).visible = False
        
        .ws(1).Shapes(1).visible = msoFalse
        .ws(2).Shapes(2).visible = msoFalse
        .ws(2).Shapes(1).GroupItems(1).OnAction = "'" & .wbDest.Name & "'!expandCollapseCols"
        .ws(2).Shapes(1).GroupItems(2).OnAction = "'" & .wbDest.Name & "'!expandCollapseRows"
        .ws(1).ListObjects(1).HeaderRowRange.Font.ColorIndex = 2
        .ws(2).ListObjects(1).HeaderRowRange.Font.ColorIndex = 2
        .CopyModule "Functions"
        .copyColours
        .wbDest.Close True
    End With
    
    strbody = "Good " & getGreeting & ", " & Line _
            & "Please see attached FC Summary for complete/outstanding units."
    With tbl.ListColumns(2).DataBodyRange.Resize(, 11)
        .Interior.Color = xlNone
        .Font.bold = False
    End With
    
    'Preserve row and column expand/collapse states during copy
    colState = getState("col")
    rowState = getState("row")
    expandCollapseCols True, False
    expandCollapseRows True, True
    tbl.ListColumns(1).Range.Resize(, 12).Copy
    
    Set outlookApp = CreateObject("Outlook.Application")
    Set outMail = outlookApp.CreateItem(olMailItem)
    With outMail
        Set wdDoc = .GetInspector.WordEditor
        .To = getEmailList("FCSummary")
        .Subject = wbe.DestName
        .Attachments.add wbe.FilePath
        pasteIntoEmail wdDoc, strbody
        .display
    End With
    
cleanup:
    On Error Resume Next
    expandCollapseCols True, CBool(colState)
    expandCollapseRows True, CBool(rowState)
    wbe.deleteDestWb
    Application.CutCopyMode = False
    Application.EnableEvents = True
    Exit Sub
errHandle:
    sendErrMsg "emailFCSummary"
    Resume cleanup
End Sub
Sub renameFCSubject(e As cEvent)
    On Error GoTo errHandle
    ans = MsgBox("Would you like to change the short title of FC " & e.FCNumber & " to: " & dLine & e.Cell.value, vbYesNo + vbQuestion, "Change FC Title")
    If ans <> vbYes Then
        MsgBox "Short title not updated in database."
        GoTo cleanup
    End If
    
    Query = "SELECT * FROM FCSummary WHERE FCNumber ='" & e.FCNumber & "'"
    Dim db As New cDB
    db.OpenConn
    db.rs.Open Query, db.conn, adOpenStatic, adLockOptimistic
    
    With db.rs
        !SubjectShort = e.Cell.value
        .Update
    End With
    
    MsgBox "Title successfully changed."

cleanup:
    On Error Resume Next
    db.rs.Close
    Exit Sub
errHandle:
    sendErrMsg "renameFCSubject"
    Resume cleanup
End Sub



''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''
' SplitMultiDelims by alainbryden
' This function splits Text into an array of substrings, each substring
' delimited by any character in DelimChars. Only a single character
' may be a delimiter between two substrings, but DelimChars may
' contain any number of delimiter characters. It returns a single element
' array containing all of text if DelimChars is empty, or a 1 or greater
' element array if the Text is successfully split into substrings.
' If IgnoreConsecutiveDelimiters is true, empty array elements will not occur.
' If Limit greater than 0, the function will only split Text into 'Limit'
' array elements or less. The last element will contain the rest of Text.
''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''
Function splitMultiDelims(ByRef Text As String, ByRef DelimChars As String, _
        Optional ByVal IgnoreConsecutiveDelimiters As Boolean = False, _
        Optional ByVal Limit As Long = -1) As String()
    Dim ElemStart As Long, n As Long, M As Long, Elements As Long
    Dim lDelims As Long, lText As Long
    Dim arr() As String
    
    lText = Len(Text)
    lDelims = Len(DelimChars)
    If lDelims = 0 Or lText = 0 Or Limit = 1 Then
        ReDim arr(0 To 0)
        arr(0) = Text
        splitMultiDelims = arr
        Exit Function
    End If
    ReDim arr(0 To IIf(Limit = -1, lText - 1, Limit))
    
    Elements = 0: ElemStart = 1
    For n = 1 To lText
        If InStr(DelimChars, Mid(Text, n, 1)) Then
            arr(Elements) = Mid(Text, ElemStart, n - ElemStart)
            If IgnoreConsecutiveDelimiters Then
                If Len(arr(Elements)) > 0 Then Elements = Elements + 1
            Else
                Elements = Elements + 1
            End If
            ElemStart = n + 1
            If Elements + 1 = Limit Then Exit For
        End If
    Next n
    'Get the last token terminated by the end of the string into the array
    If ElemStart <= lText Then arr(Elements) = Mid(Text, ElemStart)
    'Since the end of string counts as the terminating delimiter, if the last character
    'was also a delimiter, we treat the two as consecutive, and so ignore the last elemnent
    If IgnoreConsecutiveDelimiters Then If Len(arr(Elements)) = 0 Then Elements = Elements - 1
    
    ReDim Preserve arr(0 To Elements) 'Chop off unused array elements
    splitMultiDelims = arr
End Function

