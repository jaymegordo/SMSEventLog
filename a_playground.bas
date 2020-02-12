Attribute VB_Name = "a_playground"

Dim Query As String
'Provider=MSOLEDBSQL
'Driver={ODBC Driver 13 for SQL Server}


Sub testUser()
    Dim wbe As New cwbExport
    wbe.ExportAllModules "\\Mac\Dropbox\Software\VBA Projects"
    
    
    
End Sub
Sub testDates()
    
    Dim a As Date
    Dim pLastTime As Date
    
    a = Now
    pLastTime = Now - TimeValue("00:36:00")
    
    
    Debug.Print DateDiff("n", a, pLastTime)
    
    
End Sub

Sub testConns()
    Dim db As cDB
    If Not collConns Is Nothing Then
        For Each db In collConns
            Debug.Print "Conn state", db.conn.State, "rs state", db.rs.State, db.rs.Source
        Next
    End If
End Sub
Sub TearDownRecords()
    On Error GoTo errHandle
    Dim db As cDB
    If Not collConns Is Nothing Then
        For Each db In collConns
            If db.rs.State = 1 Then db.rs.Close
        Next
        Set collConns = Nothing
    End If
    
cleanup:
    On Error Resume Next
    Exit Sub
errHandle:
    sendErrMsg "TearDownRecords"
    Resume cleanup
End Sub

Sub testrs()
    Query = "Select Notes From FactoryCampaign Where Unit='F301' And FCNumber='17H023-1B'"

    Dim db As New cDB
    db.OpenConn
    db.rs.Open Query, db.conn, adOpenStatic, adLockOptimistic
    
    'Debug.Print db.rs.RecordCount
    db.printRs
    
    
End Sub
Sub testUpdates()
    Dim e As cEvent
    Set e = createEventTable(ActiveCell)
    
    Debug.Print e.Description
    
End Sub

Sub testFilter()
    Dim f As New cFilter
    f.add "UnitID.MineSite=", getMineSite(True)
    f.add "UnitID.Unit=", "F303"
    f.add "Model=", "980E"
    
    
    Debug.Print f.Contains("Unit")
    
    
End Sub

Sub sompTest()
    sField = "Unit='F303'"
    sCheck = "Unit"
    Debug.Print sField Like "*" & sCheck & "*"
End Sub

Sub testTblWidth()
    Dim tbl As ListObject
    Set tbl = ActiveSheet.ListObjects(1)
    Dim rng As Range
    For i = 1 To tbl.ListColumns.Count
         Set rng = tbl.ListColumns(i).Range
         If Not rng.EntireColumn.Hidden Then tblWidth = tblWidth + rng.width
    Next
    Debug.Print tblWidth
    Debug.Print Application.ActiveWindow.width
End Sub

Sub copyFC2()
    Application.ScreenUpdating = False
    Dim wbe As New cwbExport
    With wbe
        .createWb "FC Summary - OSB.xlsm"
        .addWs Sheet7 'Details
        .addWs Sheet8 'Summary
        .wbDest.Sheets(1).visible = False
        
        .ws(1).Shapes(1).visible = msoFalse
        .ws(2).Shapes(2).visible = msoFalse
        .ws(2).Shapes(1).GroupItems(1).OnAction = "'" & .wbDest.Name & "'!expandCollapseCols"
        .ws(2).Shapes(1).GroupItems(2).OnAction = "'" & .wbDest.Name & "'!expandCollapseRows"
        .ws(1).ListObjects(1).HeaderRowRange.Font.ColorIndex = 2
        .ws(2).ListObjects(1).HeaderRowRange.Font.ColorIndex = 2
        .CopyModule "Functions"
        '.wbDest.Close True
    End With
End Sub

Sub copyFC()
    Dim wb As Workbook
    Dim ws As Worksheet
    Set wb = ThisWorkbook
    Dim wbn As Workbook
    Dim wsn As Worksheet
    Set wbn = Workbooks.add
    sFileName = Environ$("UserProfile") & "\Desktop\FC Summary.xlsm"
    wbn.SaveAs fileName:=sFileName, FileFormat:=xlOpenXMLWorkbookMacroEnabled
    Application.ScreenUpdating = False
    
    'FC Details
    Set ws = Sheet7
    ws.Copy After:=wbn.Sheets(1)
    Set wsn = wbn.Worksheets("FC Details")
    wsn.Shapes(1).visible = msoFalse
    wsn.ListObjects(1).HeaderRowRange.Font.ColorIndex = 2
    
    'FC Summary
    Set ws = Sheet8
    ws.Copy After:=wbn.Sheets(1)
    Set wsn = wbn.Worksheets("FC Summary")
    wsn.Shapes(2).visible = msoFalse
    wsn.ListObjects(1).HeaderRowRange.Font.ColorIndex = 2
    
    wbn.Worksheets("Sheet1").visible = False
    
    'Copy colour theme to new wb
    Dim TempThemeFile As String
    Dim sourceTheme As Object
    Set sourceTheme = wb.Theme.ThemeColorScheme
    TempThemeFile = Environ$("temp") & "\xltheme" & Format(Now, "dd-mm-yy h-mm-ss") & ".xml"
    sourceTheme.Save TempThemeFile
    wbn.Theme.ThemeColorScheme.Load TempThemeFile
    Kill TempThemeFile
    
End Sub

Function swapMonthDay()
    Dim rng As Range
    Set rng = Selection
    Dim cel As Range
    For Each cel In rng
        sDate = Format(cel, "mm-dd-yyyy")
        fixdate = DateValue(Mid(sDate, 4, 2) & "-" & Left(sDate, 2) & "-" & Right(sDate, 4))
        cel.value = fixdate
    Next
End Function
Sub ttt()
    Dim e As cEvent
    Set e = createEventTable(ActiveCell)
    e.tbl.ListColumns(13).Range.NumberFormat = getDateFormat
    
End Sub
Sub tt()
    'Replacing all old file folder names
    Dim e As cEvent
    Dim ef As cEventFolder
    Dim rsTest As DAO.Recordset
    loadDB
    Dim aa As Long
    aa = 0
    Query = "SELECT EventLog.UID, EventLog.Unit, EventLog.DateAdded, EventLog.WorkOrder, EventLog.Title, EventLog.FilePath " _
            & "FROM EventLog INNER JOIN UnitID ON EventLog.Unit = UnitID.Unit " _
            & "WHERE (((UnitID.MineSite)='FortHills') And CreatedBy<>'Cummins' And FilePath Is Not Null) " _
            & "ORDER BY EventLog.Unit, EventLog.DateAdded"
    Set rsTest = db.OpenRecordset(Query, dbOpenDynaset)
    With rsTest
        .MoveLast
        .MoveFirst
'        Debug.Print .RecordCount

        Do While .EOF <> True
            aa = aa + 1
            If CLng(Right(!Unit, 3)) < 324 Then GoTo skip:
            Set e = New cEvent
            e.UID = !UID
            e.Unit = !Unit
            e.DateEvent = !DateAdded
            If Not IsNull(!WorkOrder) Then e.WorkOrder = !WorkOrder
            e.Title = !Title
            
            Set ef = New cEventFolder
            ef.init e:=e
            ef.PrintVars
            DoEvents
            'If aa > 10 Then Exit Do
skip:
            .MoveNext
        Loop
        .Close
    End With
    Set rsTest = Nothing
    
End Sub

