VERSION 5.00
Begin {C62A69F0-16DC-11CE-9E98-00AA00574A4F} CopyWorksheet 
   Caption         =   "Copy Worksheet"
   ClientHeight    =   6465
   ClientLeft      =   102
   ClientTop       =   384
   ClientWidth     =   7512
   OleObjectBlob   =   "CopyWorksheet.frx":0000
   StartUpPosition =   1  'CenterOwner
End
Attribute VB_Name = "CopyWorksheet"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = False
Attribute VB_PredeclaredId = True
Attribute VB_Exposed = False
Dim wb As Workbook
Dim ws As Worksheet

Private Sub cbSourceWb_Change()
    populateListBoxWb lbSourceWs, Workbooks(cbSourceWb.value)
End Sub
Private Sub cbDestWb_Change()
    populateListBoxWb lbDestWs, Workbooks(cbDestWb.value)
End Sub
Private Sub populateListBoxWb(lb As MSForms.ListBox, wb As Workbook)
    lb.clear
    For Each ws In wb.Worksheets
        lb.AddItem ws.Name
    Next
End Sub
Private Sub ckReplaceWs_Click()
    If ckReplaceWs.value Then
        lbDestWs.Enabled = True
        populateListBoxWb lbDestWs, Workbooks(cbDestWb.value)
        Else
        lbDestWs.Enabled = False
        lbDestWs.clear
    End If
End Sub


Private Sub userform_initialize()
    
    For Each wb In Application.Workbooks
        cbSourceWb.AddItem wb.Name
        cbDestWb.AddItem wb.Name
    Next
    cbSourceWb.value = Application.Workbooks(1).Name
    cbDestWb.value = Application.Workbooks(Application.Workbooks.Count).Name
    ckReplaceWs.value = False
    lbDestWs.clear
    
End Sub
Private Sub CommandButton_OK_Click()
    On Error GoTo errHandle
    
    If lbSourceWs.ListIndex = -1 Then
        MsgBox "Please select a source workbook."
        Exit Sub
    End If
    
    If ckReplaceWs.value Then
        If lbDestWs.ListIndex = -1 Then
            MsgBox "Please select a source workbook."
            Exit Sub
        End If
    End If
    
    Dim wbe As New cwbExport
    With wbe
        Set .wbSource = Workbooks(cbSourceWb.value)
        Set .wbDest = Workbooks(cbDestWb.value)
        .addWs .wbSource.Worksheets(lbSourceWs.value), getReplaceWs
        If lbSourceWs.value = "FC Summary" Then
            .ws(1).Shapes(2).visible = msoFalse
            .ws(1).Shapes(1).GroupItems(1).OnAction = "'" & .wbDest.Name & "'!expandCollapseCols"
            .ws(1).Shapes(1).GroupItems(2).OnAction = "'" & .wbDest.Name & "'!expandCollapseRows"
        End If
        .CopyModule "Functions"
        .copyColours
        .wbDest.Activate
    End With
    
    Unload Me
        
cleanup:
    On Error Resume Next
    Exit Sub
errHandle:
    sendErrMsg "CommandButton_OK_Click"
    Resume cleanup
End Sub
Private Sub CommandButton_Cancel_Click()
    Unload Me
End Sub
Private Function getReplaceWs() As Worksheet
    If ckReplaceWs.value Then Set getReplaceWs = Workbooks(cbDestWb.value).Worksheets(lbDestWs.value)
End Function

