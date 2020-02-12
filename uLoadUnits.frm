VERSION 5.00
Begin {C62A69F0-16DC-11CE-9E98-00AA00574A4F} uLoadUnits 
   Caption         =   "Load Units"
   ClientHeight    =   2865
   ClientLeft      =   102
   ClientTop       =   378
   ClientWidth     =   3084
   OleObjectBlob   =   "uLoadUnits.frx":0000
   StartUpPosition =   1  'CenterOwner
End
Attribute VB_Name = "uLoadUnits"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = False
Attribute VB_PredeclaredId = True
Attribute VB_Exposed = False
Private pf As cFilter
Private Sub userform_initialize()
    On Error GoTo errHandle
    Set pf = New cFilter
    
    populateCombobox cbMineSite, rs:=getQuery("MineSite")
    MineSite = getMineSite(True)
    cbMineSite.value = MineSite
    If MineSite = "FortHills" Then
        ckModel.value = True
        cbModel.value = "980*"
    End If
    centerUserform Me

cleanup:
    On Error Resume Next
    Exit Sub
errHandle:
    sendErrMsg "ViewFCDetails.userform_initialize"
    Resume cleanup
End Sub
Private Sub btnCancel_Click()
    Unload Me
End Sub
Private Sub btnOkay_Click()
    On Error GoTo errHandle
    Dim sFilter As String
    
    'MineSite
    If cbMineSite.Enabled Then pf.add "MineSite=", cbMineSite
    
    'Model
    If ckModel.value Then
        If cbModel.value Like "*" Then
            Comparison = " Like "
            Else
            Comparison = " = "
        End If
        
        sFilter = "Model" & Comparison & " '" & Replace(cbModel.value, "*", "%") & "'"
        pf.add sFilter
    End If
    
    Me.Hide
    RefreshTable f:=pf
cleanup:
    On Error Resume Next
    Application.EnableEvents = True
    Unload Me
    Exit Sub
errHandle:
    sendErrMsg "ViewFCDetails.btnOkay_Click"
    Resume cleanup
End Sub
Private Sub ckModel_Click()
    With cbModel
        If .Enabled Then
            .Enabled = False
            Else
            populateCombobox cbModel, rs:=getQuery("Model")
            .Enabled = True
        End If
    End With
End Sub
Private Sub ckMineSite_Click()
    With cbMineSite
        If .Enabled Then
            .Enabled = False
            Else
            .Enabled = True
        End If
    End With
End Sub
