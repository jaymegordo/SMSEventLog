VERSION 1.0 CLASS
BEGIN
  MultiUse = -1  'True
END
Attribute VB_Name = "cFilter"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = False
Attribute VB_PredeclaredId = False
Attribute VB_Exposed = False
Private pFinal As String
Private pColl As Collection
Private pF2 As cFilter

Public Sub add(sField As String, Optional val As Variant, Optional Extra As Integer = 1)

    Dim sFilter As String
    If Not IsMissing(val) Then
        If VarType(val) = vbString Or VarType(val) = vbDate Then
            sFilter = sField & "'" & val & "'"
            Else
            sFilter = sField & val
        End If
        Else
        sFilter = sField
    End If
    
    If Extra = 2 Then 'Lol so sketch
        If isInit2 Then
            pF2.add sFilter
            Else
            init2
        End If
        Exit Sub
    End If

    pColl.add sFilter
End Sub
Public Function Contains(sCheck As String) As Boolean
    For Each Item In pColl
        If Item Like "*.*" Then 'if the item has a '.' then split it into table and field
            sArray = Split(Item, ".")
            sTable = sArray(0)
            sField = sArray(1)
            Else
            sField = Item
        End If
        
        If sField Like "*" & sCheck & "*" Then
            Contains = True
            Exit For
        End If
    Next
End Function
Public Property Get Filter() As String
    
    For Each Item In pColl
        If pFinal <> "" Then
            pFinal = pFinal & " And " & Item
            Else
            pFinal = Item
        End If
    Next
    
    If pFinal <> "" Then pFinal = " Where " & pFinal
    Filter = pFinal & " "
    
End Property
Public Property Get FilterSpecific(sItem As String, _
                            Optional ExcludeTable As Boolean = False, _
                            Optional ExcludeWhere As Boolean = False) As String
    On Error GoTo errHandle
    Dim sArray() As String
    If Not ExcludeWhere Then sWhere = "Where "
    
    If sItem Like "*,*" Then
        arrFilters = Split(sItem, ",")
        Else
        arrFilters = Array(sItem)
    End If
    
    For i = 0 To UBound(arrFilters) 'loop through each item we got from array of sItem
        sTable = ""
        sField = ""
        sFilter = ""
        sItem = Trim(arrFilters(i))
        
        For Each Item In pColl 'pColl has the full strings that were '.add'ed
            If Item Like "*.*" Then 'if the item has a '.' then split it into table and field
                sArray = Split(Item, ".")
                sTable = sArray(0)
                sField = sArray(1)
                Else
                sField = Item
            End If
            
            If sField Like "*" & sItem & "*" Then ' did we find the target in pColl
                If Not sFinal = "" Then sFinal = sFinal & " And "
                
                If ExcludeTable And Item Like "*.*" Then
                    sFilter = sArray(1)
                    Else
                    sFilter = Item
                End If
                Exit For
            End If
        Next
        
        sFinal = sFinal & sFilter
    Next i
    
    FilterSpecific = sWhere & sFinal & " "
    
cleanup:
    On Error Resume Next
    Exit Property
errHandle:
    sendErrMsg "cFilter.FilterSpecific"
    Resume cleanup
End Property
Public Property Get Filter2() As cFilter
    If Not isInit2 Then init2
    Set Filter2 = pF2
End Property
Public Sub printFinal()
    Debug.Print Filter
End Sub
Public Sub printEach()
    For Each Item In pColl
        Debug.Print Item
    Next
End Sub
Private Sub class_initialize()
    Set pColl = New Collection
End Sub
Public Sub init2()
    Set pF2 = New cFilter
End Sub
Public Function isInit2() As Boolean
    If Not pF2 Is Nothing Then isInit2 = True
End Function
