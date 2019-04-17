VERSION 5.00
Begin {C62A69F0-16DC-11CE-9E98-00AA00574A4F} Events 
   Caption         =   "Events"
   ClientHeight    =   3840
   ClientLeft      =   102
   ClientTop       =   384
   ClientWidth     =   1764
   OleObjectBlob   =   "Events.frx":0000
   StartUpPosition =   1  'CenterOwner
End
Attribute VB_Name = "Events"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = False
Attribute VB_PredeclaredId = True
Attribute VB_Exposed = False
Private Sub CommandButton_AddNew_Click()
    Unload Me
    launchAddEvent
End Sub
Private Sub CommandButton_Cancel_Click()
    Unload Me
End Sub
Private Sub CommandButton_Delete_Click()
    Unload Me
    DeleteRecords
End Sub
Private Sub CommandButton_SortDate_Click()
    Unload Me
    sortDateAdded
End Sub
Private Sub CommandButton_SortStatus_Click()
    Unload Me
    sortStatus
End Sub

