VERSION 5.00
Begin {C62A69F0-16DC-11CE-9E98-00AA00574A4F} Passover 
   Caption         =   "Passover"
   ClientHeight    =   2670
   ClientLeft      =   102
   ClientTop       =   384
   ClientWidth     =   1752
   OleObjectBlob   =   "Passover.frx":0000
   StartUpPosition =   1  'CenterOwner
End
Attribute VB_Name = "Passover"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = False
Attribute VB_PredeclaredId = True
Attribute VB_Exposed = False
Private Sub CommandButton_Clear_Click()
    Unload Me
    clearPassover
End Sub
Private Sub CommandButton_ImportCummins_Click()
    Unload Me
    importCummins
End Sub
Private Sub CommandButton_LaunchEmail_Click()
    Unload Me
    emailPassover
End Sub
Private Sub CommandButton_Sort_Click()
    Unload Me
    sortPassover
End Sub
Private Sub userform_initialize()
    centerUserform Me
End Sub
