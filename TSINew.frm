VERSION 5.00
Begin {C62A69F0-16DC-11CE-9E98-00AA00574A4F} TSINew 
   Caption         =   "Open New TSI (Not linked to Event)"
   ClientHeight    =   4095
   ClientLeft      =   96
   ClientTop       =   384
   ClientWidth     =   2844
   OleObjectBlob   =   "TSINew.frx":0000
   StartUpPosition =   1  'CenterOwner
End
Attribute VB_Name = "TSINew"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = False
Attribute VB_PredeclaredId = True
Attribute VB_Exposed = False
Private Sub CommandButton_Cancel_Click()
    Unload Me
End Sub

Private Sub CommandButton_OK_Click()
    On Error GoTo errHandle
    Set e = New cEvent
    
    With TextBox_Unit
        If .value = "" Then
            MsgBox "Please enter unit number."
            Exit Sub
            Else
            e.Unit = .value
        End If
    End With
    
    With TextBox_Date
        If .value = "" Then
            MsgBox "Please enter a date."
            .SetFocus
            Exit Sub
            ElseIf IsDate(.value) = False Then
                MsgBox "Please enter a date the right way, not the wrong way." & Line & "(You did it the wrong way.)"
                .value = Format(Now, "yyyy-mm-dd")
                .SetFocus
                Exit Sub
                Else
                e.DateEvent = DateValue(.value)
        End If
    End With
    
    With TextBox_Title
        If .value = "" Then
            MsgBox "Please enter an event title."
            .SetFocus
            Exit Sub
            Else
            e.Title = .value
        End If
    End With
    
    e.Component = TextBox_Component.value
    e.UID = createUID
    
    loadDB
    Set rs = db.OpenRecordset(getTable, dbOpenTable)
    With rs
        .AddNew
        !UID = e.UID
        !StatusTSI = "Open"
        !Unit = e.Unit
        !DateAdded = e.DateEvent
        !Title = e.Title
        !TSIPartName = e.Component
        !TSIAuthor = Application.UserName
        .Update
    End With
    
    Unload Me
    RefreshTable iws:=10
    
    'Create event folder when new event is added
'    If getMineSite <> "BaseMine" Then
        Set EventFolder = createFolder(e)
        EventFolder.CreateEventFolder True
'    End If
       
cleanup:
    On Error Resume Next
    cleanupDB
    Exit Sub
errHandle:
    sendErrMsg "TSINew_userform"
    
End Sub

Private Sub userform_initialize()
    centerUserform Me
    TextBox_Date.value = Format(Now, "yyyy-mm-dd")
End Sub

