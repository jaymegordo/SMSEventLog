Attribute VB_Name = "FilePaths"
Sub setFso()
    If FSO Is Nothing Then Set FSO = CreateObject("Scripting.FileSystemObject")
End Sub
Function loadSerialRecordset(Optional getRs As Boolean = False) As ADODB.Recordset 'Not used?
    On Error GoTo errHandle
    Set rs2 = db.OpenRecordset("UnitID", dbOpenTable)
    rs2.Index = "Unit"

    If getRs Then Set loadSerialRecordset = rs2
    
cleanup:
    On Error Resume Next
    Exit Function
errHandle:
    If Err.Number = 91 Then
        sendErrMsg "need to load db first"
        Resume cleanup
    End If
    sendErrMsg "loadSerialRecordset"
    Resume cleanup
End Function
Function getUnitSerial(aUnit)
    On Error GoTo errHandle
    If rs2 Is Nothing Then Set rs2 = loadSerialRecordset(True)
    With rs2
        .Seek "=", aUnit
        If .NoMatch = False Then
            If checkCummins = False Then
                getUnitSerial = !Serial
                Else
                getUnitSerial = !EngineSerial
            End If
            Else
            Err.Raise 444, "Can't get unit's serial number."
        End If
    End With
cleanup:
    On Error Resume Next
    Exit Function
errHandle:
    sendErrMsg "getUnitSerial"
    Resume cleanup
End Function

Function getQuery(Optional sType As String, Optional Query As String) As ADODB.Recordset
    On Error GoTo errHandle
    If Query = "" Then
        Select Case sType
            Case "Model"
                Query = "Select Distinct Model From UnitID"
            Case "MineSite"
                Query = "Select Distinct MineSite From UnitID"
            Case "Component"
                Query = "Select Distinct Component From ComponentType"
            Case "Unit"
                Query = "Select Unit From UnitID Where MineSite='" & getMineSite(True) & "'"
        End Select
    End If
    
    Dim db As New cDB
    With db
        .OpenConn
        .rs.Open Query, db.conn, adOpenForwardOnly, adLockReadOnly
        Set getQuery = .rs
    End With
cleanup:
    On Error Resume Next
    Exit Function
errHandle:
    sendErrMsg "getQuery"
    Resume cleanup
End Function
Function getUnitModel(Unit As String)
    On Error GoTo errHandle
    Query = "Select * From UnitID Where Unit='" & Unit & "'"
    
    Dim rs As ADODB.Recordset
    Set rs = getQuery(Query:=Query)
    
    With rs
        If .RecordCount = 1 Then
            getUnitModel = !Model
            Else
            Err.Raise 444, "Can't get unit's model number."
        End If
    End With
cleanup:
    On Error Resume Next
    rs.Close
    Exit Function
errHandle:
    sendErrMsg "getUnitModel"
    Resume cleanup
End Function
Function getMineSiteUnit(aUnit)
    On Error GoTo errHandle
    If rs2 Is Nothing Then loadSerialRecordset
    With rs2
        .Seek "=", aUnit
        If .NoMatch = False Then
            getMineSiteUnit = !MineSite
            Else
            Err.Raise 444, "Can't get unit's model number."
        End If
    End With
cleanup:
    On Error Resume Next
    Exit Function
errHandle:
    sendErrMsg "getMineSiteUnit"
    Resume cleanup
End Function
Function getModelPath(aUnit) As String 'This is only for BaseMine I think
    aNum = CInt(Left(aUnit, 1))
    Select Case aNum
        Case 2
            getModelPath = "1. 930E"
        Case 3
            getModelPath = "2. 980E"
        Case 6
            getModelPath = "3. HD1500"
    End Select
End Function

Sub testFC()
    Set e = createEventTable(ActiveCell)
'    Set EventFolder = createFolder(e)
    
    With e
        .PrintVars
    End With
End Sub


'------Event Folder
' These functions control the buttons/interaction with the cEventFolder class
Sub renameEventFolder(Optional iws, Optional Target As Range, Optional e As cEvent)
    On Error GoTo errHandle
'    loadKeyVars iws, Target 'this is only to check intersect?
    
    ans = MsgBox("Woah, looks like you're trying to change an Event title! The Event folder name will need to be changed as well. " _
                & "Would you like to rename this Event to: " & dLine & aTitle, vbYesNo, "Change Event Title")
    
    If ans = vbYes Then
        If IsMissing(e) Then Set e = createEventTable(Target, CInt(iws))
        Set EventFolder = createFolder(e)
        'EventFolder.PrintVars
    End If
    
cleanup:
    On Error Resume Next
    Exit Sub
errHandle:
    sendErrMsg "renameEventFolder"
    Resume cleanup
End Sub
Sub CreateEventFolder()
    Select Case getMineSite(True)
        Case "FortHills", "FH-TKMC", "Bighorn"
            Set e = createEventTable(ActiveCell)
            Set EventFolder = createFolder(e)
            EventFolder.CreateEventFolder True

        Case Else
            MsgBox "Sorry this feature is not enabled for your MineSite!"
            End
    End Select
End Sub

Sub viewEventFolder()
Attribute viewEventFolder.VB_ProcData.VB_Invoke_Func = "V\n14"
    On Error GoTo errHandle
    disableCummins
    iws = getWSInt(ActiveSheet.CodeName)
    
    Set e = createEventTable(ActiveCell)
    
'    Select Case iws
'        Case 15 'componentCO > need to get aTitle first ' could find it by WO now? > _____________should move this into cEvent
'            e.Floc = getFloc(e.Component, e.Modifier)
'            aQuery = "SELECT EventLog.* FROM EventLog LEFT JOIN ComponentType ON ComponentType.Floc = EventLog.Floc " _
'                    & "WHERE Unit='" & e.Unit & "' AND EventLog.Floc='" & e.Floc & "' AND DateAdded=#" & e.DateEvent & "#"
''                Debug.Print aQuery
'            Dim db As New cDB
'            db.OpenConn
'            db.rs.Open Query, db.conn, adOpenStatic, adLockReadOnly
'
'            With db.rs
'                If IsNull(!Title) Then
'                    MsgBox "Couldn't find event title."
'                    'Err.Raise 444, , "Didn't get event title."
'                    e.Title = ""
'                    Else
'                    e.Title = !Title
'                End If
'
'                e.UID = !UID
'                .Close
'            End With
'    End Select
    
    Set EventFolder = createFolder(e)
    EventFolder.ViewFolder
    
cleanup:
    On Error Resume Next
    EventFolder.TearDown
    Exit Sub
errHandle:
    sendErrMsg "viewEventFolder"
    Resume cleanup
End Sub
