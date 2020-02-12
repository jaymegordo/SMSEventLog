Attribute VB_Name = "Parts"


Sub lookupPartName()
    On Error GoTo errHandle
    disableCummins
    Dim testArr() As String
    iws = getWSInt(ActiveSheet.CodeName)
    loadKeyVars iws, ActiveCell
    
    Dim db As New cDB
    db.OpenConn
    
    testArr = splitMultiDelims(aPartNo, ",")
    
    For i = 0 To UBound(testArr)
        aPartNo = Trim(testArr(i))
        Query = "SELECT * FROM Parts WHERE PartNo ='" & aPartNo & "'"
        
        db.rs.Open Query, db.conn, adOpenStatic, adLockReadOnly
        With db.rs
            If .RecordCount > 0 Then
                .MoveFirst
                strParts = strParts & !PartNo & " - " & !PartName & Line
            End If
            .Close
        End With
    Next i
    
    If strParts = "" Then
        MsgBox "Could not find matching part name for: " & aPartNo
        GoTo cleanup
    End If
    
    MsgBox strParts
    
cleanup:
    On Error Resume Next
    cleanupDB
    Exit Sub
errHandle:
    sendErrMsg "lookupPartName"
    Resume cleanup
End Sub


