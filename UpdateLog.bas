Attribute VB_Name = "UpdateLog"
Sub Auto_Open()
    refreshTablesOnOpen
End Sub
Sub test()
    Update
End Sub
Sub pushUpdate()
Attribute pushUpdate.VB_ProcData.VB_Invoke_Func = "P\n14"
    ans = MsgBox("Would you like to push an updated Event Log?" & dLine & "Current version: " _
                & getVer, vbQuestion + vbYesNo, "Manual Update")
    If ans <> vbYes Then Exit Sub
    Update True
    MsgBox "Update successfully pushed."
End Sub
Sub updateMe()
    ans = MsgBox("Would you like to manually update to the latest version of the Event Log?" _
                & dLine & "*Note, even if the version number is the same, the newest version may contain some updates.", _
                vbQuestion + vbYesNo, "Manual Update")
    If ans <> vbYes Then Exit Sub
    Update getUpdate:=True
End Sub
Sub saveUpdate() 'just save this book to the update folder but don't push an update
Attribute saveUpdate.VB_ProcData.VB_Invoke_Func = "U\n14"
    ans = MsgBox("Would you like to save this version to the update folder?", vbQuestion + vbYesNo, "Save Update")
    If ans <> vbYes Then Exit Sub
    Update saveUpdate:=True
    MsgBox "File saved to update folder."
End Sub
Sub Update(Optional pushUpdate As Boolean = False, Optional getUpdate As Boolean = False, Optional saveUpdate As Boolean = False)
    On Error GoTo errHandle
    Application.ScreenUpdating = False
    Dim FSO As FileSystemObject
    Set FSO = CreateObject("Scripting.FileSystemObject")
    Dim aFileObj As Object 'Scripting.File
    Dim NewVer As Double
    Dim OldVer As Double
    Dim WBT As Workbook
    Set WBT = ThisWorkbook
    
    OldVer = CDbl(WBT.Sheets("Version").Cells(1, 1))
    
    If Not checkCummins Then
        aPath = "P:\Regional\SMS West Mining\SMS Event Log\Update"
        NewFile = aPath & "\SMS Event Log.xlsm"
        
        Else
        aPath = getCumminsPath & "\Update"
        NewFile = aPath & "\Cummins Event Log.xlsm"
    End If
    
    If pushUpdate Then
        NewVer = OldVer + 0.01
        Debug.Print "newVer", NewVer
        WBT.Sheets("Version").Cells(1, 1) = NewVer
    End If
    
    If pushUpdate Or saveUpdate Then
        WBT.Save
        FSO.CopyFile WBT.FullName, NewFile, True
        If saveUpdate Then GoTo cleanup
    End If
    
    Set aFolder = FSO.GetFolder(aPath)
    
    For Each aFileObj In aFolder.Files
        aName = aFileObj.Name
        If aName Like "v*.txt" Then
            
            If pushUpdate Then
                aFileObj.Name = "v" & CStr(NewVer) & ".txt"
                GoTo cleanup
            End If
            
            NewVer = CDbl(Mid(aName, 2, Len(aName) - 5))
            Exit For
        End If
    Next

    If Round(NewVer, 2) - Round(OldVer, 2) Or getUpdate Then
        answer = MsgBox("A new version of this file is available, would you like to update now?" & dLine _
                    & "Previous version: " & OldVer & Line & "New version: " & NewVer, vbYesNo)
        
        If answer = vbYes Then
            'read current user settings to save in new workbook
            Application.DisplayAlerts = False
            MineSite = getMineSite
            WriteMode = getWriteMode
            
            CurPath = WBT.FullName
            TempName = Mid(CurPath, 1, Len(CurPath) - 5) & "-OLD (delete this file).xlsm"
            WBT.SaveAs TempName
            
            Set wbn = Workbooks.Open(NewFile)
            Application.DisplayAlerts = False
            wbn.SaveAs CurPath
            Application.DisplayAlerts = True
            setUserSettings wbn, WriteMode, MineSite
            
            MsgBox "File successfully updated." & dLine & "Previous version: " & OldVer & Line & "New version: " & NewVer & dLine & "Please make sure you are set to the correct MineSite and refresh tables (ctrl+shift+R) if necessary!"
            Application.EnableEvents = False
            
            'Refresh email, event log, and work order tables to correct minesite
'            Application.Run ("'" & wbn.Name & "'!RefreshEmailTable")
'            Application.Run "'" & wbn.Name & "'!RefreshTable", , , 1
'            Application.Run "'" & wbn.Name & "'!RefreshTable", , , 2
            Application.Run "'" & wbn.Name & "'!killOldFileTimer", TempName ' pass location old file to close then kill
            WBT.Close False
            wbn.Activate
        End If
    End If
cleanup:
    On Error Resume Next
    Application.DisplayAlerts = True
    Application.EnableEvents = True
    Exit Sub
errHandle:
    sendErrMsg "Can't find update path. | UpdadeCheck"
    Resume cleanup
End Sub
Sub killOldFileTimer(aTempFile As String)
    On Error Resume Next
    'Debug.Print "killOldFileTimer: " & aTempFile
    Application.OnTime Now + TimeValue("00:00:10"), "'killOldFile """ & aTempFile & """' "
End Sub
Sub killOldFile(aTempFile As String)
    On Error Resume Next
    Debug.Print "killOldFile: " & aTempFile
    For Each wb In Application.Workbooks
        If wb.Name Like "*OLD*" Then
            Debug.Print "Closing wb: " & wb.Name
            wb.Close False
            Exit For
        End If
    Next
    DoEvents
    Kill aTempFile
End Sub
Sub setVer()
    ThisWorkbook.Sheets("Version").Cells(1, 1) = 1.37
End Sub
Function getVer()
    getVer = ThisWorkbook.Sheets("Version").Cells(1, 1)
End Function

Sub setUserSettings(wbn, WriteMode, MineSite)
    With wbn.Sheets("Event Log")
        .Range("H1") = WriteMode
        .Range("MineSite") = MineSite
    End With
End Sub
Sub refreshTablesOnOpen()
    On Error GoTo errHandle
'    ans = MsgBox("Would you like to refresh EventLog and WorkOrder tables now?", vbYesNo, "Refresh Tables?")
    
'    If ans = vbYes Then
        RefreshTable RefreshType:="AllOpen", iws:=1
        RefreshTable RefreshType:="AllOpen", iws:=2
        'MsgBox "Tables refreshed."
'    End If
    
    Exit Sub
errHandle:
    sendErrMsg "refreshTablesOnOpen"
End Sub
