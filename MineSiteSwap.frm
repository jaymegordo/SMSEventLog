VERSION 5.00
Begin {C62A69F0-16DC-11CE-9E98-00AA00574A4F} MineSiteSwap 
   Caption         =   "Change MineSite"
   ClientHeight    =   3570
   ClientLeft      =   102
   ClientTop       =   378
   ClientWidth     =   2892
   OleObjectBlob   =   "MineSiteSwap.frx":0000
   StartUpPosition =   1  'CenterOwner
End
Attribute VB_Name = "MineSiteSwap"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = False
Attribute VB_PredeclaredId = True
Attribute VB_Exposed = False
Private Sub CommandButton_Cancel_Click()
    Unload Me
End Sub

Private Sub CommandButton_Okay_Click()
    On Error GoTo errHandle
    Application.EnableEvents = False
    setMineSite ListBox_MineSite.value

cleanup:
    On Error Resume Next
    Application.EnableEvents = True
    Unload Me
    Exit Sub
errHandle:
    sendErrMsg "CommandButton_Okay_Click"
    Resume cleanup
End Sub


Private Sub UserForm_KeyPress(ByVal KeyAscii As MSForms.ReturnInteger)
    'If KeyAscii = 27 Then Unload Me
    Debug.Print KeyAscii.value
End Sub

Private Sub userform_initialize()
    centerUserform Me
    Dim tbl As ListObject
    Dim dbr As Range
    Set tbl = Sheet4.ListObjects("MineSite_Table")
    Set dbr = tbl.DataBodyRange
    
    With ListBox_MineSite
        For i = 1 To dbr.Rows.Count
            .AddItem dbr.Cells(i, 1)
        Next
    
        aMineSite = getMineSite
        For i = 0 To .ListCount - 1
            If .list(i) = aMineSite Then
                .Selected(i) = True
                Exit For
            End If
        Next i
    End With
    
    
End Sub


