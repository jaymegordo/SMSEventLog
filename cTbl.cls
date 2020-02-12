VERSION 1.0 CLASS
BEGIN
  MultiUse = -1  'True
END
Attribute VB_Name = "cTbl"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = False
Attribute VB_PredeclaredId = False
Attribute VB_Exposed = False
Option Explicit
Private pTbl As ListObject
Private pCell As Range
Private pDbr As Range
Private pCols As Long
Private pRows As Long
Private pJHdr As cJobject
Private m_strHdr As String
Dim aCol As Integer
Dim aListCol As ListColumn
Dim i As Integer

Public Property Get HeaderString() As String 'fix > pJHdr
'    For i = 1 To pCols
'        m_strHdr = m_strHdr & pCollHeader.Item(i) & ", "
'    Next i
'    HeaderString = left(m_strHdr, Len(m_strHdr) - 2)
End Property
Public Property Get jHdr() As cJobject
    Set jHdr = pJHdr
End Property
Public Property Get tbl() As ListObject
    Set tbl = pTbl
End Property
Public Property Get NumCols() As Long
    NumCols = pCols
End Property
Public Property Get NumRows() As Long
    NumRows = pRows
End Property
Public Sub init(Optional pCell, Optional ws As Worksheet)
    On Error GoTo errHandle
    
    If IsMissing(pCell) Then
        Set pTbl = ws.ListObjects(1)
        Else
        'IntersectCheck pTbl.DataBodyRange, pCell
        Set pTbl = pCell.ListObject
    End If
    
    If pTbl Is Nothing Then
        MsgBox "cTbl Initialization | Table not set.", vbExclamation
        End
    End If
    
    'Set pCollHeader = New Collection
    Set pJHdr = New cJobject
    pJHdr.init Nothing
    
    pCols = pTbl.ListColumns.Count
    pRows = pTbl.ListRows.Count
    
    Dim aHdr As String
    
    For i = 1 To pCols
        aHdr = pTbl.HeaderRowRange.Cells(, i)
        'If aHdr <> "_$dbab$key$_" Then 'For now, never include the db key
            pJHdr.add aHdr
        'End If
    Next i
    
    'loopJson pJHdr, , True
cleanup:
    Exit Sub
errHandle:
    sendErrMsg "cTbl Initialization"
    Resume cleanup
End Sub
Public Function getHeaderCol(strHdr As String) As Long
    On Error GoTo errHandle
    getHeaderCol = pJHdr.find(strHdr).childIndex
    
cleanup:
    On Error Resume Next
    Exit Function
errHandle:
    getHeaderCol = 0
    Resume cleanup
End Function

Public Function getHeaderStr(cl As Range) As String
    On Error GoTo errHandle
    getHeaderStr = pJHdr.children(ColNum(cl)).key
cleanup:
    Exit Function
errHandle:
    sendErrMsg "cTbl.getHeaderStr"
    Resume cleanup
End Function

Public Property Get ColNum(cl As Range) As Integer
    ColNum = cl.Column - pTbl.HeaderRowRange.Cells(1, 1).Column + 1
End Property

Public Function getIndex(strItem As Variant, strHdr As String) As Long
    On Error GoTo errHandle
    Set aListCol = pTbl.ListColumns(getHeaderCol(strHdr))
    
    With Application.WorksheetFunction
        If IsDate(strItem) Then
            getIndex = .match(CDbl(strItem), aListCol.DataBodyRange, 0)
            Else
            getIndex = .match(strItem, aListCol.DataBodyRange, 0)
        End If
    End With
    Exit Function
errHandle:
    getIndex = 0
End Function
Public Function getValue(aIndex As Long, strHdr As String) As String
    aCol = pJHdr.find(strHdr).childIndex
    Set aListCol = pTbl.ListColumns(aCol)
    getValue = aListCol.DataBodyRange.Cells(aIndex, 1).value
End Function
