VERSION 1.0 CLASS
BEGIN
  MultiUse = -1  'True
END
Attribute VB_Name = "cEvent"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = False
Attribute VB_PredeclaredId = False
Attribute VB_Exposed = False
Private pWs As Worksheet
Private pTbl As ListObject
Private Table As cTbl
Private pDbr As Range
Private pCell As Range
Private pIws As Integer
Private i As Long

Private prsEvent As ADODB.Recordset
Private prsSerial As ADODB.Recordset
Private prsFC As ADODB.Recordset
Private prsFCSummary As ADODB.Recordset
Private pDB As cDB
Private pEF As cEventFolder
Private pIsInit As Boolean

Private pUID As Double
Private pUnit As String
Private pFCNumber As String
Private pDateEvent As Date
Private pExpiryDate As Date
Private pTitle As String
Private pDescription As String
Private pSerial As String
Private pModel As String
Private pMineSite As String

Public StatusEvent As String
Public StatusWO As String
Public WorkOrder As String
Public Component As String
Public Modifier As String
Public Floc As String
Public UnitSMR As Long
Public PartSMR As Long
Public PartName  As String
Public PartNo As String
Public PartSerial  As String
Public User As String
Public ComponentCO As Boolean

Public Sub initNew()
    pUID = createUID
    pMineSite = getMineSite
    Me.StatusEvent = "Work in Progress"
    Me.StatusWO = "Open"
    pIsInit = True
End Sub
Public Sub initTable(iws, Target As Range, Optional Complain As Boolean = True) 'init from table
    On Error GoTo errHandle
    setTblVars iws
    Set pCell = Target
    
    If Not IntersectCheck(pDbr, pCell, Complain) Then GoTo cleanup
    i = getActiveRow(pTbl, pCell)
    
    With pDbr
        Select Case iws
            Case 1
                pUID = val("UID")
                pDateEvent = val("Date Added")
                pUnit = val("Unit")
                pTitle = Trim(val("Title"))
            Case 2
                pUID = val("UID")
                pDateEvent = val("Date Opened")
                pUnit = val("Unit")
                pTitle = Trim(val("Title"))
                PartNo = val("Part Number")
                WorkOrder = val("Work Order")
                
            Case 7 'FC Details
                pUnit = val("Unit")
                pFCNumber = val("FC Number")
                setUIDfromFC
                
            Case 8 'fc summary
                pFCNumber = .Cells(i, getCol(iws, "FCNumber"))
                
            Case 15 'componentCO
                pUID = .Cells(i, 1)
                pUnit = val("Unit")
                Component = val("Component")
                Modifier = val("Side")
                pDateEvent = val("CO Date")
                WorkOrder = val("SMS WO")
                
            Case 10 'TSI
                pUID = .Cells(i, 1)
                pDateEvent = val("Failure Date")
                WorkOrder = .Cells(i, getCol(iws, "WorkOrder"))
                pUnit = .Cells(i, getCol(iws, "Unit"))
                pModel = .Cells(i, 9)
                pTitle = .Cells(i, getCol(iws, "Title"))
                UnitSMR = .Cells(i, getCol(iws, "UnitSMR"))
                PartSMR = .Cells(i, getCol(iws, "PartSMR"))
                PartName = .Cells(i, 13)
                PartNo = .Cells(i, getCol(iws, "PartNo"))
                PartSerial = .Cells(i, 15)
                User = .Cells(i, 17)

        End Select
    End With
    
    pIsInit = True
    
cleanup:
    Exit Sub
errHandle:
    sendErrMsg "Event.Init"
    Resume cleanup
End Sub
Public Sub addToTable(iws As Integer)
    On Error GoTo errHandle
    setTblVars iws
    pTbl.ListRows.add
    LastRow = pTbl.ListRows.Count
    
    With pDbr
        Select Case iws
            Case 1
                .Cells(LastRow, 1) = pUID
                .Cells(LastRow, 2) = "x"
                .Cells(LastRow, 3) = StatusEvent
                .Cells(LastRow, getCol(iws, "Unit")) = pUnit
                .Cells(LastRow, getCol(iws, "Title")) = pTitle
                .Cells(LastRow, 6) = Format(pDateEvent, "Mmm dd yyyy") & " - "
                .Cells(LastRow, getCol(iws, "DateAdded")) = pDateEvent
                .Cells(LastRow, 13) = Application.UserName
            Case 2
                .Cells(LastRow, 1) = pUID
                .Cells(LastRow, 2) = StatusWO
                .Cells(LastRow, 3) = aWarrantyType
                .Cells(LastRow, 5) = "1" 'seg
                .Cells(LastRow, getCol(iws, "Unit")) = pUnit
                .Cells(LastRow, 9) = UnitSerial
                .Cells(LastRow, getCol(iws, "Title")) = pTitle
                If UnitSMR > 0 Then .Cells(LastRow, getCol(iws, "UnitSMR")) = UnitSMR
                .Cells(LastRow, getCol(iws, "DateAdded")) = pDateEvent
                .Cells(LastRow, 15) = Application.UserName
                .Cells(LastRow, 17) = ComponentCO
                .Cells(LastRow, 18) = False
                .Cells(LastRow, 19) = 0
        End Select
    End With
    
    'Probably doesn't work with enableevents off
    'pDbr.Cells(LastRow, Table.getHeaderCol("Title")).Select
    
cleanup:
    Exit Sub
errHandle:
    sendErrMsg "cEvent.addToTable"
    Resume cleanup
End Sub
Public Sub updateValue()
    On Error GoTo errHandle
    sField = Field(pIws, Table.getHeaderStr(pCell))
    Dim f As New cFilter
    
    Select Case pIws
        Case 7
            sCols = "Unit, " & sField
            sTable = "FactoryCampaign"
            f.add "Unit=", pUnit
            f.add "FCNumber=", pFCNumber
        
        Case 8 'FC Summary
            sCols = "FCSummary.FCNumber, " & sField
            
            sTable = "FCSummary LEFT JOIN FCSummaryMineSite " _
                    & "ON FCSummary.FCNumber=FCSummaryMineSite.FCNumber"
                    
            f.add "FCSummary.FCNumber=", pFCNumber
            f.add "MineSite=", getMineSite(True)
            
        Case Else
            sCols = sField
            sTable = "EventLog"
            f.add "UID=", pUID
    End Select
    
    Query = "Select " & sCols & " From " & sTable & f.Filter
    'Debug.Print Query
    
    Dim db As New cDB
    db.OpenConn
    db.rs.Open Query, db.conn, adOpenStatic, adLockOptimistic
    
    With db.rs
        .Fields(sField) = updateValCheck(pCell.value)
        .Update
        .Close
    End With
    
cleanup:
    On Error Resume Next
    Application.EnableEvents = True
    Exit Sub
errHandle:
    sendErrMsg "cEvent.updateValue | Query ='" & Query & "'"
    Resume cleanup
End Sub
Private Function updateValCheck(val As Variant) As Variant
    If val = "" Then
        updateValCheck = Null
        Else
        updateValCheck = val
    End If
End Function
    
Public Sub updateRecord() 'Not sure if need this
    On Error GoTo errHandle
    Dim db As New cDB
    db.OpenConn True
    
    db.rs.Open getUIDQuery(pUID), db.conn, adOpenStatic, adLockOptimistic
    
    With db.rs
        Select Case pIws
            Case 1
                !PassoverSort = val("Passover")
                !StatusEvent = val("Status")
                If val("Status") = "Complete" And !WarrantyYN = "No" Then !StatusWO = "Closed" 'Auto close non warranty WOs on Event close
                !Unit = val("Unit")
                If getMineSite = "BaseMine" Then !Title = val("Title")
                !Description = val("Description")
                !Required = val("Required")
                !DateAdded = val("Date Added")
                !DateCompleted = val("Date Complete")
                !IssueCategory = val("Issue")
                !SubCategory = val("Sub Category")
                !Cause = val("Cause")
                !CreatedBy = val("Added By")
                !TimeCalled = val("Time Called to Event")
                .Update
        End Select
        
        .Close
    End With
    
cleanup:
    On Error Resume Next
    Exit Sub
errHandle:
    sendErrMsg "cEvent.updateRecord"
    Resume cleanup
End Sub
Public Property Get colRestricted() As Boolean
    
    On Error GoTo errHandle
    Select Case pIws
        Case 1
            Exit Property
        Case 2
            arrRestrict = Array("Serial", "DLS", "Pics", "CCOS")
        Case 7
            arrRestrict = Array("Mine Site", "Model", "Unit", "FC Number", "Status", "Type", "Subject", "Date Complete KA", "Expiry Date", "SMR", "Pics")
        Case 8
            arrRestrict = Array("FC Number", "Type", "Prog", "Prog %")
            If Table.ColNum(pCell) > 10 Then colRestricted = True
        Case 10
            arrRestrict = Array("Model")
        Case 15
            arrRestrict = Array("Unit", "Component", "Side")
    End Select
    
    Dim sField As String
    sField = Table.getHeaderStr(pCell)
    If IsInArray(sField, arrRestrict) Then colRestricted = True
    
cleanup:
    On Error Resume Next
    Exit Property
errHandle:
    sendErrMsg "cEvent.colRestricted"
    Resume cleanup
End Property
Public Property Get ActiveColName() As String
    ActiveColName = Table.getHeaderStr(pCell)
End Property
Public Property Get ActiveColNum() As Long
    ActiveColNum = Table.getHeaderCol(ActiveColName)
End Property
Public Property Get Cell() As Range
    Set Cell = pCell
End Property

Public Sub CloseEvent()
    On Error GoTo errHandle
    
    Set pEF = createFolder(Me)
    If pEF.NumPics < 1 Then
        ans = MsgBox("No pics added to event folder. Are you sure you would like to close event?", vbYesNo + vbQuestion)
        If ans <> vbYes Then
            Me.val("Status") = "Open"
            Exit Sub
        End If
    End If
    
cleanup:
    On Error Resume Next
    pEF.TearDown
    Exit Sub
errHandle:
    sendErrMsg "cEvent.CloseEvent"
    Resume cleanup
End Sub

Public Sub deletefromDB()
    If Me.hasFC Then
        ans = MsgBox("Event '" & pTitle & "' is linked to FC '" & pFCNumber _
                & "', would you like to unlink it then delete?", vbYesNo + vbQuestion)
        If ans = vbYes Then
            Me.unlinkFC True
            Else
            Exit Sub
        End If
    End If
    
    setRsEvent
    With prsEvent
        .Delete
        .Close
    End With
End Sub
Public Sub deletefromTable(iws As Integer)
    If iws <> getWSInt(pWs.CodeName) Then
        Set Table = New cTbl
        Table.init ws:=getWorkSheet(iws)
    End If
    If pUID <> 0 Then i = Table.getIndex(pUID, "UID")
    If i = 0 Then Exit Sub ' Err.Raise 444, , "Can't find UID in table."
'    Debug.Print i, Table.tbl.Range.Worksheet.CodeName, pTitle
    ClearFilter Table.tbl
    Table.tbl.ListRows(i).Delete
End Sub
Private Sub setUIDfromFC()
    On Error GoTo errHandle
    Dim rsFC As ADODB.Recordset
    Query = "Select UID From FactoryCampaign Where FCNumber ='" & pFCNumber & "' And Unit ='" & pUnit & "' "
    
    Dim db As New cDB
    db.OpenConn
    db.rs.Open Query, db.conn, adOpenStatic, adLockReadOnly
    
    Set rsFC = db.rs
    With rsFC
        If .RecordCount = 1 And Not IsNull(!UID) Then
            pUID = !UID
            Else
            pIsInit = False
        End If
    End With
    rsFC.Close
    
cleanup:
    On Error Resume Next
    Exit Sub
errHandle:
    sendErrMsg "setUIDfromFC"
    Resume cleanup
End Sub
Public Property Get rsEvent() As ADODB.Recordset
    setRsEvent
    Debug.Assert Not prsEvent Is Nothing
    Set rsEvent = prsEvent
End Property
Private Sub setRsEvent()
    On Error GoTo errHandle
    If pUID = 0 Then Exit Sub
    
    If prsEvent Is Nothing Then
        Dim db As New cDB
        db.OpenConn
        db.rs.Open getUIDQuery(pUID), db.conn, adOpenStatic, adLockOptimistic
        Set prsEvent = db.rs
    End If
    
cleanup:
    On Error Resume Next
    Exit Sub
errHandle:
    sendErrMsg "cEvent.setRsEvent"
    Resume cleanup
End Sub
Private Sub setRsSerial() 'actually setting unit values?
    On Error GoTo errHandle
    Query = "Select * From UnitID Where Unit='" & pUnit & "'"
    Dim db As New cDB
    db.OpenConn
    db.rs.Open Query, db.conn, adOpenStatic, adLockReadOnly
    
    Set prsSerial = db.rs
    With prsSerial
        If .RecordCount = 1 Then
            pMineSite = !MineSite
            pSerial = !Serial
            pModel = !Model
        End If
    End With
    
cleanup:
    On Error Resume Next
    db.rs.Close
    Exit Sub
errHandle:
    sendErrMsg "setRsSerial"
    Resume cleanup
End Sub
Public Property Get rsFC(Optional UIDQuery As Boolean = True, _
                        Optional MS As Boolean = False, _
                        Optional Summary As Boolean = False) As ADODB.Recordset
    setRsFC UIDQuery, MS, Summary
    Set rsFC = prsFC
End Property
Private Sub setRsFC(Optional UIDQuery As Boolean = True, _
                    Optional MS As Boolean = False, _
                    Optional Summary As Boolean = False)
    On Error GoTo errHandle
    Dim Query As String
    Dim Filter As String
    Dim dbTable As String
    Dim f As New cFilter
    
    dbTable = "FactoryCampaign"
    
    If MS Then dbTable = "FCSummaryMineSite Right Join " & dbTable & " On FCSummaryMineSite.FCNumber=FactoryCampaign.FCNumber "
    If Summary Then dbTable = "FCSummary Right Join (" & dbTable & ") On FCSummary.FCNumber=FactoryCampaign.FCNumber "
    
    
    If UIDQuery Then
        If pUID = 0 Then Err.Raise 222, , "UID not set. FC not linked to Event."
        f.add "UID=", pUID
        Else
        f.add "Unit=", pUnit
        f.add "FactoryCampaign.FCNumber=", pFCNumber
        If MS Then f.add "(FCSummaryMineSite.MineSite='" & MineSite & "' OR FCSummaryMineSite.MineSite Is Null)"
    End If
    
    Query = "Select * From " & dbTable & f.Filter
    'Debug.Print Query
    
    If prsFC Is Nothing Then
        Dim db As New cDB
        db.OpenConn
        db.rs.Open Query, db.conn, adOpenStatic, adLockOptimistic
        Set prsFC = db.rs
    End If
    
cleanup:
    Exit Sub
errHandle:
    sendErrMsg "cEvent.setRsFC"
    Resume cleanup
End Sub
Public Property Get rsFCSummary(Optional MS As Boolean = False) As DAO.Recordset
     setRsFCSummary MS
     Set rsFCSummary = prsFCSummary
End Property
Private Sub setRsFCSummary(Optional MS As Boolean = False)
    On Error GoTo errHandle
    Dim Query As String
    Dim Filter As String
    Dim f As New cFilter
    
    f.add "FCSummary.FCNumber=", pFCNumber
    
    If Not MS Then
        Query = "Select * From FCSummary " & f.Filter
        Else
        f.add "FCSummaryMineSite.MineSite=", getMineSite(True)
        Query = "Select * From FCSummary Left Join FCSummaryMineSite on FCSummaryMineSite.FCNumber = FCSummary.FCNumber " & f.Filter
    End If
    
    If prsFCSummary Is Nothing Then
        Dim db As New cDB
        db.OpenConn
        db.rs.Open Query, db.conn, adOpenKeyset, adLockOptimistic
        Set prsFCSummary = db.rs
    End If
    
cleanup:
    Exit Sub
errHandle:
    sendErrMsg "cEvent.setRsFC"
    Resume cleanup
End Sub
Public Function isFCExpired() As Boolean
    On Error GoTo errHandle
    setRsFCSummary
    Debug.Assert Not prsFCSummary Is Nothing
    With prsFCSummary
        pExpiryDate = !ExpiryDate
        If pExpiryDate < DateValue(Now) Then
            isFCExpired = True
            Else
            isFCExpired = False
        End If
        .Close
    End With
    Set prsFCSummary = Nothing
    
cleanup:
    On Error Resume Next
    Exit Function
errHandle:
    sendErrMsg "cEvent.isFCExpired"
    Resume cleanup
End Function
Public Sub msgFCExpired()
    If isFCExpired Then MsgBox "FC " & FCNumber & " expired on " & pExpiryDate & dLine & "Please ensure the warranty/reliability groups are informed.", vbCritical, "FC EXPIRED!"
End Sub
Public Function hasFC() As Boolean
    setRsFC
    With prsFC
        If .RecordCount = 1 Then
            pFCNumber = !FCNumber
            hasFC = True
            Else
            hasFC = False
        End If
    End With
End Function
Public Sub unlinkFC(Optional msgConfirmation As Boolean = False) ' Un-Links FC in FactoryCampaign with the Event
    setRsFC
    With prsFC
        pFCNumber = !FCNumber
        !UID = Null
        !DateCompleteSMS = Null
        .Update
        .Close
    End With
    
    If msgConfirmation Then MsgBox "FC '" & pFCNumber & "' cancelled and unlinked from: " & pUnit & " | " & pTitle
End Sub
Property Get UID() As Double
    UID = pUID
End Property
Property Let UID(dUID As Double)
    pUID = dUID
End Property
Property Get FCNumber() As String
    FCNumber = pFCNumber
End Property
Property Let FCNumber(strFCNumber As String)
    pFCNumber = strFCNumber
End Property
Property Get Unit() As String
    Unit = pUnit
End Property
Property Let Unit(strUnit As String)
    pUnit = strUnit
End Property
Property Get Title() As String
    Title = pTitle
End Property
Property Let Title(strTitle As String)
    pTitle = strTitle
End Property
Property Get DateEvent() As Date
    DateEvent = pDateEvent
End Property
Property Let DateEvent(dDateEvent As Date)
    pDateEvent = dDateEvent
End Property
Public Property Get isInit() As Boolean
    isInit = pIsInit
End Property
Public Property Get Description() As String
    On Error GoTo errHandle
    If pDescription = "" Then
        setRsEvent
        With prsEvent
            If .RecordCount = 1 And Len(!Description) > 0 Then
                pDescription = !Description
                Else
                pDescription = "No description in event log"
            End If
        End With
    End If
    
    Description = pDescription
    
cleanup:
    Exit Property
errHandle:
    sendErrMsg "cEvent.Description"
    Resume cleanup
End Property
Public Property Get UnitSerial() As String
    If pSerial = "" Then setRsSerial
    UnitSerial = pSerial
End Property
Public Property Get Model() As String
    If pModel = "" Then setRsSerial
    Model = pModel
End Property
Public Property Get MineSite() As String
    If pMineSite = "" Then setRsSerial
    MineSite = pMineSite
End Property
Public Sub colourLine(Colour As String)
    Dim c As Long
    Select Case Colour
        Case "Orange"
            c = RGB(253, 106, 60)
        Case "Yellow"
            c = RGB(255, 255, 100)
        Case "None"
            c = xlNone
    End Select
    
    pTbl.ListRows(i).Range.Interior.Color = c
End Sub
Public Property Get tbl() As ListObject
    If Not pTbl Is Nothing Then Set tbl = pTbl
End Property
Public Property Get val(col As Variant) As Variant
    On Error GoTo errHandle
    If Table Is Nothing Then Exit Property
    If VarType(col) = vbString Then col = Table.getHeaderCol(CStr(col))
    If col = 0 Then Exit Property
    val = pDbr.Cells(i, col)
    
cleanup:
    On Error Resume Next
    Exit Property
errHandle:
    sendErrMsg "val"
    Resume cleanup
End Property
Public Property Let val(col As Variant, value As Variant)
    On Error GoTo errHandle
    If Table Is Nothing Then Exit Property
    If VarType(col) = vbString Then col = Table.getHeaderCol(CStr(col))
    If col = 0 Or i < 1 Then Exit Property
    Application.EnableEvents = False
    pDbr.Cells(i, col).value = value
cleanup:
    On Error Resume Next
    Application.EnableEvents = True
    Exit Property
errHandle:
    sendErrMsg "cEvent.Let.val"
    Resume cleanup
End Property
Private Sub setTblVars(iws)
    Set pWs = getWorkSheet(iws)
    Set pTbl = pWs.ListObjects(1)
    Set pDbr = pTbl.DataBodyRange
    Set Table = New cTbl
    pIws = iws
    Table.init ws:=pWs
End Sub
Public Property Get iws() As Integer
    iws = pIws
End Property
Public Sub PrintVars()
    Debug.Print "UID", pUID
    Debug.Print "WorkOrder", WorkOrder
    Debug.Print "Unit", pUnit
    Debug.Print "DateEvent", pDateEvent
    Debug.Print "Title", pTitle
    Debug.Print "Component", Component
    Debug.Print "Modifier", Modifier
    Debug.Print "Floc", Floc
    Debug.Print "FCNumber", pFCNumber
    Debug.Print "Model", pModel
    Debug.Print "UnitSMR", UnitSMR
    Debug.Print "PartSMR", PartSMR
    Debug.Print "PartName", PartName
    Debug.Print "PartNo", PartNo
    Debug.Print "PartSerial", PartSerial
    Debug.Print "User", User
    Debug.Print "MineSite", MineSite
    Debug.Print "Model", Model
    Debug.Print "UnitSerial", UnitSerial
End Sub
Private Sub class_initialize()
'    pIsInit = True
End Sub

Public Sub TearDown() 'A bit messy, would be better in a collection
    On Error Resume Next
    prsEvent.Close
    prsSerial.Close
    prsFC.Close
    prsFCSummary.Close
    
End Sub
