Attribute VB_Name = "Functions_2"
'Functions2 with dependent libraries

Function createEventTable(Target As Range, Optional iws As Integer = 0, _
                            Optional Complain As Boolean = True) As cEvent
    If iws = 0 Then iws = getWSInt(ActiveSheet.CodeName)
    Dim e As New cEvent
    e.initTable iws, Target, Complain
    Set createEventTable = e
End Function

Function createFolder(e As cEvent) As cEventFolder
    Dim ef As New cEventFolder
    ef.init e:=e
    Set createFolder = ef
End Function

Sub populateCombobox(aBox As ComboBox, Optional aCol As ListColumn, Optional rs As Object)
    'Easily load a useform combo box from a table listcolumn
    With aBox
        If Not aCol Is Nothing Then 'load from a listcolumn
            For i = 2 To aCol.Range.Rows.Count
                .AddItem aCol.Range(i).value
            Next i
            .value = aCol.Range(2).value
            
            ElseIf Not IsMissing(rs) Then
                With rs
                    Do While .EOF <> True
                        aBox.AddItem .Fields(0).value
                        .MoveNext
                    Loop
                    .Close
                End With
                
                Else
'                'populate from FastQuery - THIS ISNT USED
'                Dim tbl As ListObject
'                Dim job As cJobject
'                Dim strQuery As String
'                iws = getWSInt(Worksheets("Summary").CodeName)
'                Set tbl = getWorkSheet(iws).ListObjects(1)
'
'                strQuery = "Select " & matchHeaderID("Title", tbl) & ", Count(" & matchHeaderID("Title", tbl) & ") group by " & matchHeaderID("Title", tbl)
'                Set job = FastQuery(strQuery, , iws)
'                For i = 1 To job.find("table.rows").children.count
'                    .AddItem job.find("table.rows").children(i).child("c.1.v").Value
'                Next i
'                .Value = job.find("table.rows").children(1).child("c.1.v").Value ' set the first value in the combobox
        End If

    End With
End Sub

Sub populateListBox(aBox As MSForms.ListBox, aCol As ListColumn, Optional SelectAll As Boolean = False)
    With aBox
        For i = 2 To aCol.Range.Rows.Count
            .AddItem aCol.Range(i).value
        Next i
        
        If SelectAll Then
            For i = 0 To .ListCount - 1
                If .list(i) <> "Closed" Then .Selected(i) = True
            Next i
        End If
    End With
End Sub
