VERSION 5.00
Begin {C62A69F0-16DC-11CE-9E98-00AA00574A4F} ViewFC 
   Caption         =   "View Factory Campaigns"
   ClientHeight    =   2865
   ClientLeft      =   72
   ClientTop       =   324
   ClientWidth     =   3444
   OleObjectBlob   =   "ViewFC.frx":0000
   StartUpPosition =   1  'CenterOwner
End
Attribute VB_Name = "ViewFC"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = False
Attribute VB_PredeclaredId = True
Attribute VB_Exposed = False
Private Sub CommandButton_Cancel_Click()
    Unload Me
End Sub

Private Sub CommandButton_Okay_Click()
    Unload Me
    refreshFCSummary OpenOnly:=CheckBox_OpenOnly.value, _
                        DeliveredOnly:=CheckBox_DeliveredOnly.value, _
                        CustomerFriendly:=CheckBox_CustomerFriendly.value, _
                        ModelFilter:=ComboBox_Model.value
    
End Sub
Private Sub userform_initialize()
    centerUserform Me
    CheckBox_OpenOnly.value = True
    
    With ComboBox_Model
        .AddItem "980E"
        .AddItem "930E"
        .AddItem "HD1500"
    End With
End Sub
