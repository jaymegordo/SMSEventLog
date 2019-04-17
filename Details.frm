VERSION 5.00
Begin {C62A69F0-16DC-11CE-9E98-00AA00574A4F} Details 
   Caption         =   "Event Details | (Ctrl+Shift+D)"
   ClientHeight    =   11400
   ClientLeft      =   102
   ClientTop       =   384
   ClientWidth     =   10236
   OleObjectBlob   =   "Details.frx":0000
   StartUpPosition =   1  'CenterOwner
End
Attribute VB_Name = "Details"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = False
Attribute VB_PredeclaredId = True
Attribute VB_Exposed = False
Private pEvent As cEvent
Private prs As ADODB.Recordset

Private Sub CommandButton_Delete_Click()
    ans = MsgBox("Are you sure you want to delete this record from the Event Log database? This cannot be undone.", vbQuestion + vbYesNo, "Delete Record")
    If ans <> vbYes Then Exit Sub
    
    prs.Delete
    
    Me.Hide
    MsgBox "Record deleted."
    Unload Me
End Sub

Private Sub CommandButton_Update_Click()
    On Error GoTo errHandle
    
    With prs
        prevValue = .Fields(ListBox_Details.ListIndex).value
        .Fields(ListBox_Details.ListIndex) = TextBox_Details.value
        .Update
    End With
    
    With prs.Fields(ListBox_Details.ListIndex)
        strUpdate = .Name & " updated" & dLine & "From: " & Line & prevValue & dLine & "To:" & Line & TextBox_Details.value
        MsgBox strUpdate
    End With
    
cleanup:
    On Error Resume Next
    Exit Sub
errHandle:
    If Err.Number = 3421 Then
        MsgBox "Data type conversion error. Please check input data:"
        With TextBox_Details
            .value = prs.Fields(ListBox_Details.ListIndex).value
            .SetFocus
        End With
        Resume cleanup
    End If
    sendErrMsg "Details_updateClick"
    Resume cleanup
End Sub

Private Sub CommandButton_Cancel_Click()
    On Error Resume Next
    pEvent.TearDown
    prs.Close
    Unload Me
End Sub

Private Sub ListBox_Details_Click()
    On Error GoTo errHandle
    With prs.Fields(ListBox_Details.ListIndex)
        Label_Field.Caption = .Name & ":"
        TextBox_Details.value = .value
    End With
cleanup:
    On Error Resume Next
    Exit Sub
errHandle:
    sendErrMsg "ListBox_Details_Click"
    Resume cleanup
End Sub

Private Sub userform_initialize()
    On Error GoTo errHandle
    Set pEvent = createEventTable(ActiveCell)
    centerUserform Me
    
    Select Case pEvent.iws
        Case 1, 2, 10, 15
            Set prs = pEvent.rsEvent
        Case 7 'FC Details
            Set prs = pEvent.rsFC(False, True, True)
        Case 8 'FC Summary
            Set prs = pEvent.rsFCSummary(True)
        Case Else
            MsgBox "Details function not set for this table yet."
            Unload Me
            Exit Sub
    End Select
        
    With prs
        If .RecordCount = 1 Then
            For i = 0 To .Fields.Count - 2
                ListBox_Details.AddItem .Fields(i).Name & ": " & .Fields(i).value
nextField:
            Next i
            Else
            Err.Raise 444, , "More than one record found: " & .RecordCount
        End If
    End With
        
cleanup:
    On Error Resume Next
    Exit Sub
errHandle:
    If Err.Number = -2147352571 Then
        ListBox_Details.RemoveItem (i)
        ListBox_Details.AddItem prs.Fields(i).Name & ": *************ERROR*************"
        Resume nextField
    End If
    sendErrMsg "getDetails_initialize"
    Resume cleanup
End Sub
