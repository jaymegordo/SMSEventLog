Attribute VB_Name = "ComponentCO"
Option Compare Text


Sub loopSunbench()
'    On Error GoTo errHandle
    loadDB
    Set rs = db.OpenRecordset("EventLog", dbOpenTable)
    
    aQuery = "SELECT Sun_CO_Records.* FROM Sun_CO_Records INNER JOIN UnitID ON Sun_CO_Records.Unit = UnitID.Unit " _
            & " WHERE UnitID.Model Like '*980E*' AND Sun_CO_Records.Moved=False Order By Sun_CO_Records.Unit, DateAdded "
    
    Set rsSunBench = db.OpenRecordset(aQuery, dbOpenDynaset)

    With rsSunBench
        .MoveLast
        .MoveFirst
'        Debug.Print .RecordCount
'        For i = 0 To .Fields.Count - 1
'            Debug.Print .Fields(i).Name
'        Next i

'        GoTo cleanup
        Do While .EOF <> True
            aUnit = !Unit
            aDate = !DateAdded
            aComponent = !Component
            aModifier = !Modifier
            aFloc = getFloc(aComponent, aModifier)
            
            linkCORecord
            
            .MoveNext
        Loop
    End With

cleanup:
    On Error Resume Next
    rs.Close
    rsSunBench.Close
    db.Close
    Set db = Nothing
    Exit Sub
errHandle:
    sendErrMsg "loopSunbench"
    Resume cleanup
End Sub
Sub linkCORecord()
    strAdd = aUnit & " | " & aDate & " | " & aComponent & ", " & aModifier
    aQuery = "SELECT * FROM EventLog WHERE Unit ='" & aUnit & "' AND DateAdded Between #" & aDate - 10 & "# AND #" & aDate + 10 & "# AND Title <> Null Order By DateAdded"
    Set rs3 = db.OpenRecordset(aQuery, dbOpenDynaset)
    With rs3
        If .RecordCount > 0 Then 'add items to listbox
            LinkCO.ListBox1.clear
            Do While .EOF <> True
                LinkCO.ListBox1.AddItem !Unit & " | " & !DateAdded & " | " & !Title
                .MoveNext
            Loop
            LinkCO.TextBox1.value = strAdd
            LinkCO.Show
            
            Else 'No records in date range found, have to add new record
            Debug.Print "None in date rng - Adding: " & strAdd
            addEditCORecordFromSunBench aRecordset:=rs, EditOnly:=False
            'addEditCORecordfromGoogleSheet aRecordset:=rs
        End If
    End With
End Sub
Sub addEditCORecordFromSunBench(aRecordset As DAO.Recordset, Optional EditOnly As Boolean = False)
    On Error GoTo errHandle
    
    'Adding to either rs (eventlog TABLE) OR rs3 (linkco dialog DYNASET from eventlog) from rsSunBench
    With aRecordset
        Select Case EditOnly
            Case False 'AddNew > should probs be to rs only?
                
                 aUID = createUID
                
                Debug.Print "AddNew: ", aUnit, aDate, aComponent, aModifier
                
                .AddNew
                !UID = aUID
                !MineSite = "BaseMine" 'getMineSiteUnit(aUnit)
                !Unit = aUnit
                !DateAdded = aDate
                !Title = aComponent & " " & aModifier & " - CO"

            Case True 'Found, edit existing
                .Edit
                aUID = !UID
        End Select
        
        !Floc = aFloc
        !WorkOrder = rsSunBench!WorkOrder
        !WarrantyYN = rsSunBench!WarrantyYN
        !SuncorWO = rsSunBench!SuncorWO
        !SuncorPO = rsSunBench!SuncorPO
        !SMR = rsSunBench!SMR
        !ComponentSMR = rsSunBench!ComponentSMR
        !PartNumber = rsSunBench!PartNumber
        !SNRemoved = rsSunBench!SNRemoved
        !RemovalReason = rsSunBench!RemovalReason
        !CapUSD = rsSunBench!CapUSD
        !GroupCO = rsSunBench!GroupCO
        !ComponentCO = True
        
        .Update
        
    End With
    
    With rsSunBench
        .Edit
        !UID = aUID
        !Moved = True
        .Update
    End With
    
cleanup:
    Exit Sub
errHandle:
    sendErrMsg "addEditCORecordFromSunBench"
    Resume cleanup
End Sub
Sub refreshComponentCO()
    LoadComponents.Show
End Sub
Sub refreshComponentForecast(Optional MineSite As String)
    On Error GoTo errHandle
    iws = 16
    setTblVars iws
    Loading.Show vbModeless
    DoEvents 'allow the form to load and display its text
    
    ClearFilter tbl
    Application.EnableEvents = False
    Application.ScreenUpdating = False
    ClearTable tbl
    
    dbr.Cells(1, 1).Resize(2, dbr.Columns.Count).FillDown 'this keeps the formulas in the last columns from being blank. adds ~1s, messy, should find a better way
    
    aQuery = " SELECT t3.MineSite, t3.Model, t3.Unit, t3.Component, t3.Modifier, t3.BenchSMR, t3.CurrentUnitSMR, t2.LastCO " _
            & "FROM (SELECT UnitID.MineSite, UnitID.Model, UnitID.Unit,  ComponentType.Component, ComponentType.Modifier, ComponentType.Floc, " _
                & "ComponentType.BenchSMR, t1.CurrentUnitSMR " _
                & "FROM ComponentType, (SELECT UnitID.Unit, ((Date()- Max(UnitSMR.DateSMR))*20)+Max(UnitSMR.SMR) AS CurrentUnitSMR FROM UnitID " _
                    & "LEFT JOIN UnitSMR ON UnitID.Unit = UnitSMR.Unit GROUP BY UnitID.Unit)  AS t1 " _
                    & "INNER JOIN UnitID ON t1.Unit = UnitID.Unit " _
                & "WHERE (((UnitID.Model) Like '%980E%') AND ((UnitID.MineSite)='FortHills') )) as t3 " _
                & "LEFT JOIN (SELECT EventLog.Unit, EventLog.Floc, Max(EventLog.SMR) AS LastCO FROM EventLog " _
                & "WHERE ComponentCO=True GROUP BY EventLog.Unit, EventLog.Floc) " _
            & "AS t2 ON t2.Floc = t3.Floc AND t2.Unit = t3.Unit " _
            & "ORDER BY t3.Unit, t3.Floc"
        'AND ((UnitID.MineSite)='FortHills')
        ' AND ((ComponentType.Major)=True)
        
    loadDB
    Set rs = db.OpenRecordset(aQuery, dbOpenDynaset)
    dbr.Cells(1, 1).CopyFromRecordset rs

cleanup:
    On Error Resume Next
    Loading.Hide
    cleanupDB
    Application.ScreenUpdating = True
    Application.EnableEvents = True
    Exit Sub
errHandle:
    Select Case Err.Number
        Case 3008
            ErrMsg = "The database is currently locked by another user or undergoing maintenance, try again shortly!"
        Case -2147467259
            ErrMsg = "Bad record in database, let Jayme know!"
        Case Else
            ErrMsg = "Oops! Something went wrong! Not able to refresh table."
        'Case 3078
            'network access interupted
    End Select
    ErrMsg = ErrMsg & " | refreshComponentForecast"
    sendErrMsg ErrMsg
    Resume cleanup
End Sub

Sub getActiveCol()
    Debug.Print ActiveCell.Column
End Sub

Sub scanGSheet()
    On Error GoTo errHandle
    LinkEvents = True
    Set ws = Sheet17
    FirstRow = 2
    LastRow = ws.Cells(Rows.Count, 1).End(xlUp).row
    loadDB
    Set rs = db.OpenRecordset("EventLog", dbOpenTable)
    Set rs2 = db.OpenRecordset("UnitID", dbOpenTable) 'need this to exclude bad units
    rs2.Index = "Unit"
    
    'need to loop once first to check for new CO records, count them, then ask if user would like to link records before refreshing tables.
    
    With rs
        .Index = "SuncorWOFloc"
        For i = FirstRow To LastRow
            aUnit = replaceUnitZero(ws.Cells(i, 1))
            If checkUnitExists(aUnit) = False Then
                skipUnit = skipUnit + 1
                GoTo next_i
            End If
            
            aSuncorWO = ws.Cells(i, 2)
            If IsNumeric(aSuncorWO) = False Then GoTo next_i
            
            aDate = ws.Cells(i, 3)
            aComponent = ws.Cells(i, 6)
            If aComponent Like "*spindle*" Then aComponent = "Spindle"
            If checkComponent(aComponent) = False Then
                skipComp = skipComp + 1
                GoTo next_i
            End If
            
            aModifier = parseModifier(ws.Cells(i, 7))
            aFloc = getFloc(aComponent, aModifier)
            aRemovalReason = ws.Cells(i, 11)
            aSNRemoved = ws.Cells(i, 20)
            aSNInstalled = ws.Cells(i, 23)
            aWarrantyYN = parseWarranty(ws.Cells(i, 35))

            .Seek "=", aSuncorWO, aFloc
            
            If .NoMatch = True Then 'need to check and link or create new event
                Missing = Missing + 1
                If LinkEvents = True Then linkCORecord
                
                Else
                Present = Present + 1
                If !ComponentCO = True Then 'already linked, move on > this could change once supervisors confirm component CO on entry**
                    COTrue = COTrue + 1
                    
                    Else 'not linked, need to add values to existing event > already seeked to correct record
                    COFalse = COFalse + 1
                    addEditCORecordfromGoogleSheet rs, True
                    
                End If
            End If
next_i:
        Next i
    End With
    
cleanup:
    On Error Resume Next
    Debug.Print "skipUnit: "; skipUnit
    Debug.Print "skipComp: "; skipComp
    Debug.Print "Missing: "; Missing
    Debug.Print "Present: "; Present
    Debug.Print "COTrue: "; COTrue
    Debug.Print "COFalse: "; COFalse
    cleanupDB
    Exit Sub
errHandle:
    sendErrMsg "scanGSheet"
    Resume cleanup
End Sub
'Sub addCOManual()
'    loadDB
'    Set rs = db.OpenRecordset("EventLog", dbOpenTable)
'
'End Sub



Sub addEditCORecordfromGoogleSheet(aRecordset As DAO.Recordset, Optional EditOnly As Boolean = False)
    On Error GoTo errHandle
    With aRecordset
        Select Case EditOnly
            Case False 'AddNew
                .AddNew
                !UID = createUID
                !MineSite = getMineSiteUnit(aUnit)
                !WarrantyYN = aWarrantyYN
                !Unit = aUnit
                !Title = aComponent & " " & aModifier & " - CO"
                !DateAdded = aDate
                !SuncorWO = aSuncorWO
                !SMR = getUnitSMR(aUnit, aDate)
                
            Case True 'Should already be seeked to correct record
                .Edit

        End Select
        If IsNumeric(aSuncorWO) Then !SuncorWO = aSuncorWO
        If IsNumeric(!SMR) = False Then !SMR = getUnitSMR(aUnit, aDate)
        
        !RemovalReason = aRemovalReason
        !ComponentCO = True
        !Floc = getFloc(aComponent, aModifier)
        !SNRemoved = aSNRemoved
        !SNInstalled = aSNInstalled
        .Update
    End With
cleanup:
    Exit Sub
errHandle:
    sendErrMsg "addEditCORecordfromGoogleSheet"
    Resume cleanup
End Sub


Function checkComponent(aWord) As Boolean
    If rs5 Is Nothing Then Set rs5 = db.OpenRecordset("ComponentType", dbOpenTable)
    With rs5
        .Index = "ComponentModifier"
        .Seek "=", aWord
        If .NoMatch = False Then
            checkComponent = True
            Else
            checkComponent = False
            'Debug.Print aUnit & " | " & aWord
        End If
    End With
End Function
Function parseModifier(aWord)
    If aWord Like "*left*" Then
        parseModifier = "LH"
        ElseIf aWord Like "*right*" Then
            parseModifier = "RH"
            Else
            parseModifier = ""
    End If
End Function
Function parseWarranty(aWord)
    Select Case True
        Case aWord Like "*Warranty*"
            parseWarranty = "Yes"
        Case aWord Like "*PRP*"
            parseWarranty = "PRP"
        Case Else
            parseWarranty = "No"
    End Select
End Function
Sub importCompCO()
    'Import Zeroed components from SAP > currently using Suncor FH's GoogleSheet for changeouts
    On Error GoTo errHandle
    Application.ScreenUpdating = False
    Dim aSuncorWO As Variant
    FirstRow = 2
    ImpFolder = "P:\Regional\SMS West Mining\SMS Event Log\Component Tracking\Import Component CO\"
    myFile = Dir(ImpFolder & "*.xlsx*")
    
    ans = MsgBox("Found file: " & myFile & dLine _
            & "Would you like to begin the import?", vbYesNo, "Import Component Changeouts")
    If ans = vbNo Then GoTo cleanup
    
    loadDB
    Set rs = db.OpenRecordset("ComponentCO", dbOpenTable)
    beforecount = rs.RecordCount
    Set rs2 = db.OpenRecordset("UnitSMR", dbOpenTable)
    rs2.Index = "UnitDate"
    Set rs3 = db.OpenRecordset("UnitID", dbOpenTable)
    rs3.Index = "Unit"

    Set wb = Workbooks.Open(fileName:=ImpFolder & myFile)
    'Set wb = ActiveWorkbook
    Set ws = wb.Sheets(1)
    LastRow = ws.Cells(Rows.Count, 1).End(xlUp).row
    
    With rs
        .Index = "UnitFlocDate"
        For i = FirstRow To LastRow
            If ws.Cells(i, 3) = 0 Then
                aStrFloc = ws.Cells(i, 1)
                aUnit = "F" & Mid(aStrFloc, 3, 3) 'InStr(1,ws.Cells(2,1),"-")
                aFloc = Right(aStrFloc, Len(aStrFloc) - 6)
                aDate = ws.Cells(i, 2)
                aNotes = ws.Cells(i, 4)

                If aDate > getDeliveryDate(aUnit) + 5 Then
                    .Seek "=", aUnit, aFloc, aDate
                    
                    'find lower to upper range of '0' period
                    b = i
                    Do While ws.Cells(b + 1, 1) = aStrFloc And ws.Cells(b + 1, 3) = 0
                        b = b + 1
                    Loop
                    
                    If .NoMatch = True Then
                        For y = i To b 'find line that has comment
                            If ws.Cells(y, 4) <> "" Then
                                aNotes = ws.Cells(y, 4)
                                aSuncorWO = Mid(aNotes, InStrRev(aNotes, " ") + 1, 8)
                                Exit For
                            End If
                        Next y
                        
                        aUnitSMR = getUnitSMR(aUnit, aDate)
                        aSMR = getComponentSMR(aUnit, aFloc, aDate, aUnitSMR)
                        
                        'Debug.Print "i: " & i & " b: " & b & " | " & aUnit & " | " & aFloc & " | " & aDate & " | " & aSMR & " | " & aNotes & " | " & aSuncorWO
                        strComponentsCO = strComponentsCO & aUnit & " | " & aFloc & " | " & aDate & " | UnitSMR:" & Format(aUnitSMR, "#,###") & " | ComponentSMR:" & Format(aSMR, "#,###") & " | " & aNotes & dLine
                        
                        .AddNew
                        !Unit = aUnit
                        !Floc = aFloc
                        !DateCO = aDate
                        !UnitSMR = aUnitSMR
                        !SMR = aSMR
                        !Notes = aNotes
                        If IsNumeric(aSuncorWO) Then !WO_Customer = aSuncorWO
                        .Update
                        
                        Else 'CO record exists
                        DuplicateRec = DuplicateRec + 1
                    End If
                    i = b ' set i to upper so we can resume after the hrs have been reset to 0
                End If
            End If
next_i:
        'DoEvents
        Next i
    End With
    
    rCount = rCount + 1
    wb.Close SaveChanges:=False

    rowsadded = rs.RecordCount - beforecount
    
    FinalMessage = "Records added to access database: " & rowsadded & Line _
            & "Duplicate records skipped: " & DuplicateRec & dLine _
            & strComponentsCO
    
    MsgBox FinalMessage

cleanup:
    cleanupDB
    Exit Sub
errHandle:
    If Err.Number = 3022 Then
        Debug.Print dbr.Cells(i, 1) & " | " & dbr.Cells(i, 2) & " | " & dbr.Cells(i, 3)
        Resume next_i
    End If
    sendErrMsg "importCompCO"
    Resume cleanup
End Sub
Function getComponentSMR(aUnit, aFloc, aDate, Optional aUnitSMR) 'adds smr to each componoent CO record in table
    'OLD > not using EventLog yet
    On Error GoTo errHandle
    
    prevSMR = 0
    aQuery = "SELECT * FROM ComponentCO WHERE Floc ='" & aFloc & "' AND Unit ='" & aUnit & "' AND DateCO <#" & aDate & "# ORDER BY DateCO DESC"
    
    Set rs4 = db.OpenRecordset(aQuery, dbOpenDynaset)
    With rs4
        If .RecordCount > 0 Then
            .MoveFirst
            prevSMR = getUnitSMR(!Unit, !DateCO)
            'Debug.Print PrevSMR
        End If
    End With
    
    If IsMissing(aUnitSMR) Then
        getComponentSMR = getUnitSMR(aUnit, aDate) - prevSMR
        Else
        getComponentSMR = aUnitSMR - prevSMR
    End If
    'Debug.Print !Unit & " | " & !Floc & " | " & !DateCO & " | " & CurSMR
    
cleanup:
    On Error Resume Next
    rs4.Close
    Set rs4 = Nothing
    Exit Function
errHandle:
    sendErrMsg "getComponentSMR"
End Function

Function getUnitSMR(Unit, aDate) As Long
    On Error GoTo errHandle
    Dim f As New cFilter
    f.add "Unit=", Unit
    f.add "DateSMR<=", aDate
    Query = "Select DateSMR, SMR From UnitSMR " & f.Filter & " Order By DateSMR Desc"
    
    Dim db As New cDB
    db.OpenConn
    db.rs.Open Query, db.conn, adOpenStatic, adLockReadOnly
    
    With db.rs
        .MoveFirst
        If .RecordCount > 0 Then
            getUnitSMR = !SMR
            Else
            Err.Raise 444, "can't find SMR for Unit: " & Unit & ", Date: " & aDate
        End If
    End With
    
cleanup:
    On Error Resume Next
    db.rs.Close
    Exit Function
errHandle:
    sendErrMsg "getUnitSMR"
    Resume cleanup
End Function
Function getDeliveryDate(aUnit) As Date
    With rs3
        .Seek "=", aUnit
        If .NoMatch = False Then
            If IsDate(!DeliveryDate) Then
                getDeliveryDate = !DeliveryDate
                
                Else
                'Debug.Print "No delivery date."
                getDeliveryDate = DateValue(Now)
            End If
            
            Else
            Debug.Print "Can't find unit: " & aUnit
        End If
    End With
End Function
Sub importUnitHrs()
    On Error GoTo errHandle
    Application.ScreenUpdating = False
    DuplicateRec = 0
    FirstRow = 2
    ImpFolder = "P:\Regional\SMS West Mining\SMS Event Log\Component Tracking\Import Unit Hours\"
    
    ans = MsgBox("Please ensure 'Unit SMR' .xlsx file is located in: " & Line & ImpFolder & dLine _
            & "Would you like to begin the import?", vbYesNo, "Import Location")
    If ans = vbNo Then GoTo cleanup

    myFile = Dir(ImpFolder & "*.xlsx*")
    Set wb = Workbooks.Open(fileName:=ImpFolder & myFile)
    Set ws = wb.Sheets(1)
    DoEvents
    LastRow = ws.Cells(Rows.Count, 1).End(xlUp).row
    
    loadDB
    Set rs2 = db.OpenRecordset("UnitSMR", dbOpenTable)
    With rs2
        beforecount = .RecordCount
        .Index = "UnitDate"
        
        For i = FirstRow To LastRow
            aUnit = "F" & Right(ws.Cells(i, 1), 3)
            aDate = ws.Cells(i, 2)
            .Seek "=", aUnit, aDate
            
            If .NoMatch Then
                .AddNew
                !Unit = aUnit
                !DateSMR = aDate
                !SMR = ws.Cells(i, 3)
                .Update
                Else
                DuplicateRec = DuplicateRec + 1
            End If
next_i:
        Next i
    End With
    
    rCount = rCount + 1
    wb.Close SaveChanges:=False

    rowsadded = rs2.RecordCount - beforecount
    
    FinalMessage = "Reports opened: " & rCount & Line _
            & "Records added to access database: " & rowsadded & Line _
            & "Duplicate records skipped: " & DuplicateRec & dLine
    
    MsgBox FinalMessage

cleanup:
    On Error Resume Next
    cleanupDB
    Exit Sub
errHandle:
    sendErrMsg "importUnitHours"
    Resume cleanup
End Sub
Function getComponentCOQuery(e As cEvent) As String
    getComponentCOQuery = "SELECT EventLog.* FROM EventLog LEFT JOIN ComponentType ON ComponentType.Floc = EventLog.Floc " _
            & "WHERE Unit='" & e.Unit & "' AND EventLog.Floc='" & e.Floc & "' AND DateAdded=#" & e.DateEvent & "#"
End Function
Sub updateCompCO()
    On Error GoTo errHandle
    iws = 15
    
    Dim e As cEvent
    Set e = createEventTable(ActiveCell)
    e.Floc = getFloc(e.Component, e.Modifier)
    
    Set rs = db.OpenRecordset(getComponentCOQuery(e), dbOpenDynaset)
    With rs
        Select Case .RecordCount
            Case 1
                .Edit
            
            Case 0
                .AddNew
                !UID = createUID
                !Unit = e.Unit
                If aModifier <> "" Then
                    !Title = e.Component & ", " & e.Modifier & " - CO"
                    Else
                    !Title = e.Component & " - CO"
                End If
                !Floc = e.Floc
                !DateAdded = e.DateEvent
                !ComponentCO = True
                !MineSite = e.MineSite

            Case Else
                Debug.Print .RecordCount
                Err.Raise 400, , "More than 1 component CO record found."
        End Select
        
        !GroupCO = e.val("Group CO")
        !SMR = e.val("Unit SMR")
        !ComponentSMR = e.val("Comp SMR")
        !SNRemoved = e.val("Sn Removed")
        !SNInstalled = e.val("SN Installed")
        !WarrantyYN = e.val("Wtny")
        !CapUSD = e.val("CapUSD")
        !WorkOrder = e.val("SMS WO")
        !SuncorWO = e.val("Customer WO")
        !SuncorPO = e.val("Customer PO")
        !RemovalReason = e.val("Notes")
        !COConfirmed = e.val("Details Conf")
        .Update
        
        'Creates string with each field and item updated for MsgBox
        .MoveFirst
        Dim arrHeader() As Variant
        arrHeader = Array("Unit", "Floc", "GroupCO", "DateAdded", "SMR", "ComponentSMR", "SNRemoved", "SNInstalled", "WarrantyYN", "CapUSD", _
                            "WorkOrder", "SuncorWO", "SuncorPO", "RemovalReason", "COConfirmed")
        For i = LBound(arrHeader) To UBound(arrHeader)
            strUpdate = strUpdate & arrHeader(i) & ": " & .Fields(arrHeader(i)).value & Line
        Next i
    End With
    
    MsgBox "Component CO record updated." & dLine & strUpdate
    
cleanup:
    cleanupDB
    Exit Sub
errHandle:
    sendErrMsg "updateCompCO"
    Resume cleanup
End Sub

Sub addSMR() 'Corrects Unit and Component SMR for each CO record in EventLog
    'On Error GoTo errHandle
    loadDB
    'EventLog.Unit='F333' AND
    aQuery = "SELECT EventLog.Unit, DateAdded, Floc, SMR, ComponentSMR FROM EventLog LEFT JOIN UnitID ON EventLog.Unit = UnitID.Unit WHERE ComponentCO = True AND Model Like '*980E*' ORDER BY EventLog.Unit, DateAdded"
    
    Set rs = db.OpenRecordset(aQuery, dbOpenDynaset)
    Set rs2 = db.OpenRecordset("UnitSMR", dbOpenTable)
    rs2.Index = "UnitDate"
    
    With rs
        Do While .EOF <> True
            prevSMR = getUnitSMRPrevCO(!Unit, !DateAdded, !Floc) 'Previous Unit SMR
            UnitSMR = getUnitSMR(!Unit, !DateAdded) 'Unit SMR at DateAdded
            
            .Edit
            !SMR = UnitSMR
            !ComponentSMR = UnitSMR - prevSMR
            'Debug.Print !Unit & " | " & !Floc & " | " & !DateCO & " | " & CurSMR
            .Update
            .MoveNext
        Loop
    End With
    cleanupDB
    
End Sub
Function getUnitSMRPrevCO(Unit As String, aDate As Date, Optional Floc, _
            Optional Component, Optional Modifier, Optional Complain As Boolean = False)
    On Error GoTo errHandle
    
    If IsMissing(Floc) Then aFloc = getFloc(Component, Modifier)
    
    Dim f As New cFilter
    f.add "Unit=", Unit
    f.add "Floc=", Floc
    f.add "DateAdded<'" & aDate & "'"
    
    Query = "SELECT Unit, Floc, SMR, DateAdded FROM EventLog " & f.Filter & " ORDER BY DateAdded DESC"
        
    Dim db As New cDB
    db.OpenConn
    db.rs.Open Query, db.conn, adOpenStatic, adLockReadOnly
    
    With db.rs
        If .RecordCount > 0 Then
            .MoveFirst ' this is the most recent
            getUnitSMRPrevCO = getUnitSMR(!Unit, !DateAdded)
            'Debug.Print PrevSMR & " | " & !Unit & " | " & !Floc & " | " & !DateAdded
            
            Else 'no previous changeouts
            If Complain = True Then MsgBox "No previous changeouts found for unit '" & Unit & " - " & Floc & "'"
            getUnitSMRPrevCO = 0
        End If
    End With
    
cleanup:
    On Error Resume Next
    db.rs.Close
    Exit Function
errHandle:
    sendErrMsg "getUnitSMRPrevCO"
    getUnitSMRPrevCO = 0
    Resume cleanup
End Function


Sub setComponentCOType(e As cEvent)
    On Error GoTo errHandle
    aUID = e.UID
    Dim tempVal As Boolean
    tempVal = e.val("Comp CO")
    
    ans = MsgBox("Woah, looks like you're trying to add a component changeout record! Please select the component type.", vbYesNo)
    
    If ans = vbYes Then
        Dim frmCOManual As New addCOManual
        Set frmCOManual.e = e
        frmCOManual.Show
        Else
        e.val("Comp CO") = tempVal
    End If
    
cleanup:
    On Error Resume Next
    Exit Sub
errHandle:
    sendErrMsg "setComponentCOType"
    Resume cleanup
End Sub

Sub tempAddFloc()
    loadDB
    aQuery = "SELECT Component, Modifier, Floc FROM EventLog WHERE ComponentCO = True"
    Set rs = db.OpenRecordset(aQuery, dbOpenDynaset)
    With rs
        Do While .EOF <> True
            '.Edit

                aFloc = getFloc(!Component, !Modifier)
                Debug.Print aFloc

            '.Update
            .MoveNext
        Loop
    End With

cleanup:
    On Error Resume Next
    cleanupDB
    Exit Sub
errHandle:
    sendErrMsg "tempAddFloc"
    Resume cleanup
End Sub
Function getFloc(Component, Optional Modifier) As String
    On Error GoTo errHandle
    If IsMissing(Modifier) Then Modifier = ""
    
    If Component Like "*,*" Then 'split "Component, LH" into component and modifier
        strTemp = Component
        posComma = InStr(1, strTemp, ",")
        Component = Left(strTemp, posComma - 1)
        Modifier = Trim(Right(strTemp, Len(strTemp) - posComma))
    End If
    
    Dim f As New cFilter
    f.add "Component=", Component
    If Modifier <> "" Then f.add "Modifier=", Modifier
    Query = "Select * From ComponentType " & f.Filter
    
    Dim db As New cDB
    db.OpenConn
    db.rs.Open Query, db.conn, adOpenStatic, adLockReadOnly
    
    With db.rs
        If .RecordCount = 1 Then getFloc = !Floc
    End With
    
cleanup:
    On Error Resume Next
    db.rs.Close
    Exit Function
errHandle:
    sendErrMsg "getFloc"
    Resume cleanup
End Function
Function convInOut(aWord)
    Select Case aWord
        Case "LH"
            convInOut = "IN"
        Case "RH"
            convInOut = "OUT"
    End Select
End Function
Sub refreshGSheet()
    With Sheet17.QueryTables(1)
        .Refresh
       'Debug.Print .Connection
       '.Connection = "URL;https://docs.google.com/spreadsheets/d/1cSV85R5fsza9-ylOGTiQ-KmVX6J_VEYE79DD7tGl5Fo/gviz/tq?tqx=out:html&tq&gid=1"
       '&tqx=out:html&tq&gid=1
    End With
End Sub
Function checkUnitExists(aUnit) As Boolean
    With rs2
        .Seek "=", aUnit
        If .NoMatch = False Then
            checkUnitExists = True
            Else
            checkUnitExists = False
        End If
    End With
End Function
Function replaceUnitZero(aUnit)
    If Mid(aUnit, 2, 1) = "0" Then aUnit = Replace(aUnit, "0", "", 1, 1)
    replaceUnitZero = aUnit
End Function


'Sub linkSuncorWO()
'    loadDB
'    Set ws = ActiveSheet
'    Set tbl = ws.ListObjects(1)
'    Set dbr = tbl.DataBodyRange
'    Set rs = db.OpenRecordset("EventLog", dbOpenTable)
'
'    For i = 12 To dbr.Rows.Count
'        aUnit = dbr.Cells(i, 1)
'        aSuncorWO = dbr.Cells(i, 2)
'        aDate = dbr.Cells(i, 3)
'        aComponent = dbr.Cells(i, 4)
'        aModifier = dbr.Cells(i, 5)
'        aRemovalReason = dbr.Cells(i, 8)
'        aSNRemoved = dbr.Cells(i, 11)
'        aSNInstalled = dbr.Cells(i, 12)
'        aWarrantyYN = parseWarranty(dbr.Cells(i, 14))
'
'        strAdd = aUnit & " | " & aDate & " | " & aComponent & ", " & aModifier
'        aQuery = "SELECT * FROM EventLog WHERE Unit ='" & aUnit & "' AND DateAdded Between #" & aDate - 10 & "# AND #" & aDate + 10 & "# AND Title <> Null "
'        Set rs3 = db.OpenRecordset(aQuery, dbOpenDynaset)
'        With rs3
'            If .RecordCount > 0 Then
'                LinkCO.ListBox1.Clear
'                Do While .EOF <> True
'                    LinkCO.ListBox1.AddItem !Unit & " | " & !DateAdded & " | " & !Title
'                    .MoveNext
'                Loop
'                LinkCO.TextBox1.Value = strAdd
'                LinkCO.Show
'
'                Else
'                Debug.Print i & " - Adding: " & strAdd
'                addEditCORecordfromGoogleSheet 'AddNew
'            End If
'        End With
'    Next i
'
'    cleanupDB
'
'End Sub
