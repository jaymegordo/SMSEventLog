VERSION 5.00
Begin {C62A69F0-16DC-11CE-9E98-00AA00574A4F} FCSummary 
   Caption         =   "Refresh FC Summary"
   ClientHeight    =   1575
   ClientLeft      =   102
   ClientTop       =   378
   ClientWidth     =   1944
   OleObjectBlob   =   "FCSummary.frx":0000
   StartUpPosition =   1  'CenterOwner
End
Attribute VB_Name = "FCSummary"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = False
Attribute VB_PredeclaredId = True
Attribute VB_Exposed = False
Private Sub CommandButton_OpenOnly_Click()
    refreshFCSummary
    Unload Me
End Sub

Private Sub CommandButton1_Click()
    refreshFCSummary True
    Unload Me
End Sub
Private Sub userform_initialize()
    centerUserform Me
End Sub
