VERSION 1.0 CLASS
BEGIN
  MultiUse = -1  'True
END
Attribute VB_Name = "cConn"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = False
Attribute VB_PredeclaredId = False
Attribute VB_Exposed = False


Private pconn As ADODB.Connection
Private pLastTime As Date

Public Property Get conn() As ADODB.Connection
    On Error GoTo errHandle
    
    'If connection has gone unused for more than 5 minutes, clear it
    If Abs(DateDiff("n", Now, pLastTime)) > 5 Then Set pconn = Nothing
    
    If pconn Is Nothing Then Set pconn = New ADODB.Connection
    Set conn = pconn
    pLastTime = Now
    
cleanup:
    On Error Resume Next
    Exit Property
errHandle:
    sendErrMsg "cConn.conn"
    Resume cleanup
End Property

Private Sub class_initialize()
    pLastTime = Now
End Sub

