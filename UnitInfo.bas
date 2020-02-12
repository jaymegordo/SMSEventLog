Attribute VB_Name = "UnitInfo"


Sub addSelectedUnit()
    On Error GoTo errHandle
    iws = getWSInt(ActiveSheet.CodeName)
    setTblVars iws
    Set Target = ActiveCell
    IntersectCheck dbr, Target
    i = getActiveRow(tbl, Target)
    
    With dbr
        aMineSite = .Cells(i, 1)
        aModel = .Cells(i, 2)
        aSerial = .Cells(i, 3)
        aEngineSerial = .Cells(i, 4)
        aUnit = .Cells(i, 5)
        aDeliveryDate = .Cells(i, 6)
    End With
    
    Query = "Select * From UnitID Where Unit='" & aUnit & "'"
    
    Dim db As New cDB
    db.OpenConn
    db.rs.Open Query, db.conn, adOpenStatic, adLockOptimistic
    
    With db.rs
        beforecount = .RecordCount

        If beforecount < 1 Then .AddNew

        !MineSite = aMineSite
        !Model = aModel
        !Serial = aSerial
        !EngineSerial = aEngineSerial
        !Unit = aUnit
        !DeliveryDate = aDeliveryDate
        .Update
        
        rowsadded = .RecordCount - beforecount
    End With

    If rowsadded > 0 Then
        aMessage = rowsadded & " new row(s) added to UnitID table." & dLine
        Else
        aMessage = "Record updated: " & dLine
    End If
    
    MsgBox aMessage _
            & "MineSite: " & aMineSite & Line _
            & "Model: " & aModel & Line _
            & "Serial: " & aSerial & Line _
            & "Engine Serial: " & aEngineSerial & Line _
            & "Unit: " & aUnit & Line _
            & "Delivery Date: " & aDeliveryDate
    
cleanup:
    On Error Resume Next
    db.rs.Close
    Exit Sub
errHandle:
    sendErrMsg "addSelectedUnit"

End Sub
