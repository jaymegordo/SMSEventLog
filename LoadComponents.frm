VERSION 5.00
Begin {C62A69F0-16DC-11CE-9E98-00AA00574A4F} LoadComponents 
   Caption         =   "Load Comp."
   ClientHeight    =   5295
   ClientLeft      =   96
   ClientTop       =   384
   ClientWidth     =   3132
   OleObjectBlob   =   "LoadComponents.frx":0000
   StartUpPosition =   1  'CenterOwner
End
Attribute VB_Name = "LoadComponents"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = False
Attribute VB_PredeclaredId = True
Attribute VB_Exposed = False
Private pf As cFilter

Private Sub userform_initialize()
    On Error GoTo errHandle
    Set pf = New cFilter
    pf.add "ComponentCO=", "True"
    
    populateCombobox cbMineSite, rs:=getQuery("MineSite")
    MineSite = getMineSite(True)
    cbMineSite.value = MineSite
    centerUserform Me
    
cleanup:
    On Error Resume Next
    Exit Sub
errHandle:
    sendErrMsg "LoadComponents.userform_initialize"
    Resume cleanup
End Sub

Private Sub btnCancel_Click()
    Unload Me
End Sub

Private Sub btnOkay_Click() ' This is only for specific components
    launchQuery
End Sub

Private Sub ckComp_Click()
    With cbComp
        If .Enabled Then
            .Enabled = False
            Else
            populateCombobox cbComp, rs:=getQuery("Component")
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

Private Sub ckUnit_Click()
    With cbUnit
        If .Enabled Then
            .Enabled = False
            Else
            populateCombobox cbUnit, rs:=getQuery("Unit")
            .Enabled = True
        End If
    End With
End Sub

Private Sub CommandButton_All_Click()
    launchQuery
End Sub

Private Sub CommandButton_Cancel_Click()
    Unload Me
End Sub

Private Sub CommandButton_MajorComp_Click()
    pf.add "ComponentType.Major=", "True"
    launchQuery
End Sub

Private Sub launchQuery()
    On Error GoTo errHandle
    If ckMineSite.value Then pf.add "UnitID.MineSite=", cbMineSite.value
    If ckUnit.value Then pf.add "UnitID.Unit=", cbUnit.value
    If ckComp Then pf.add "ComponentType.Component=", cbComp.value
    
    Me.Hide
    RefreshTable f:=pf
cleanup:
    On Error Resume Next
    Application.EnableEvents = True
    Unload Me
    Exit Sub
errHandle:
    sendErrMsg "LoadComponents.launchQuery"
    Resume cleanup
End Sub
