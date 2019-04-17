VERSION 5.00
Begin {C62A69F0-16DC-11CE-9E98-00AA00574A4F} PLM 
   Caption         =   "SMS PLM Report"
   ClientHeight    =   3015
   ClientLeft      =   102
   ClientTop       =   378
   ClientWidth     =   1692
   OleObjectBlob   =   "PLM.frx":0000
   StartUpPosition =   1  'CenterOwner
End
Attribute VB_Name = "PLM"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = False
Attribute VB_PredeclaredId = True
Attribute VB_Exposed = False
Private Sub CommandButton_Cancel_Click()
    Unload Me
End Sub
Private Sub CommandButton_launchReportGenerator_Click()
    Unload Me
    launchPLMReportGenerator
    Unload Me
End Sub
Private Sub CommandButton_Upload_Click()
    Unload Me
    importPLM
End Sub
Private Sub userform_initialize()
    centerUserform Me
End Sub
