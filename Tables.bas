Attribute VB_Name = "Tables"
Option Compare Text
Sub launchEvents()
    Events.Show
End Sub
Sub launchAddEvent()
    WriteCheck
    OpenedFromWarranty = False
    AddEvent.Show
End Sub

Sub refreshUnit()
    Dim f As New cFilter
    If getMineSite(True) = "FortHills" Then strDefault = "F"
    
    Unit = InputBox("Enter unit number:", "Unit", Default:=strDefault)
    If Len(Unit) < 2 Then Exit Sub
    f.add "EventLog.Unit=", Unit
    f.Filter2.add "FactoryCampaign.Unit=", Unit
    RefreshTable f:=f
End Sub
Sub ButtonPassover()
    Passover.Show
End Sub
Sub ButtonLoadEvents()
Attribute ButtonLoadEvents.VB_ProcData.VB_Invoke_Func = "R\n14"
    iws = getWSInt(ActiveSheet.CodeName)
    Select Case iws
        Case 1, 2
            LoadEvents.Show
        Case 7, 8
            ViewFCDetails.Show
        Case 10
            RefreshDateRange.Show
        Case 11
            uLoadUnits.Show
        Case 13, 14
            RefreshTable
        Case 15
            refreshComponentCO
        Case 16
            RefreshTable
    End Select
End Sub

Sub RefreshTable(Optional RefreshType As String, Optional aUnit, Optional iws, _
                Optional aFC, Optional DateLower, Optional DateUpper, Optional f As cFilter, Optional sOrder As String)
    'This is the main function that loads records into the EventLog, WorkOrder, FactoryCampaign(Details), and TSI tables
    On Error GoTo errHandle
    
    If IsMissing(iws) Then
        iws = getWSInt(ActiveSheet.CodeName)
        Set ws = ActiveSheet
        Else
        Set ws = getWorkSheet(iws)
    End If
    Set tbl = ws.ListObjects(1)
    Set dbr = tbl.DataBodyRange
    Dim aFilter As String
    
    Loading.Show vbModeless
    DoEvents 'allow the form to load and display its text
    
    If f Is Nothing Then Set f = New cFilter
    
    Select Case RefreshType
        Case "AllOpen"
            Select Case iws
                Case 1
                    f.add "(PassoverSort='x' OR StatusEvent<>'Complete')"
                Case 2
                    f.add "StatusWO=", "Open"
            End Select
            
        Case "Dates"
            If IsMissing(DateUpper) Then DateUpper = Now
            f.add "DateAdded BETWEEN '" & DateLower & "' AND '" & DateUpper & "' "
            
        Case "ComponentReturns"
            f.add "DateReturned>=", DateValue(Now - 7)
        Case "CO"
            f.add "ComponentCO=", "True"
    End Select
    
    Select Case iws
        Case 1 'EventLog
            
            If checkCummins Then
                f.add "EventLog.MineSite=", getMineSite
                
                Else
                If Not f.Contains("Unit") Then
                    If hasSubSite Then
                        f.add "EventLog.MineSite=", getMineSite
                        f.add getSubSiteFilter
                        Else
                        f.add "UnitID.MineSite=", getMineSite(True)
                    End If
                End If
            End If
            
            Query = "SELECT UID, PassoverSort, StatusEvent, EventLog.Unit, Title, Description, Required, DateAdded , DateCompleted, " _
                & "IssueCategory, SubCategory, Cause, CreatedBy, TimeCalled " _
                & "From  EventLog INNER JOIN UnitID ON (EventLog.Unit=UnitID.Unit) " _
                & f.Filter _
                & " ORDER BY " & sOrder & "DateAdded DESC"
            
            
'            Debug.Print Query
'            GoTo cleanup
            
            DateCol = 8
            
        Case 2 'WorkOrders
            
            If checkCummins Then
                SerialType = "EngineSerial"
                f.add "EventLog.MineSite=", getMineSite
                
                Else
                SerialType = "Serial"
                
                If Not f.Contains("Unit") Then
                    If getWarrantyOnly = "Yes" Then f.add "(WarrantyYN='Yes' OR WarrantyYN='PRP')"
                    
                    If hasSubSite Then
                        f.add "EventLog.MineSite=", getMineSite
                        f.add getSubSiteFilter
                        Else
                        f.add "UnitID.MineSite=", getMineSite(True)
                    End If
                End If
            End If
            
            f.add "StatusWO Is Not Null"
            
            
            Query = "SELECT UID, StatusWO, WarrantyYN, WorkOrder, Seg, SuncorWO, SuncorPO, EventLog.Unit, " _
                & SerialType & ", " & "Title, PartNumber, SMR, DateAdded, DateCompleted, " _
                & "CreatedBy, WOComments, ComponentCO, Downloads, Pictures, CCOS " _
                & "From EventLog INNER JOIN UnitID ON (EventLog.Unit=UnitID.Unit) " _
                & f.Filter _
                & "ORDER BY DateAdded"
'            Debug.Print Query
            'GoTo cleanup
            DateCol = 13
            
        Case 7 'FC Details
            
            Query = "SELECT t1.*  " _
                    & "FROM FCSummaryMineSite RIGHT JOIN  (" _
                    & "SELECT UnitID.MineSite, UnitID.Model, FactoryCampaign.Unit, FactoryCampaign.FCNumber, " _
                    & "IIf([EventLog].[DateCompleted] Is Null And [FactoryCampaign].[DateCompleteSMS] Is Null " _
                    & "And [FactoryCampaign].[DateCompleteKA] Is Null,'Open','Closed') AS calcStatus, " _
                    & "FCSummary.Classification, IIf([SubjectShort] Is Not Null,[SubjectShort],[FactoryCampaign].[Subject]) AS calcSubj, " _
                    & "IIf([DateCompleteSMS] Is Null,[EventLog].[DateCompleted],[DateCompleteSMS]) AS calcDate, " _
                    & "FactoryCampaign.DateCompleteKA, FCSummary.ExpiryDate, EventLog.SMR, EventLog.Pictures, FactoryCampaign.Notes " _
                    & "FROM EventLog RIGHT JOIN (FCSummary INNER JOIN (UnitID INNER JOIN FactoryCampaign ON UnitID.Unit = FactoryCampaign.Unit) " _
                    & "ON FCSummary.FCNumber = FactoryCampaign.FCNumber) " _
                    & "ON EventLog.UID = FactoryCampaign.UID " & f.Filter2.Filter & ") AS t1 " _
                    & "ON FCSummaryMineSite.MineSite=t1.MineSite AND FCSummaryMineSite.FCNumber=t1.FCNumber " _
                    & f.Filter
                
                'Need to wrap the original query with a temp table to filter 'calcStatus', because can't filter a calculated field --> the 'WHERE' clause executes before the calculation.
                If RefreshType = "AllOpenFC" Then
                    Query = "SELECT tempTbl.* From (" & Query & ") As tempTbl WHERE calcStatus='Open' ORDER BY Unit, FCNumber"
                    Else
                    Query = Query & " Order By t1.Unit, t1.FCNumber"
                End If
            DateCol = 8
            
        Case 10 'TSI
            aFilter = "WHERE UnitID.MineSite ='" & getMineSite(True) & "' And StatusTSI Is NOt NULL " & aFilter
            
            Query = "SELECT UID, StatusTSI, DateAdded, DateInfo, " _
                & "DateTSISubmission, TSINumber, WorkOrder, " _
                & " EventLog.Unit, UnitID.Model, Title, SMR, ComponentSMR, TSIPartName, PartNumber, SNRemoved, TSIDetails, TSIAuthor " _
                & "FROM EventLog INNER JOIN UnitID ON EventLog.Unit=UnitID.Unit " & aFilter & "ORDER BY DateAdded "
                
        Case 11 'Unit Info
            Query = "SELECT MineSite, Model, Serial, EngineSerial, Unit, DeliveryDate FROM UnitID " _
            & f.Filter _
            & "ORDER BY MineSite, Unit"
        
        Case 12 'Component Look Ahead
            aWeek = DatePart("ww", Now, vbMonday, vbFirstFourDays) - 1
            Query = "SELECT Week, StartDate, DueDate, DueWeek, Status, MainWC, WOType, SuncorWO, SMSWO, FLOC, Description, Category " _
                & "FROM ComponentLookAhead " & "WHERE Week >= " & aWeek & " AND (Category <> 'x' OR Category IS Null) " _
                & "ORDER BY Week, StartDate"
                    'AND WOType <> 'MPRG'
        
        Case 13 'Parts
            aModel = ws.Cells(2, 6)
            Query = "SELECT Model, PartNo, PartName FROM Parts WHERE Model='" & _
                aModel & "' ORDER BY PartName "

        Case 14 'Fault Codes
            Query = "SELECT Type, Description, Code FROM FaultCodes ORDER BY Type, Code "
            
        Case 15 'Component CO
            Select Case RefreshType
                Case "MajorComp"
                    aFilter = " AND ComponentType.Major='True' "
                Case "SpecificComp"
                    
            End Select
                    
            Query = "SELECT UID, EventLog.Unit, ComponentType.Component, ComponentType.Modifier, " _
                & "GroupCO, DateAdded, SMR, ComponentSMR, SNRemoved, SNInstalled, WarrantyYN, " _
                & "CapUSD, WorkOrder, SuncorWO, SuncorPO, RemovalReason " _
                & "FROM (EventLog INNER JOIN ComponentType ON EventLog.Floc=ComponentType.Floc) LEFT JOIN UnitID ON EventLog.Unit=UnitID.Unit " _
                & f.Filter _
                & "ORDER BY EventLog.Unit, DateAdded, ComponentType.Modifier, GroupCO"
            
        Case 16
            dbr.Cells(1, 1).Resize(2, dbr.Columns.Count).FillDown 'this keeps the formulas in the last columns from being blank. adds ~1s, messy, should find a better way
            
            Query = " SELECT t3.MineSite, t3.Model, t3.Unit, t3.Component, t3.Modifier, t3.BenchSMR, t3.CurrentUnitSMR, t2.LastCO " _
                    & "FROM (SELECT UnitID.MineSite, UnitID.Model, UnitID.Unit, ComponentType.Component, ComponentType.Modifier, ComponentType.Floc, " _
                        & "ComponentType.BenchSMR, t1.CurrentUnitSMR " _
                        & "FROM ComponentType, (SELECT UnitID.Unit, (DateDiff(day, CURRENT_TIMESTAMP, Max(UnitSMR.DateSMR))*20)+Max(UnitSMR.SMR) AS CurrentUnitSMR FROM UnitID " _
                            & "LEFT JOIN UnitSMR ON UnitID.Unit = UnitSMR.Unit GROUP BY UnitID.Unit)  AS t1 " _
                            & "INNER JOIN UnitID ON t1.Unit = UnitID.Unit " _
                        & "WHERE (((UnitID.Model) Like '%980E%') AND ((UnitID.MineSite)='FortHills') )) as t3 " _
                        & "LEFT JOIN (SELECT EventLog.Unit, EventLog.Floc, Max(EventLog.SMR) AS LastCO FROM EventLog " _
                        & "WHERE ComponentCO='True' GROUP BY EventLog.Unit, EventLog.Floc) " _
                    & "AS t2 ON t2.Floc = t3.Floc AND t2.Unit = t3.Unit " _
                    & "ORDER BY t3.Unit, t3.Floc"
                    
        Case Else
            Err.Raise 420, "No table to refresh."
    End Select
    
    Dim db As New cDB
    With db
        .OpenConn
         .rs.Open Query, db.conn, adOpenStatic, adLockReadOnly
        '.printRs
        .loadToTable tbl
    End With

    'Set table number formats > could set the formats IN the query
    If iws = 1 Then
        Autofit_Height
        tbl.ListColumns(14).DataBodyRange.NumberFormat = _
            "dd-mmm hh:mm AM/PM"
    End If
    If iws = 1 Or iws = 2 Or iws = 7 Then
        tbl.ListColumns(DateCol).DataBodyRange.NumberFormat = getDateFormat
        tbl.ListColumns(DateCol + 1).DataBodyRange.NumberFormat = getDateFormat
    End If
    If iws = 12 Then
        tbl.ListColumns(2).DataBodyRange.NumberFormat = getDateFormat
        tbl.ListColumns(3).DataBodyRange.NumberFormat = getDateFormat
    End If
    If iws = 1 Or iws = 2 Then
        tbl.ListColumns(1).DataBodyRange.NumberFormat = "0"
    End If
    DoEvents
    
cleanup:
    On Error Resume Next
    Loading.Hide
    db.rs.Close
    Application.ScreenUpdating = True
    Application.EnableEvents = True
    Select Case iws
        Case 10
            getWorkSheet(iws).Activate
            dbr.Cells(tbl.Range.Rows.Count - 1, 7).Activate
        Case Else
            dbr.Cells(1, 2).Activate
    End Select
    Exit Sub
errHandle:
    sendErrMsg "RefreshTable | iws: " & iws
    Resume cleanup
End Sub

Sub DeleteRecords()
    On Error GoTo errHandle
    WriteCheck
    Application.ScreenUpdating = False
    iws = getWSInt(ActiveSheet.CodeName)
    
    Dim sRange As Range
    Set sRange = Application.Selection
    Dim e As cEvent
    Dim collEvents As New Collection

    For Each Target In sRange 'Colour cells & add to collection
        Set e = createEventTable(Target)
        e.colourLine "Orange"
        collEvents.add e
    Next
    sCount = collEvents.Count
    
    Application.ScreenUpdating = True
    If sCount > 1 Then sss = "s"
    Select Case iws
        Case 1, 2
            aMessage = "Are you sure you want to delete " & sCount & " row" & sss & " from the database?" & dLine & "This will permanently delete BOTH event and work order."
        Case 10
            aMessage = "Are you sure you want to delete " & sCount & " TSI" & sss & " from the database?" _
                    & dLine & "If the TSI is linked to an Event this will only clear the TSI."
    End Select
    
    answer = MsgBox(aMessage, vbYesNo + vbQuestion, "Delete Events")

    For Each e In collEvents 'Set back to no colour
        e.colourLine "None"
    Next
    Application.ScreenUpdating = False

    If answer = vbYes Then
        Application.EnableEvents = False

        For Each e In collEvents
            With e
                .deletefromTable iws
                
                Select Case iws
                    Case 1, 2
                        If iws = 1 Then ' delete from opposite table too
                            .deletefromTable 2
                            Else
                            .deletefromTable 1
                        End If
                        .deletefromDB
                        
                    Case 10 'TSI
                        With .rsEvent
                            If !StatusEvent = Null And !StatusWO = Null Then
                                .Close
                                e.deletefromDB 'tsi not linked to event, delete entire row
                                Else
                                !StatusTSI = Null 'just set to null
                                .Update
                                .Close
                            End If
                        End With
                End Select
            End With
        Next
        
        Set e = collEvents.Item(1)
        With e.tbl.DataBodyRange
            .Cells(.Rows.Count, 2).Activate
        End With
    End If

cleanup:
    On Error Resume Next
    TearDownRecords
    Application.EnableEvents = True
    Exit Sub
errHandle:
    sendErrMsg "Uh oh, something went wrong! Not able to delete record in Access Database. | deleteRecords"
    Resume cleanup
End Sub

Sub updateRecord(Target As Range)
    On Error GoTo errHandle
    Application.EnableEvents = False
    Dim e As cEvent
    Set e = createEventTable(Target, Complain:=True)
    
    Select Case e.ActiveColName
        Case "Status"
            Select Case Target.value
                Case "Complete" 'Auto close non warranty WOs on Event close
                    If e.rsEvent!WarrantyYN = "No" Then e.rsEvent!StatusWO = "Closed"
                    
                Case "Closed"
                    If e.val("Date Closed") = "" Then
                        With e.rsEvent
                            !DateCompleted = DateValue(Now)
                            .Update
                        End With
                        e.val("Date Closed") = DateValue(Now)
                    End If
                    e.CloseEvent
                    e.TearDown 'kill prsEvent... pretty sketch
                    
                Case "Cancelled"
                    If e.hasFC Then e.unlinkFC True
            End Select
            
        Case "Title"
            If getMineSite(True) <> "BaseMine" Then renameEventFolder e:=e
        
        Case "Comp CO"
            If Target.value = True Then setComponentCOType e
        
        Case "Subject"
            renameFCSubject e
            
    End Select
    
    If e.isInit And Not e.colRestricted Then e.updateValue
    
cleanup:
    On Error Resume Next
    Application.EnableEvents = True
    Exit Sub
errHandle:
    sendErrMsg "Tables.UpdateRecord"
    Resume cleanup
End Sub

Sub JumpSelectedEvent()

    On Error GoTo errHandle
    iws = ActiveSheet.Index
    
    Dim tbl2 As ListObject
    Set tbl = Sheets(iws).ListObjects(1)
    Set dbr = tbl.DataBodyRange
    hRow = tbl.HeaderRowRange.row
    
    IntersectCheck dbr
    
    Set Target = ActiveCell
    aUID = dbr.Cells(Target.row - hRow, 1)

    If iws = 1 Then
        iws2 = 2
        Else
        iws2 = 1
    End If
    Set tbl2 = Sheets(iws2).ListObjects(1)
    Set dRow2 = tbl2.ListColumns(1).Range.find(aUID)
    
    If dRow2 Is Nothing Then
        MsgBox "Can't find selected event in opposite table, ensure correct rows are loaded from the database.", vbExclamation
        GoTo cleanup
    End If
    
    Sheets(iws2).Activate
    tbl2.DataBodyRange.Cells(dRow2.row - tbl2.HeaderRowRange.row, 2).Activate
    
cleanup:
    Application.EnableEvents = True
    Exit Sub
errHandle:
    MsgBox "Uh oh, something went wrong! Not sure what though, to be honest." & dLine _
            & "Error " & Str(Err.Number) & ": " & Chr(13) & Err.Description, vbExclamation, "Error"
    Resume cleanup
End Sub




