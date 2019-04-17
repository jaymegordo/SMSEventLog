VERSION 5.00
Begin {C62A69F0-16DC-11CE-9E98-00AA00574A4F} LinkCO 
   Caption         =   "Link Component COs"
   ClientHeight    =   6540
   ClientLeft      =   96
   ClientTop       =   384
   ClientWidth     =   10872
   OleObjectBlob   =   "LinkCO.frx":0000
   StartUpPosition =   1  'CenterOwner
End
Attribute VB_Name = "LinkCO"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = False
Attribute VB_PredeclaredId = True
Attribute VB_Exposed = False
Private Sub CommandButton_Cancel_Click()
    Unload Me
    End
End Sub

Private Sub CommandButton_Link_Click()
    'aCO = ListBox1.Value
    
    'Debug.Print ListBox1.ListIndex
    b = 0
    With rs3 'This sets the recordset to the correct existing record to be linked > uses "MoveNext" till on correct record (ListIndex is currently selected item?)
        .MoveFirst
        Do While b < ListBox1.ListIndex
            .MoveNext
            b = b + 1
        Loop
        Debug.Print "Link: ", !Unit & " | " & !DateAdded & " | " & !Title
        addEditCORecordFromSunBench aRecordset:=rs3, EditOnly:=True
'        addEditCORecordfromGoogleSheet aRecordset:=rs3, EditOnly:=True
    End With
    
    'Debug.Print aCO
    LinkCO.Hide
End Sub

Private Sub CommandButton_NoMatch_Click()
    'create new event for current CO record
    
    addEditCORecordFromSunBench aRecordset:=rs, EditOnly:=False
'    addEditCORecordfromGoogleSheet aRecordset:=rs3, EditOnly:=False
    LinkCO.Hide
End Sub

