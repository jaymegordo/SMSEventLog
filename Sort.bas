Attribute VB_Name = "Sort"
Sub sortPassover()
Attribute sortPassover.VB_ProcData.VB_Invoke_Func = " \n14"
    Application.ScreenUpdating = False
    Set ELT = Sheet1.ListObjects("EventLog")
    ELT.Sort _
        .SortFields.clear
    ELT.Sort _
        .SortFields.add key:=Range("EventLog[[#All],[Unit]]"), SortOn:= _
        xlSortOnValues, Order:=xlAscending, DataOption:=xlSortTextAsNumbers
    With ELT _
        .Sort
        .Header = xlYes
        .MatchCase = False
        .Orientation = xlTopToBottom
        .SortMethod = xlPinYin
        .Apply
    End With
    
    ELT.Sort _
        .SortFields.clear
    ELT.Sort _
        .SortFields.add key:=Range("EventLog[[#All],[Passover]]"), _
        SortOn:=xlSortOnValues, Order:=xlAscending, DataOption:= _
        xlSortTextAsNumbers
    With ELT _
        .Sort
        .Header = xlYes
        .MatchCase = False
        .Orientation = xlTopToBottom
        .SortMethod = xlPinYin
        .Apply
    End With
    Autofit_Height
End Sub
Sub sortDateAdded()
    Application.ScreenUpdating = False
    Set ELT = Sheet1.ListObjects("EventLog")
    ELT.Sort. _
        SortFields.clear
    ELT.Sort. _
        SortFields.add key:=Range("EventLog[[#All],[Date added]]"), SortOn:= _
        xlSortOnValues, Order:=xlDescending, DataOption:=xlSortTextAsNumbers
    With ELT.Sort
        .Header = xlYes
        .MatchCase = False
        .Orientation = xlTopToBottom
        .SortMethod = xlPinYin
        .Apply
    End With
    
    Autofit_Height
    Range("A5").Select
End Sub
Sub sortStatus()
    'Fix
    Application.ScreenUpdating = False
    setTblVars (1)
    
    tbl.Sort. _
        SortFields.clear
        tbl.Sort. _
        SortFields.clear
    tbl.Sort. _
        SortFields.add(Range("EventLog[Status]"), xlSortOnCellColor, xlAscending, , _
        xlSortNormal).SortOnValue.Color = RGB(255, 204, 204)
    tbl.Sort. _
        SortFields.add(Range("EventLog[Status]"), xlSortOnCellColor, xlAscending, , _
        xlSortNormal).SortOnValue.Color = RGB(250, 191, 143)
    tbl.Sort. _
        SortFields.add(Range("EventLog[Status]"), xlSortOnCellColor, xlAscending, , _
        xlSortNormal).SortOnValue.Color = RGB(255, 235, 156)
    With tbl.Sort
        .Header = xlYes
        .MatchCase = False
        .Orientation = xlTopToBottom
        .SortMethod = xlPinYin
        .Apply
    End With
    
    Autofit_Height
    Range("B5").Select
End Sub
Sub clearPassover()
Attribute clearPassover.VB_ProcData.VB_Invoke_Func = " \n14"
    On Error GoTo cleanup
    Application.ScreenUpdating = False
    Application.EnableEvents = False
    Set tbl = Sheet1.ListObjects(1)
    Set dbr = tbl.DataBodyRange

    For i = 1 To dbr.Rows.Count
        Set Target = dbr.Cells(i, 2)
        If Target <> "" Then
            checkRowUpdate Target, 1
            Target.ClearContents
        End If
    Next i
cleanup:
    Application.EnableEvents = True
End Sub
Sub Autofit_Height()
    Range("EventLog[[Title]:[REQUIRED]]").Rows.AutoFit
End Sub
Sub Copy_Passover()
    Dim NumRows As Long
    highlightRow ClearOnly:=True
    Sheet1.Range("EventLog[[#Headers],[Passover]]").Select
    Range(Selection, Selection.End(xlDown)).Select
    NumRows = Selection.Rows.Count
    ActiveCell.Offset(rowOffset:=0, columnOffset:=1).Activate
    Selection.Resize(NumRows, 6).Select
    Selection.Copy
    Sheet1.Range("EventLog[[#Headers],[Passover]]").Select
End Sub
Sub Jump()
    On Error Resume Next
    Set tbl = Sheet1.ListObjects(1)
    Set dbr = tbl.DataBodyRange
        
    If ActiveCell.row - tbl.HeaderRowRange.row > dbr.Rows.Count / 2 Then
        dbr.Cells(1, 5).Activate
        Else
        dbr.Cells(dbr.Rows.Count, 5).Activate
    End If
    Application.EnableEvents = True
End Sub
Sub JumpRight()
    On Error Resume Next
    Set tbl = Sheet1.ListObjects(1)
    Set dbr = tbl.DataBodyRange
    Sheet1.Cells(ActiveCell.row, tbl.ListColumns.Count).Activate
End Sub
Sub Reset_Filters()
    Sheet1.Select
    Set ELT = Sheet1.ListObjects(1)
    ELT.HeaderRowRange(1).Select
    If Sheet1.FilterMode Then
        Sheet1.ShowAllData
    End If
End Sub



