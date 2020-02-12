VERSION 5.00
Begin {C62A69F0-16DC-11CE-9E98-00AA00574A4F} CustomFC 
   Caption         =   "Create Custom FC"
   ClientHeight    =   3885
   ClientLeft      =   102
   ClientTop       =   378
   ClientWidth     =   5280
   OleObjectBlob   =   "CustomFC.frx":0000
   StartUpPosition =   1  'CenterOwner
End
Attribute VB_Name = "CustomFC"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = False
Attribute VB_PredeclaredId = True
Attribute VB_Exposed = False
Private Sub userform_initialize()
    centerUserform Me
    TextBox_ReleaseDate.value = Format(Now, getDateFormat)
    TextBox_ExpiryDate.value = Format(Now + 365, getDateFormat)
    TextBox_Classification = "FT"
End Sub
Private Sub CommandButton_Cancel_Click()
    Unload Me
    End
End Sub
Private Sub CommandButton_OK_Click()
    On Error GoTo errHandle
    
    With TextBox_FCNumber
        If .value = "" Then
            MsgBox "Please enter a custom FC Number."
            GoTo cleanup
            Else
            aFCNumber = .value
        End If
    End With
    
    With TextBox_Subject
        If .value = "" Then
            MsgBox "Please enter a subject."
            GoTo cleanup
            Else
            aSubject = .value
        End If
    End With
    
    With TextBox_Classification
        If .value = "" Then
            MsgBox "Please enter a type."
            GoTo cleanup
            Else
            aClassification = .value
        End If
    End With
    
    With TextBox_ReleaseDate
        If .value = "" Then
            MsgBox "Please enter a release date."
            GoTo cleanup
            ElseIf IsDate(.value) = False Then
                MsgBox "Must be valid date."
                .value = Format(Now, getDateFormat)
                .SetFocus
                Else
                aReleaseDate = DateValue(.value)
        End If
    End With
    
    With TextBox_ExpiryDate
        If .value = "" Then
            MsgBox "Please enter an expiry date."
            GoTo cleanup
            ElseIf IsDate(.value) = False Then
                MsgBox "Must be valid date."
                .value = Format(Now, getDateFormat)
                .SetFocus
                Else
                aExpiryDate = DateValue(.value)
        End If
    End With
    
cleanup:
    On Error Resume Next
    Unload Me
    Exit Sub
errHandle:
    sendErrMsg "commandbutton_ok_click"
    Resume cleanup
End Sub
