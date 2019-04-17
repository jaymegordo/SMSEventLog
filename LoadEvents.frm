VERSION 5.00
Begin {C62A69F0-16DC-11CE-9E98-00AA00574A4F} LoadEvents 
   Caption         =   "Load"
   ClientHeight    =   3360
   ClientLeft      =   102
   ClientTop       =   384
   ClientWidth     =   1764
   OleObjectBlob   =   "LoadEvents.frx":0000
   StartUpPosition =   1  'CenterOwner
End
Attribute VB_Name = "LoadEvents"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = False
Attribute VB_PredeclaredId = True
Attribute VB_Exposed = False
Private pf As cFilter
Private pIws As Integer

Private Sub userform_initialize()
    Set pf = New cFilter
    pIws = getWSInt(ActiveSheet.CodeName)
End Sub

Private Sub CommandButton_Cancel_Click()
    Unload Me
End Sub

Private Sub CommandButton_CO_Click()
    Unload Me
    RefreshTable "CO"
End Sub

Private Sub CommandButton_Date_Click()
    Unload Me
    launchRefreshDateRange
End Sub

Private Sub CommandButton_Open_Click()
    Me.Hide
    RefreshTable RefreshType:="AllOpen", sOrder:="Unit, StatusEvent DESC, "
    Unload Me
End Sub

Private Sub CommandButton_Unit_Click()
    Unload Me
    refreshUnit
End Sub

