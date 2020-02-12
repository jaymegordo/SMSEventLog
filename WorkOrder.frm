VERSION 5.00
Begin {C62A69F0-16DC-11CE-9E98-00AA00574A4F} WorkOrder 
   Caption         =   "Work Order"
   ClientHeight    =   5460
   ClientLeft      =   102
   ClientTop       =   378
   ClientWidth     =   1752
   OleObjectBlob   =   "WorkOrder.frx":0000
   StartUpPosition =   1  'CenterOwner
End
Attribute VB_Name = "WorkOrder"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = False
Attribute VB_PredeclaredId = True
Attribute VB_Exposed = False
Private Sub CommandButton_AddNew_Click()
    Unload Me
    addNewWO
End Sub

Private Sub CommandButton_Cancel_Click()
    Unload Me
End Sub

Private Sub CommandButton_Close_Click()
    Unload Me
    closeWO
End Sub
Private Sub CommandButton_Delete_Click()
    Unload Me
    DeleteRecords
End Sub
Private Sub CommandButton_EmailCompReturns_Click()
    Unload Me
    emailComponentReturns
End Sub
Private Sub CommandButton_EmailRequest_Click()
    Unload Me
    emailWORequest True
End Sub
Private Sub CommandButton_GetWO_Click()
    Unload Me
    getWOFromOutlook
End Sub
Private Sub CommandButton_PRP_Click()
    Unload Me
    emailPRP
End Sub
Private Sub userform_initialize()
    centerUserform Me
End Sub
