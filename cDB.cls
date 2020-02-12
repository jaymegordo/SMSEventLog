VERSION 1.0 CLASS
BEGIN
  MultiUse = -1  'True
END
Attribute VB_Name = "cDB"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = False
Attribute VB_PredeclaredId = False
Attribute VB_Exposed = False
Private prs As ADODB.Recordset
Private pconn As ADODB.Connection
Private arrRs() As Variant
Private arrInput() As Variant
Private arrMaxColLen() As Long
Private pArrInit As Boolean

'Provider=MSOLEDBSQL
'"Provider=MSDASQL;DSN=dsnName;UID=MyUserID;PWD=MyPassword;"
'SQLOLEDB.1
'MSDASQL.1
'Microsoft.WINDOWS.SQLLITE.OLEDB.4.0
'SQLNCLI11.1

Const sConnect = "Provider=SQLOLEDB.1;Server=tcp:jgazure1.database.windows.net,1433;Database=db1;Uid=jgordon@jgazure1;" _
                & "Pwd={Z%^7wdpf%Nai=^ZFy-U.};Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;"

Private Sub class_initialize()
    
End Sub

Public Property Get conn() As ADODB.Connection
    Set conn = pconn
End Property

Public Property Set conn(ByVal oconn As ADODB.Connection)
    Set pconn = oconn
End Property

                
Public Property Get rs() As ADODB.Recordset
    Set rs = prs
End Property

Public Property Set rs(ByVal ors As ADODB.Recordset)
    Set prs = ors
End Property

Public Sub closeConn()
    On Error Resume Next
    prs.Close
End Sub

Public Sub loadToTable(tbl As ListObject)
    On Error GoTo errHandle
    Application.ScreenUpdating = False
    ClearFilter tbl
    
    Application.EnableEvents = False
    ClearTable tbl
    Application.EnableEvents = False
    
    tbl.DataBodyRange.Cells(1, 1).CopyFromRecordset prs

cleanup:
    On Error Resume Next
    'Application.EnableEvents = True
    Exit Sub
errHandle:
    sendErrMsg "loadToTable"
    Resume cleanup
End Sub

Public Sub OpenConn(Optional UseServer As Boolean = False)
    On Error GoTo errHandle
    If gConn Is Nothing Then Set gConn = New cConn
    If gConn.conn.State = 0 Then gConn.conn.Open sConnect
    
    Set pconn = gConn.conn
    
    Set prs = New ADODB.Recordset
    If Not UseServer Then prs.CursorLocation = adUseClient
    
    'Debug.Print "Open conn"
    
    If collConns Is Nothing Then Set collConns = New Collection
    collConns.add Me
    
cleanup:
    On Error Resume Next
    Exit Sub
errHandle:
    sendErrMsg "cDB.OpenConn"
    Resume cleanup
End Sub

Private Sub printHeader()
    For y = 0 To UBound(arrRs, 2)
        strVal = prs.Fields(y).Name
        strPrint = strPrint & strVal & Space(arrMaxColLen(y) - Len(strVal) + 5)
    Next y
    Debug.Print strPrint
    Debug.Print String(Len(strPrint) - 5, "-")
End Sub

Private Sub printLine(i As Long)
    For y = 0 To UBound(arrRs, 2)
        strVal = arrRs(i, y)
        If IsNull(strVal) Then strVal = ""
        If Len(strVal) > 50 Then strVal = Left(strVal, 50)
        strVal = Replace(strVal, Chr(10), " ")
        strPrint = strPrint & strVal & Space(arrMaxColLen(y) - Len(strVal) + 5)
    Next y
    Debug.Print strPrint
End Sub

Public Sub printRs(Optional MaxRows As Long)
    On Error GoTo errHandle
    Dim i As Long
    If Not pArrInit Then setArray
    If MaxRows = 0 Or MaxRows > UBound(arrRs, 1) Then MaxRows = UBound(arrRs, 1) '- 1
    
    ReDim arrMaxColLen(UBound(arrRs, 2)) As Long
    
    'find max length of each column
    For y = 0 To UBound(arrRs, 2)
        maxLen = Len(prs.Fields(y).Name)
        For i = 0 To MaxRows
            If IsNull(arrRs(i, y)) Then
                curLen = 0
                Else
                curLen = Len(arrRs(i, y))
            End If
            If curLen > maxLen Then maxLen = curLen
            If maxLen > 50 Then
                maxLen = 50
                Exit For
            End If
        Next i
        arrMaxColLen(y) = maxLen
    Next y
    
    printHeader
    For i = 0 To MaxRows
        printLine i
    Next i

cleanup:
    On Error Resume Next
    Exit Sub
errHandle:
    sendErrMsg "cDB.printRs"
    Resume cleanup
End Sub

Public Sub setArray()
    pArrInit = True
    arrInput = prs.GetRows
    TransposeArray
End Sub

Public Sub TransposeArray()
    Dim RowNdx As Long, ColNdx As Long
    Dim LB1 As Long, LB2 As Long, UB1 As Long, UB2 As Long

    LB1 = LBound(arrInput, 1)
    LB2 = LBound(arrInput, 2)
    UB1 = UBound(arrInput, 1)
    UB2 = UBound(arrInput, 2)

    ReDim arrRs(LB2 To UB2, LB1 To UB1)

    For RowNdx = LB2 To UB2
    For ColNdx = LB1 To UB1
        arrRs(RowNdx, ColNdx) = arrInput(ColNdx, RowNdx)
    Next ColNdx, RowNdx

End Sub

