Attribute VB_Name = "PicsDLS_ImportFiles"
Option Compare Text
Sub ButtonPLM()
    PLM.Show
End Sub
Sub launchPLMReportGenerator()
    On Error GoTo errHandle
    Application.ScreenUpdating = False
    loadKeyVars 2, ActiveCell
    Set wb = Workbooks.Open("P:\Regional\SMS West Mining\Payload and Fault Analyzer\PLM Report Generator.xlsm", readOnly:=True)
    Set ws = wb.Worksheets("Report")
        
    With ws
        Debug.Print .Name
        .Cells(2, 2) = aUnit
        .Cells(2, 3) = aDate
    End With
    
cleanup:
    Application.ScreenUpdating = True
    Exit Sub
errHandle:
    sendErrMsg "launchPLMReportGenerator"
    Resume cleanup
End Sub
Sub importPLM()
    On Error GoTo errHandle
    Application.ScreenUpdating = False
    Dim fDialog As FileDialog
    Dim FolderPath As String
    Dim RowsAddedTotal As Long
    Dim vrtSelectedItem As Variant
    Dim VerPLM As Integer
    
    loadDB
    loadKeyVars 2, ActiveCell
    
    'Select haulcycle files
    FolderPath = getBasePath
    Set fDialog = Application.FileDialog(msoFileDialogFilePicker)
    With fDialog
        .AllowMultiSelect = True
        .InitialView = msoFileDialogViewDetails
        .Title = "Select PLM Report(s) for Import"
        .InitialFileName = FolderPath
    End With
        
    'Show the dialog, -1 means success
    If fDialog.Show <> -1 Then GoTo cleanup
    
    dbPath = "P:\Regional\SMS West Mining\Payload and Fault Analyzer\PLM Database.accdb"
    Set db2 = DAO.Workspaces(0).OpenDatabase(dbPath)
    Set rs = db2.OpenRecordset("PLM Database", dbOpenTable)
    rs.Index = "PrimaryKey"
    
    Set rs2 = db.OpenRecordset("UnitID", dbOpenTable)
    rs2.Index = "Unit"

    For Each vrtSelectedItem In fDialog.SelectedItems
        aFile = vrtSelectedItem
        Set wb = Workbooks.Open(vrtSelectedItem, readOnly:=True)
        Set ws = wb.Sheets(1)

        aUnit = Trim(Right(ws.Range("A2"), 5))
        Debug.Print "UnitCheck: " & aUnit
        
checkUnit:
        With rs2
            .Seek "=", aUnit
            If .NoMatch = False Then
                VerPLM = !VerPLM
                Else
                aUnit = InputBox("Could not get unit number for Unit: '" & aUnit & "'. Please enter:", "Unit Number", "")
                GoTo checkUnit
CheckVerPLM:
                If IsNumeric(VerPLM) = False Then
                    VerPLM = InputBox("Could not get PLM version from database. Please ensure Unit and PLM Version have been added to UnitID table.")
                    GoTo CheckVerPLM
                End If
            End If
        End With

        'Launch main plm import function
        RowsAddedTotal = PLM_Import(aFile, aUnit, ws, VerPLM) + RowsAddedTotal

next_file:
        wb.Close False
    Next vrtSelectedItem
    
    MsgBox "Haulcycle records added to PLM database: " & RowsAddedTotal
    
cleanup:
    cleanupDB
    closeDB
    Set FSO = Nothing
    Set folder = Nothing
    Set subfolders = Nothing
    Exit Sub
errHandle:
    sendErrMsg ErrMsg:="importPLM"
    Resume cleanup
End Sub

Function PLM_Import(aFile, aUnit, ws, VerPLM As Integer) As Long
    On Error GoTo errHandle
    Dim Conv As Double
    Dim dpCount As Integer
            
    Debug.Print "PLM Function Recieving Unit: " & aUnit
    Debug.Print "PLM Function Recieving ws: " & ws.Name
    
    LastRow = ws.Cells(ws.Rows.Count, "K").End(xlUp).row
    
    Select Case VerPLM
        Case 4
            Set Destination = Range("B12:AW" & LastRow)
            aArray = Destination.value
            
            With rs
                beforecount = .RecordCount
                For i = 1 To UBound(aArray, 1)
                    aDate = CDate(aArray(i, 1))
                    aTime = CDate(aArray(i, 2))
                    aPayload = aArray(i, 3)
                    .Seek "=", aUnit, aDate, aTime, aPayload
                    If .NoMatch = True Then
                        .AddNew
                        !Unit = aUnit
                        !Date = aDate
                        !Time = aTime
                        !Payload = aPayload
                        !Swingloads = aArray(i, 4)
                        !StatusFlag = aArray(i, 6)
                        !CarryBack = aArray(i, 7)
                        !TotalCycleTime = CDate(aArray(i, 8))
                        !LHaulDistance = aArray(i, 17)
                        !LMaxSpeed = aArray(i, 19)
                        !EMaxSpeed = aArray(i, 21)
                        !MaxSprung = aArray(i, 27)
                        !TruckType = aArray(i, 32)
                        !TareSprungWeight = aArray(i, 38)
                        !PayloadEstShovel = aArray(i, 42)
                        !QuickPayloadEst = aArray(i, 43)
                        !GrossPayload = aArray(i, 46)
                        .Update
                    End If
Next_record_4:
                Next i
                rowsadded = .RecordCount - beforecount
            End With
                    
        Case 3
            Set Destination = Range("B9:AU" & LastRow)
            aArray = Destination.value
            
            'Convert date to "mm/dd/yyyy" if it contains /
            If aArray(2, 1) Like "*/*" Then
                For i = 1 To UBound(aArray, 1)
                    TD = aArray(i, 1)
                    aArray(i, 1) = Mid(TD, InStr(1, TD, "/", vbTextCompare) + 1, InStr(4, TD, "/", vbTextCompare) _
                                    - InStr(1, TD, "/", vbTextCompare) - 1) & "/" & Mid(TD, 1, InStr(1, TD, "/", vbTextCompare) - 1) _
                                    & "/" & Right(TD, 4)
                Next i
            End If

            'Convert short or long tons to metric
            PayloadUnits = ws.Cells(3, 2)

            Select Case PayloadUnits
                Case "Short Tons"
                    Conv = 0.907185
                Case "Long Tons"
                    Conv = 1.01605
                Case Else
                    Conv = 1
            End Select
            
            With rs
                beforecount = .RecordCount
                For i = 1 To UBound(aArray, 1)
                    aDate = CDate(aArray(i, 1))
                    aTime = CDate(aArray(i, 2))
                    aPayload = Round(aArray(i, 3) * Conv, 1)
                    .Seek "=", aUnit, aDate, aTime, aPayload
                    If .NoMatch = True Then
                        .AddNew
                        !Unit = aUnit
                        !Date = aDate
                        !Time = aTime
                        !Payload = aPayload
                        !Swingloads = aArray(i, 4)
                        !StatusFlag = aArray(i, 6)
                        !CarryBack = Round(aArray(i, 7) * Conv, 1)
                        !TotalCycleTime = CDate(aArray(i, 8))
                        !LHaulDistance = aArray(i, 17)
                        !LMaxSpeed = aArray(i, 19)
                        !EMaxSpeed = aArray(i, 21)
                        !MaxSprung = Round(aArray(i, 27) * Conv, 1)
                        !TruckType = aArray(i, 32)
                        !TareSprungWeight = Round(aArray(i, 37) * Conv, 1)
                        !PayloadEstShovel = Round(aArray(i, 41) * Conv, 1)
                        !QuickPayloadEst = Round(aArray(i, 42) * Conv, 1)
                        !GrossPayload = Round(aArray(i, 46) * Conv, 1)
                        .Update
                    End If
Next_record_3:
                Next i
                rowsadded = .RecordCount - beforecount
            End With
        End Select
        
        PLM_Import = rowsadded

cleanup:
    Erase aArray
    Debug.Print "Duplicates skipped: " & dpCount
    Exit Function
errHandle:
    If Err.Number = 3022 Then 'Duplicate records > probably dont need this now cause using index/match
        dpCount = dpCount + 1
        Select Case VerPLM
            Case 4
                Resume Next_record_4
            Case 3
                Resume Next_record_3
        End Select
    End If
    
    sendErrMsg ErrMsg:="plmImport | " & aFile

End Function

