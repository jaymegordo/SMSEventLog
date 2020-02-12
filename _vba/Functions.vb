Public SubName As String


Sub checkDropbox()
    On Error GoTo errHandle
    If getRemoteServer = True Then
        If IsProcessRunning("Dropbox.exe") = False Then Err.Raise 69420, Description:="Dropbox not running on remote server."
    End If
Exit Sub
errHandle:
    If Err.Number = 5 Then
        Slack.sendMessage "Error: Dropbox not running on remote server."
        Shell ("C:\Program Files (x86)\Dropbox\Client\Dropbox.exe")
        Exit Sub
    End If
    sendErrMsg "checkDropbox"
End Sub

Sub CleanupRS()
    On Error Resume Next
    rs.Close
    Set rs = Nothing
End Sub

Function ClearFilter(tbl)
    On Error Resume Next
    With tbl
        If .AutoFilter Is Nothing Then Exit Function
        If .AutoFilter.FilterMode = True Then
            .AutoFilter.ShowAllData
        End If
    End With
End Function

Function ClearTable(dbr)
    With dbr
        If .Rows.count > 1 Then
            .Offset(1, 0).Resize(.Rows.count - 1, .Columns.count).Rows.Delete
        End If
    End With
End Function

Function dLine() As String
    dLine = Chr(10) & Chr(10)
End Function

Function Encode(str As String) As String
    Encode = Application.WorksheetFunction.EncodeURL(str)
End Function

Function EncodeReplace(str As String) As String
    EncodeReplace = Encode(Replace(str, "~", Chr(34)))
End Function

Function getAltStatus(symbol As String) As Boolean
    On Error GoTo errHandle
    Query = "Select AltStatus From Symbols Where Symbol='" & symbol & "'"
    Dim db As New cDB
    db.OpenConn
    db.rs.Open Query, db.conn, adOpenForwardOnly, adLockReadOnly
    getAltStatus = db.rs!AltStatus
    db.rs.Close
    

cleanup:
    On Error Resume Next
    Exit Function
errHandle:
    sendErrMsg "getAltStatus"
    Resume cleanup
End Function

Function getCloseOnly() As Boolean
    setUserSettingsTable
    Dim rngCloseOnly As Range
    Set rngCloseOnly = dbr3.Cells(9, 2)
    getCloseOnly = rngCloseOnly
End Function

Function getContracts(xbt As Double, Leverage As Double, EntryPrice As Double, Side As Long, Optional IsAltcoin As Boolean = False) As Double
    Select Case IsAltcoin
        Case False
            getContracts = Round(xbt * Leverage * EntryPrice * Side, 0)
        Case True
            getContracts = Round(xbt * Leverage * (1 / EntryPrice) * Side, 0)
    End Select
End Function

Function getDatabasePath()
    On Error GoTo errHandle
'    aDatabase = "turtledatabase - working.accdb"
    aDatabase = "turtledatabase.accdb"

    aDatabasePath = Environ$("USERPROFILE") & "\Dropbox\Turtle\" & aDatabase
    If Not Dir(aDatabasePath, vbDirectory) = vbNullString Then
        getDatabasePath = aDatabasePath
        Exit Function
    End If
    
errHandle:
    sendErrMsg "getDatabasePath"
    End
End Function

Function getDecimal(IsAltcoin As Boolean) As Integer
    Select Case IsAltcoin
        Case False
            getDecimal = 0
        Case True
            getDecimal = 8
    End Select
End Function

Function getFundingString(Bitmex As cBitmex) As String
    On Error GoTo errHandle
    Dim aHours As Integer
    aFundingRate = Format(Bitmex.getFunding, "0.###%")
    aHours = (Bitmex.FundingTime - Now) * 24
    getFundingString = aFundingRate & " in " & aHours & " hr"
    
cleanup:
    Exit Function
errHandle:
    getFundingString = "can't get funding string"
    sendErrMsg "getFundingString"
    Resume cleanup
End Function

Function getFraction(n As Integer)
    Select Case n
        Case 1
            getFraction = (1 / 6)
        Case 2
            getFraction = (1 / 4.5)
        Case 3
            getFraction = (1 / 3.6)
        Case 4
            getFraction = (1 / 3)
        Case Else
            Err.Raise 444
    End Select
End Function

Function getManSpeed(aSide As String) As Integer
    setUserSettingsTable
    Dim ManSpeed As Range
    
    Select Case aSide
        Case "LongEnter"
            Set ManSpeed = dbr3.Cells(10, 2)
        Case "LongExit"
            Set ManSpeed = dbr3.Cells(11, 2)
        Case "ShortEnter"
            Set ManSpeed = dbr3.Cells(12, 2)
        Case "ShortExit"
            Set ManSpeed = dbr3.Cells(13, 2)
    End Select

    getManSpeed = ManSpeed
End Function

Function getManStopOn(Optional disableStop As Boolean = False) As Boolean
    setUserSettingsTable
    Dim rngManStopOn As Range
    Set rngManStopOn = dbr3.Cells(4, 2)
    
    Select Case disableStop
        Case False 'get
            getManStopOn = rngManStopOn
        Case True 'set
            rngManStopOn = False
            getManStopOn = False
    End Select
End Function

Function getManStopPrice(ByVal LongShort) As Long
    setUserSettingsTable
    Dim aManStopPrice As Range
    Select Case LongShort 'if short, get "price long" + vice versa
        Case 1
            Set aManStopPrice = dbr3.Cells(6, 2)
        Case -1
            Set aManStopPrice = dbr3.Cells(5, 2)
    End Select
    getManStopPrice = aManStopPrice
End Function

Function getNextTime(Optional fiveMin As Boolean = False)
        
    If fiveMin = True Then
        startTime = DateAdd("n", 1, Now)
        Do While Minute(startTime) Mod 5 <> 0
            startTime = DateAdd("n", 1, startTime)
        Loop
        getNextTime = TimeValue(hour(startTime) & ":" & Minute(startTime) & ":10")
        Exit Function
    End If
        
    If hour(Now) = 23 Then
        NextHour = 0
        Else
        NextHour = hour(Now) + 1
    End If
    getNextTime = TimeValue(NextHour & ":00:15")
End Function

Function getOrderPrice(AnchorPrice As Double, b As Integer, OrderSpread As Double, LongShort As Integer, EnterExit As Integer)
    getOrderPrice = Round(AnchorPrice * (1 + OrderSpread * (b - 1) * LongShort * EnterExit), aDec)
End Function

Function getPnl(aStatus, EntryPrice, ExitPrice) As Double
    On Error GoTo errHandle
    Select Case aStatus
        Case "Long", "Long-MR"
            getPnl = Round((ExitPrice - EntryPrice) / EntryPrice, 4)
        Case "Short", "Short-MR"
            getPnl = Round((EntryPrice - ExitPrice) / ExitPrice, 4)
    End Select
cleanup:
    Exit Function
errHandle:
    If Err.Number = 11 Then
        getPnl = 0
        Resume cleanup
    End If
    sendErrMsg "getPnl"
End Function

Function getPnlLongShort(LongShort, EntryPrice, ExitPrice) As Double
    On Error GoTo errHandle
    Select Case LongShort
        Case 1
            getPnlLongShort = Round((ExitPrice - EntryPrice) / EntryPrice, 4)
        Case -1
            getPnlLongShort = Round((EntryPrice - ExitPrice) / ExitPrice, 4)
    End Select
cleanup:
    Exit Function
errHandle:
    If Err.Number = 11 Then
        getPnlLongShort = 0
        Resume cleanup
    End If
    sendErrMsg "getPnl"
End Function

Function getPnlXBT(aContracts As Double, EntryPrice As Double, ExitPrice As Double, Optional IsAltcoin As Boolean = False) As Double
    On Error GoTo errHandle
    Select Case IsAltcoin
        Case False
            getPnlXBT = Round(aContracts * (1 / EntryPrice - 1 / ExitPrice), 8)
        Case True
            getPnlXBT = Round(aContracts * (ExitPrice - EntryPrice), 8)
    End Select
cleanup:
    Exit Function
errHandle:
    If aContracts = 0 Then getPnlXBT = 0
    Resume cleanup
End Function

Function getPrice(PnL, EntryPrice, Optional aLongShort) As Double
    On Error GoTo errHandle
    If IsMissing(aLongShort) Then aLongShort = LongShort
    Select Case aLongShort
        Case 1
            getPrice = PnL * EntryPrice + EntryPrice
        Case -1
            getPrice = EntryPrice / (1 + PnL)
    End Select
    Exit Function
errHandle:
    sendErrMsg "getPrice"
End Function

Function getPriceFormat(Optional AltStatus As Boolean = False, Optional WorksheetFormat As Boolean = False) As String
    Select Case AltStatus
        Case False
            getPriceFormat = "$#,###0"
        Case True
            If Not WorksheetFormat Then
                getPriceFormat = "0.000e+00"
                Else
                getPriceFormat = "0.000 E+00"
            End If
    End Select
End Function

Function getPriceFormatMil(aNum) As String
    If AltStatus = False Then dollarsign = "$"
    Select Case aNum
        Case Is > 1000000
            aFormat = "#,#,,.0M"
        Case Is > 1000
            aFormat = "#,#,.0K"
        Case Else
            aFormat = "#"
    End Select
    getPriceFormatMil = dollarsign & aFormat
End Function

Function getRemoteServer()
    If Environ$("computername") = "JaymeAzureRD1" Then
        getRemoteServer = True
        Else
        getRemoteServer = False
    End If
End Function

Function getRSUsers() As ADODB.Recordset
    On Error GoTo errHandle
    Dim db As New cDB
    db.OpenConn
    db.rs.Open "UserSettings", db.conn, adOpenStatic, adLockReadOnly, adCmdTable
    
    Set getRSUsers = db.rs
cleanup:
    Exit Function
errHandle:
    sendErrMsg "getRSUsers"
    Resume cleanup
End Function

Function getStopCloseOn() As Boolean
    setUserSettingsTable
    Dim rngStopCloseOn As Range
    Set rngStopCloseOn = dbr3.Cells(7, 2)
    getStopCloseOn = rngStopCloseOn
End Function

Function getStopClosePrice() As Long
    setUserSettingsTable
    Dim aStopClosePrice As Range
    Set aStopClosePrice = dbr3.Cells(8, 2)
    aStopClosePrice.Select
    getStopClosePrice = aStopClosePrice
End Function

Function getTable()
    getTable = "BTC_OHLC"
    'getTable = "BXBT_OHLC"
End Function

Function getTimeOffset()
    If getRemoteServer = True Then
        getTimeOffset = 0
        ElseIf (Environ$("Username")) = "jgordon" Then 'Alberta
            getTimeOffset = 6
            Else 'BC
            getTimeOffset = 7
    End If
End Function


Function getTradingLive() As Boolean
    'getTradingLive = False
    getTradingLive = True
End Function


Function isIso(strVal As String) As Boolean
    If Right(strVal, 1) = "Z" Then
        If Mid(strVal, 11, 1) = "T" Then
            isIso = True
            Exit Function
        End If
        Else
        isIso = False
    End If
End Function

Function IsProcessRunning(Process As String)
    Dim objList As Object

    Set objList = getObject("winmgmts:") _
        .ExecQuery("select * from win32_process where name='" & Process & "'")

    If objList.count > 0 Then
        IsProcessRunning = True
        Else
        IsProcessRunning = False
    End If
End Function

Sub jumpDate()
    
    aDate = InputBox("Enter date:")
    Dim Table As New cTbl
    With Table
        .init ws:=ActiveSheet
        aRow = .getIndex(CDate(aDate), "CloseTime")
        Debug.Print aRow
    End With
    
    Table.tbl.DataBodyRange.Cells(aRow, 1).Activate

End Sub

Sub jumpToDate()
    Set tbl = Sheet1.ListObjects(1)
    Set dbr = tbl.DataBodyRange
    aDate = InputBox("Input date:", "Find Date", Format(Now, "yyyy-mm-dd"))
    
    Dim aRng As Range
    Set aRng = tbl.ListColumns(1).DataBodyRange.find(aDate)
    aRng.Activate
End Sub

Sub killLockDB()
    On Error GoTo errHandle
    Application.Wait Now + TimeValue("00:00:03")
    Debug.Print "Killing db lock " & Now
    dbLockPath = Environ$("USERPROFILE") & "\Dropbox\Turtle\TurtleDatabase.laccdb"
    If Not Dir(dbLockPath, vbDirectory) = vbNullString Then kill dbLockPath 'db lock file exists

cleanup:
    Exit Sub
errHandle:
    If Err.Number = 70 Then
        sendErrMsg "Can't delete db lock file."
        Resume cleanup
    End If
    sendErrMsg "killLockDB"
    Resume cleanup
End Sub

Function Line() As String
    Line = Chr(10)
End Function

Function parseTimestamp(aTimeStamp As String) As Date
    aTimeStamp = Replace(aTimeStamp, "T", " ")
    parseTimestamp = Replace(aTimeStamp, ".000Z", "")
End Function

Sub populateCombobox(aBox As ComboBox, Optional aCol As ListColumn, _
                    Optional rs As Object, Optional field As Variant, Optional closeRs As Boolean = True)
    'Easily load a useform combo box from a table listcolumn
    With aBox
        .Clear
        If Not aCol Is Nothing Then 'load from a listcolumn
            For i = 2 To aCol.Range.Rows.count
                .AddItem aCol.Range(i).Value
            Next i
            .Value = aCol.Range(2).Value
            
            ElseIf Not IsMissing(rs) Then
                If IsMissing(field) Then field = 0
                With rs
                    Do While .EOF <> True
                        aBox.AddItem .Fields(field).Value
                        .MoveNext
                    Loop
                    If closeRs Then .Close
                End With
        End If

    End With
End Sub

Sub populateListBox(aBox As MSForms.ListBox, aCol As ListColumn, Optional SelectAll As Boolean = False)
    With aBox
        For i = 2 To aCol.Range.Rows.count
            .AddItem aCol.Range(i).Value
        Next i
        
        If SelectAll Then
            For i = 0 To .ListCount - 1
                If .list(i) <> "Closed" Then .Selected(i) = True
            Next i
        End If
    End With
End Sub

Function PRNT(Optional Name As String, Optional aValue)
    On Error GoTo errHandle
    If getRemoteServer <> True Then
        If IsMissing(aValue) = False Then
            Debug.Print Name, aValue
            Else
            Debug.Print Name
        End If
    End If
    Exit Function
errHandle:
    sendErrMsg "PRNT - " & Name
End Function

Function readTextFile(myFile As String) As String
    Open myFile For Input As #1
    Do Until EOF(1)
        Line Input #1, textline
        Text = Text & textline
    Loop
    Close #1
    readTextFile = Text
End Function

Function sendErrMsg(Optional SubName)
    If Err.Number = 555 Then
'        displayResultsTable
        On Error GoTo 0
        Err.Raise 444
    End If
    aMessage = "Error: " & Err.Number & " | " & Err.Description & " | " & SubName
    Err.Clear
    Debug.Print aMessage
    If getRemoteServer = True Then Discord.sendMessage ch.Jambot, aMessage
End Function

Sub setUserSettingsTable()
    If tbl3 Is Nothing Then
        Set tbl3 = Sheet6.ListObjects("SettingsTable")
        Set dbr3 = tbl3.DataBodyRange
    End If
End Sub

Function strStatus(Status As Long) As String
    Select Case Status
        Case 2
            strStatus = "Long-MR"
        Case 1
            strStatus = "Long"
        Case 0
            strStatus = "Neutral"
        Case -1
            strStatus = "Short"
        Case -2
            strStatus = "Short-MR"
    End Select
End Function

Sub timeSub(s As String)
    'time any sub with ' timeSub "TestSubName" '
    Dim sw As cStopWatch
    Set sw = New cStopWatch
    sw.StartTimer
    
    Application.Run s
    
    sw.printTimer
End Sub

Sub tre()
    aNum = 200
    Debug.Print Format(aNum, getPriceFormatMil(aNum))
End Sub

Function getExtremum(arrDS() As Variant, MaxMin As Integer, Size As Integer, StartRow As Long, aCol As Integer) As Double
   On Error GoTo errHandle
    ReDim arrPeriods(1 To Size) As Double
    
    For y = 1 To UBound(arrPeriods)
        arrPeriods(y) = arrDS(StartRow - Size + y - 1, aCol)
    Next y
    
    Select Case MaxMin
        Case 1
            getExtremum = Application.WorksheetFunction.Max(arrPeriods)
        Case -1
            getExtremum = Application.WorksheetFunction.min(arrPeriods)
    End Select
    
cleanup:
    Exit Function
errHandle:
    sendErrMsg "getExtremum"
    Resume cleanup
End Function
Function getFraction(n As Integer)
    Select Case n
        Case 1
            getFraction = (1 / 6)
        Case 2
            getFraction = (1 / 4.5)
        Case 3
            getFraction = (1 / 3.6)
        Case 4
            getFraction = (1 / 3)
        Case Else
            Err.Raise 444
    End Select
End Function