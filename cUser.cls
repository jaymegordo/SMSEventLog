VERSION 1.0 CLASS
BEGIN
  MultiUse = -1  'True
END
Attribute VB_Name = "cUser"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = False
Attribute VB_PredeclaredId = False
Attribute VB_Exposed = False
Private prsUser As ADODB.Recordset
Private pDB As cDB
Private pUser As String
Private pVer As Double

Private Sub class_initialize()
    On Error GoTo errHandle
    pUser = Application.UserName
    pVer = Range("Version")
    setUser
cleanup:
    On Error Resume Next
    Exit Sub
errHandle:
    'sendErrMsg "cUser.class_initialize"
    Resume cleanup
End Sub
Public Sub Login()
    On Error GoTo errHandle
    With prsUser
        
        !LastLogin = Format(Now, "yyyy-mm-dd hh:nn:ss")
        !Version = pVer
        !NumOpens = !NumOpens + 1
        !FilePath = ThisWorkbook.FullName
        .Update
    End With
cleanup:
    On Error Resume Next
    prsUser.Close
    Exit Sub
errHandle:
    'sendErrMsg "cUser.Login"
    Resume cleanup
End Sub
Public Sub UpdateHrs()
    On Error GoTo errHandle
    Dim NewHours As Double
    With prsUser
        If !LastLogin Is Not Null Then NewHours = (Now - CDate(!LastLogin)) * 24
        If NewHours > 12 Then GoTo cleanup
        
        If .RecordCount = 1 Then
            !LastLogin = Now
            !Hours = !Hours + NewHours
            !Version = pVer
            .Update
        End If
    End With
    
cleanup:
    On Error Resume Next
    prsUser.Close
    Exit Sub
errHandle:
'    sendErrMsg "cUser.UpdateHrs"
    Resume cleanup
End Sub
Private Sub setUser()
    On Error GoTo errHandle
    
    Query = "Select * From UserSettings Where UserName='" & pUser & "'"
    Set pDB = New cDB
    pDB.OpenConn
    pDB.rs.Open Query, pDB.conn, adOpenStatic, adLockOptimistic
    Set prsUser = pDB.rs
    
    With prsUser
        If .RecordCount < 1 Then
            .AddNew
            !UserName = pUser
            .Update
            Debug.Print "Added user, new recordcount:", .RecordCount
        End If
    End With
cleanup:
    On Error Resume Next
    Exit Sub
errHandle:
    'sendErrMsg "cUser.setUser"
    Resume cleanup
End Sub
Public Property Get UserName() As String
    UserName = pUser
End Property
