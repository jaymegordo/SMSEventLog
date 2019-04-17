VERSION 5.00
Begin {C62A69F0-16DC-11CE-9E98-00AA00574A4F} RefreshDateRange 
   Caption         =   "Select date range:"
   ClientHeight    =   4410
   ClientLeft      =   90
   ClientTop       =   366
   ClientWidth     =   3006
   OleObjectBlob   =   "RefreshDateRange.frx":0000
   StartUpPosition =   1  'CenterOwner
End
Attribute VB_Name = "RefreshDateRange"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = False
Attribute VB_PredeclaredId = True
Attribute VB_Exposed = False
Private Sub CommandButton_Cancel_Click()
    Unload Me
End Sub

Private Sub CommandButton_OK_Click()
    On Error GoTo errHandle
    Dim aDateLower As Date
    Dim aDateUpper As Date
    
    With TextBox_DateLower
        If IsDate(.value) Then
            aDateLower = .value
            Else
            MsgBox "DateLower must be a valid date!"
            .value = ""
            .SetFocus
            Exit Sub
        End If
    End With
    
    With TextBox_DateUpper
        If IsDate(.value) = False Then
            aDateUpper = Now
            Else
            aDateUpper = .value
        End If
    End With
    
    Unload Me
    RefreshTable "Dates", DateLower:=aDateLower, DateUpper:=aDateUpper
    
cleanup:
    On Error Resume Next
    Exit Sub
errHandle:
    sendErrMsg "RefreshDateRange_CommandButton_Ok_Click"
End Sub

Private Sub Week_Click()
    Unload Me
    RefreshTable "Dates", DateLower:=Now - 8
End Sub
Private Sub LastMonth_Click()
    Unload Me
    RefreshTable "Dates", DateLower:=Now - 31
End Sub

Private Sub All_Click()
    If iws = 9 Then
        Unload Me
        RefreshTable "All"
        Exit Sub
    End If
    answer = MsgBox("This will take 30-60s to refresh all database rows, depending on internet speed. If you're looking for a " _
            & "specific unit, use the 'Refresh by Unit' button." & dLine _
            & "Are you sure you wish to continue?", vbYesNo)
    
    If answer = vbYes Then
        Unload Me
        RefreshTable "All"
        Else
        Unload Me
        End
    End If
End Sub
Private Sub userform_initialize()
    On Error GoTo errHandle
    centerUserform Me
    iws = getWSInt(ActiveSheet.CodeName)
    TextBox_DateLower.value = Format(DateValue(Month(DateAdd("m", -1, Now)) & "/1/" & Year(DateAdd("m", -1, Now))), "yyyy-mm-dd")
    Exit Sub
errHandle:
    sendErrMsg "RefreshDateRange_initialize"
End Sub
