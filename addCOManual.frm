VERSION 5.00
Begin {C62A69F0-16DC-11CE-9E98-00AA00574A4F} addCOManual 
   Caption         =   "Add CO Record"
   ClientHeight    =   1965
   ClientLeft      =   102
   ClientTop       =   378
   ClientWidth     =   3252
   OleObjectBlob   =   "addCOManual.frx":0000
   StartUpPosition =   1  'CenterOwner
End
Attribute VB_Name = "addCOManual"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = False
Attribute VB_PredeclaredId = True
Attribute VB_Exposed = False

Private pe As cEvent

Private Sub CommandButton_Cancel_Click()
    Unload Me
End Sub

Public Property Get e() As cEvent
    Set e = pe
End Property

Public Property Set e(ByVal obje As cEvent)
    Set pe = obje
End Property


Private Sub CommandButton_OK_Click()
    
    Query = "SELECT ComponentCO, Floc FROM EventLog WHERE UID=" & pe.UID
    
    Dim db As New cDB
    db.OpenConn True
    db.rs.Open Query, db.conn, adOpenStatic, adLockOptimistic
    With db.rs
        !ComponentCO = True
        !Floc = getFloc(ComboBox_CO.value)
        .Update
    End With
    
    MsgBox "Component CO record updated."
    
cleanup:
    On Error Resume Next
    db.rs.Close
    Unload Me
    Exit Sub
errHandle:
    sendErrMsg "Add CO OK Button"
    Resume cleanup
End Sub

Private Sub userform_initialize()
    On Error GoTo errHandle
    centerUserform Me
    Query = "SELECT Component, Modifier FROM ComponentType ORDER BY Component"
    
    Dim db As New cDB
    db.OpenConn
    db.rs.Open Query, db.conn, adOpenForwardOnly, adLockReadOnly
    
    With db.rs
        Do While .EOF <> True
            If !Modifier <> "" Then
                ComboBox_CO.AddItem !Component & ", " & !Modifier
                Else
                ComboBox_CO.AddItem !Component
            End If
            .MoveNext
        Loop
    End With
    ComboBox_CO.value = ComboBox_CO.list(0)
    
cleanup:
    On Error Resume Next
    db.rs.Close
    Exit Sub
errHandle:
    sendErrMsg "addCOManual.UserForm_Initialize"
    Resume cleanup
End Sub
