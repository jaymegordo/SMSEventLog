VERSION 5.00
Begin {C62A69F0-16DC-11CE-9E98-00AA00574A4F} AddEvent 
   Caption         =   "Add Event"
   ClientHeight    =   7530
   ClientLeft      =   6
   ClientTop       =   276
   ClientWidth     =   5076
   OleObjectBlob   =   "AddEvent.frx":0000
   StartUpPosition =   1  'CenterOwner
End
Attribute VB_Name = "AddEvent"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = False
Attribute VB_PredeclaredId = True
Attribute VB_Exposed = False
Private StopOkay As Boolean
Private pEvent As cEvent
Private pEvent2 As cEvent
Private rsCO As ADODB.Recordset

Private Sub Add_Event_Click()
    On Error GoTo errHandle
    Application.ScreenUpdating = False
    
    StopOkay = False 'Hmmmm this doesn't work so well
    checkUnit
    checkSMR
    checkDate
    checkTitle
    If StopOkay Then Exit Sub

    aWarrantyType = ComboBox_Warranty.value
    
    Me.Hide
    Application.EnableEvents = False
    
    'Add new event to Access database first
    
    Query = "EventLog"
    Dim db As New cDB
    db.OpenConn
    
    db.rs.Open Query, db.conn, adOpenKeyset, adLockOptimistic
    With db.rs
        .AddNew
        !UID = pEvent.UID
        !MineSite = pEvent.MineSite
        !PassoverSort = "x"
        !CreatedBy = Application.UserName
        !StatusWO = pEvent.StatusWO
        !WarrantyYN = aWarrantyType
        !StatusEvent = pEvent.StatusEvent
        !Seg = "1"
        !Unit = pEvent.Unit
        !Title = pEvent.Title
        If pEvent.UnitSMR > 0 Then !SMR = pEvent.UnitSMR
        !DateAdded = pEvent.DateEvent
        If checkCummins Then !IssueCategory = "Engine"

        If CheckBox_CO.value Then
            pEvent.ComponentCO = True
            pEvent.PartSMR = TextBox_ComponentSMR.value
            !ComponentCO = pEvent.ComponentCO
            !Floc = getFloc(ComboBox_CO.value) ' this will split the string into component & modifier
            If IsNumeric(pEvent.PartSMR) Then !ComponentSMR = pEvent.PartSMR
            If CheckBox_CO2.value Then !GroupCO = True
        End If
        
        .Update
        
        If CheckBox_CO2.value Then 'add second event for group CO
            Set pEvent2 = New cEvent
            With pEvent2
                .initNew
                .Unit = pEvent.Unit
                .DateEvent = pEvent.DateEvent
                .Component = ComboBox_CO2.value
                .Title = .Component & " - CO"
                .ComponentCO = True
                .UnitSMR = pEvent.UnitSMR
                .PartSMR = TextBox_ComponentSMR2.value
            End With
            
            .AddNew
            !UID = pEvent2.UID
            !MineSite = pEvent2.MineSite
            !Unit = pEvent2.Unit
            !Title = pEvent2.Title
            !DateAdded = pEvent2.DateEvent
            !StatusEvent = pEvent2.StatusEvent
            !StatusWO = pEvent2.StatusWO
            !SMR = pEvent2.UnitSMR
            !ComponentCO = pEvent2.ComponentCO
            !Floc = getFloc(pEvent2.Component)
            !GroupCO = True
            If IsNumeric(pEvent2.PartSMR) Then !ComponentSMR = pEvent2.PartSMR
            .Update
        End If
    End With
    
    'Link UID to FC Table
    If CheckBox_FC.value Then
        With pEvent.rsFC(False)
            If .RecordCount <> 1 Then
                MsgBox "FC record not linked to event UID." & dLine & "Check the FC summary tab to make sure this FC applies to selected unit. " _
                        & "THIS IS IMPORTANT - Let Jayme know." & dLine _
                        & "Unit: " & pEvent.Unit & Line & "FC: " & pEvent.FCNumber & "Recordcount: " & .RecordCount
                GoTo Skip_rs2
            End If
            !UID = pEvent.UID
            .Update
Skip_rs2:
            .Close
        End With
    End If
    
    pEvent.addToTable 1
    pEvent.addToTable 2
    
    If Not pEvent2 Is Nothing Then
        pEvent2.addToTable 1
        pEvent2.addToTable 2
    End If
    
    'Create event folder when new event is added
    If CheckBox_EventFolder.value Then
        Select Case getMineSite
            Case "BaseMine" 'dont do anything
            Case Else
                Dim EventFolder As New cEventFolder
                With EventFolder
                    .init e:=pEvent
                    .CreateEventFolder True
                End With
        End Select
    End If
    
    Application.ScreenUpdating = True
    iws = getWSInt(ActiveSheet.CodeName)
    Sheets(iws).ListObjects(1).DataBodyRange.Cells(Sheets(iws).ListObjects(1).DataBodyRange.Rows.Count, 2).Activate
    
cleanup:
    On Error Resume Next
    If Not db.rs Is Nothing Then db.rs.Close
    If Not rsCO Is Nothing Then rsCO.Close
    Application.EnableEvents = True
    Unload Me
    Exit Sub
errHandle:
    ErrMsg = "Uh oh, something went wrong! Not able to add record."
    sendErrMsg ErrMsg & " | addEvent"
    Resume cleanup
End Sub

Private Sub CheckBox_CO_Click()
    Query = "SELECT Component, Modifier FROM ComponentType ORDER BY Component"
    Dim db As New cDB
    db.OpenConn
    db.rs.Open Query, db.conn, adOpenStatic, adLockReadOnly
    
    Set rsCO = db.rs
    With rsCO
        Do While .EOF <> True
            If !Modifier <> "" Then
                ComboBox_CO.AddItem !Component & ", " & !Modifier
                Else
                ComboBox_CO.AddItem !Component
            End If
            .MoveNext
        Loop
    End With
    
    TextBox_ComponentSMR.Enabled = True
    CommandButton_getSMR.Enabled = True
    ComboBox_CO.Enabled = True
    CheckBox_CO2.Enabled = True
    
End Sub
Private Sub CheckBox_CO2_Click()
    
    With rsCO ' Duplicate code from Checkbox_CO but whatever
        .MoveFirst
        Do While .EOF <> True
            If !Modifier <> "" Then
                ComboBox_CO2.AddItem !Component & ", " & !Modifier
                Else
                ComboBox_CO2.AddItem !Component
            End If
            .MoveNext
        Loop
    End With
    ComboBox_CO2.Enabled = True
    TextBox_ComponentSMR2.Enabled = True
End Sub

Private Sub ComboBox_CO_Change()
    TextBox_Title.value = ComboBox_CO.value
End Sub
Private Sub CheckBox_FC_Click()
    On Error GoTo errHandle
    If CheckBox_FC.value = False Or tag <> "" Then Exit Sub
    
    checkUnit
    If StopOkay Then
        CheckBox_FC.value = False
        Exit Sub
    End If
    
    Dim aFCSelector As New FCSelector
    aFCSelector.init pEvent
    aFCSelector.Show
    
cleanup:
    On Error Resume Next
    cleanupDB
    Set aFCSelector = Nothing
    Exit Sub
errHandle:
    sendErrMsg "CheckBox_FC_Click"
    Resume cleanup
End Sub



Private Sub CommandButton_getSMR_Click()
    'Lookup previous component COs
    checkUnit
    checkSMR
    checkDate
    
    If CheckBox_CO.value Then TextBox_ComponentSMR = pEvent.UnitSMR - getUnitSMRPrevCO(pEvent.Unit, pEvent.DateEvent, Floc:=getFloc(ComboBox_CO.value), Complain:=True)
    If CheckBox_CO2.value Then TextBox_ComponentSMR2 = pEvent.UnitSMR - getUnitSMRPrevCO(pEvent.Unit, pEvent.DateEvent, Floc:=getFloc(ComboBox_CO2.value), Complain:=True)
    
End Sub

Private Sub UserForm_QueryClose(Cancel As Integer, CloseMode As Integer)
    If CloseMode = 0 Then Cancel_Click
End Sub
Private Sub Cancel_Click()
    Unload Me
End Sub
Private Sub userform_initialize()
    Set pEvent = New cEvent
    pEvent.initNew
    Dim ws As Worksheet
    Set ws = Worksheets("Lists")
    Dim tbl As ListObject
    Set tbl = ws.ListObjects("MineSite_Table")
    
    centerUserform Me
    iws = getWSInt(ActiveSheet.CodeName)
    TextBox_Date.value = Format(Now, getDateFormat)
    
    populateCombobox ComboBox_MineSite, tbl.ListColumns(1)
    ComboBox_MineSite.value = getMineSite
    
        If Not checkCummins Then 'SMS
            Select Case getMineSite(True)
                Case "BaseMine"
                    CheckBox_EventFolder.Enabled = False
                Case "FortHills"
                    CheckBox_EventFolder.value = True
                    TextBox_Unit = "F"
                Case "FH-TKMC", "Bighorn"
                    CheckBox_EventFolder.value = True
            End Select
            
            With ComboBox_Warranty
                .AddItem "Yes"
                .AddItem "No"
                .AddItem "PRP"
                Select Case iws
                    Case 1
                        .value = "No"
                    Case 2
                        .value = "Yes"
                End Select
            End With
            
            Else 'Cummins
            With ComboBox_Warranty
                .AddItem "WTNY"
                .AddItem "LEMS"
                .AddItem "FME"
                .value = "WTNY"
            End With
            
            CheckBox_EventFolder.Enabled = False
            CheckBox_FC.Enabled = False
        End If
    
End Sub
Private Sub checkUnit()
    With TextBox_Unit
        If .value = "" Then
            MsgBox "Please enter unit number."
            StopOkay = True
            Else
            pEvent.Unit = .value
        End If
    End With
End Sub
Private Sub checkSMR()
    With TextBox_SMR
        If .value <> "" And IsNumeric(.value) = False Then
            MsgBox "SMR must be numeric."
            .value = ""
            .SetFocus
            StopOkay = True
            ElseIf .value = "" Then
                aSMR = 0
                Else
                pEvent.UnitSMR = .value
        End If
    End With
End Sub
Private Sub checkDate()
    With TextBox_Date
        If Not IsDate(.value) Then
            MsgBox "Date must be a valid date!"
            .value = Format(Now, getDateFormat)
            .SetFocus
            StopOkay = True
            ElseIf DateValue(.value) > Now Then
                MsgBox "Date cannot be later than today!" & dLine _
                        & "Today's date: " & Format(Now, getDateFormat) & Line _
                        & "Your date: " & Format(.value, getDateFormat)
                .value = Format(Now, getDateFormat)
                .SetFocus
                StopOkay = True
                Else
                pEvent.DateEvent = .value
        End If
    End With
End Sub
Private Sub checkTitle()
    With TextBox_Title
        If .value = "" Then
            MsgBox "Please enter an event title."
            StopOkay = True
            Else
            pEvent.Title = .value
        End If
    End With
End Sub
