Public Discord As New cDiscord
Public Account As cAccount
Public SymSave As cSymBacktest
Public collSyms As Collection
Public collUsers As Collection
Public oSymbol As cSymbol
Public oUser As cUser
Public curUser As cUser

Sub launchTurtle()
    On Error GoTo errHandle
    aMessageFinal = ""
    Dim strQuery As String
    Dim i As Integer
    Dim y As Integer
    Dim Sym As cSymBacktest
    Dim User As cUser
    Dim Bitmex As cBitmex
    Dim rsUser As ADODB.Recordset
    Dim rsSym As ADODB.Recordset
    Dim collSyms As New Collection
    
    strQuery = "SELECT * WHERE M=True"
    
    Dim db As New cDB
    db.OpenConn
    db.rs.Open "Symbols", db.conn, adOpenStatic, adLockReadOnly, adCmdTable
    Set rsSym = db.rs
    
    Set collUsers = New Collection
    
    If getTradingLive Then
        'Get User % settings from google sheets
        Dim job As cJobject
        Set job = FastQuery(strQuery:=strQuery, iws:=5).find("table").clone
        aRows = job.find("rows").children.count
'        loopJson job, , True, "Tree"
'        End

        Set rsUser = getRSUsers

        With job.child("rows")
            For i = 1 To aRows
                Set User = New cUser
                User.NameShort = .children(i).child("c.1.v").Value
                User.PercentBalance = .children(i).child("c.4.v").Value
                User.gRow = i
                User.initFromDB rsUser
                
                'Set symbols for each user
                For y = 5 To 12
                    Set oSymbol = New cSymbol
                    oSymbol.NameSimple = job.find("cols").children(y).child("label").Value
                    oSymbol.PercentBalance = .children(i).child("c." & y & ".v").Value
                    
                    'Set full name from db
                    With rsSym
                        .Filter = "SymbolSimple='" & oSymbol.NameSimple & "'"
                        If .RecordCount = 1 Then
                            oSymbol.SymbolBitmex = !SymbolBitmex
                            oSymbol.DecimalFigs = !DecimalFigs
                            oSymbol.AltStatus = !AltStatus
                        End If
                    End With
                    
                    User.collSymbols.add oSymbol
                    
                Next y
                'User.printSymbols
                
                Set Bitmex = New cBitmex
                With Bitmex
                    Set .User = User
                    .getOpenPosition
                    .getOpenOrders
                    .getTotalBalance
                End With
                Set User.Bitmex = Bitmex
                collUsers.add User
                
            Next i
        End With
        
        rsSym.Filter = ""
        
        'Loop symbols enabled in DB >change to syms enabled on google sheet?
        With rsSym
            .MoveFirst
            Do While Not .EOF
                If !Enabled Then
                    Set Sym = New cSymBacktest
                    Sym.init CStr(!symbol), DateValue(Now - 90), CDbl(!modUp), CDbl(!modDown), _
                            , True, CBool(!P1Enabled), CBool(!P2Enabled), rsSym
                    Sym.DecideFull
                    Sym.Teardown
                    
                    checkSymbol Sym
                    
                    collSyms.add Sym
                End If
                
                .MoveNext
                DoEvents
            Loop
        End With
    End If
    
    Discord.sendMessage ch.Jambot, aMessageFinal
    
    writeUserBalanceGoogle collUsers, collSyms
    
cleanup:
    On Error Resume Next
    rsSym.Close
    
    Exit Sub
errHandle:
    sendErrMsg "launchTurtle"
    Resume cleanup
End Sub



Sub runAll()
    Dim i As Long
    Dim modUp As Double
    Dim modDown As Double
    Dim Sym As cSymBacktest
    Set collSyms = New Collection
    Set Account = New cAccount
    arrSym = Array("XBTUSD", ".BADAXBT", ".BXRPXBT", ".BEOSXBT", ".BBCHXBT", ".BETHXBT", ".BLTCXBT", ".TRXXBT")
    
    StartDate = #12/1/2018#
    modUp = 2
    modDown = 1
    MeanRevEnabled = False
    P1Enabled = True
    P2Enabled = False
    
    For Each symbol In arrSym
'        Account.reset
        Set Sym = New cSymBacktest
        Sym.init CStr(symbol), StartDate, modUp, modDown, MeanRevEnabled, , P1Enabled, P2Enabled, , 1 / UBound(arrSym)
        collSyms.add Sym
'        Debug.Print sym.StartRow, sym.LastRow
    Next
'    End
        For i = Sym.StartRow To Sym.LastRow
            For Each Sym In collSyms
                Sym.Decide i
            Next Sym
        Next i
        
        For Each Sym In collSyms
            Sym.Teardown
        Next Sym
        Debug.Print Account.Max, Account.Balance
        Account.printSummary
'        sym.printFinal
'        collSyms.add sym
'    Next
    
    
End Sub
Sub printEach()
    Dim Sym As cSymBacktest
    Set Sym = collSyms.Item(1)
    Debug.Print Sym.curTrade(1).PnLCurrent
End Sub

Sub checkSymbol(Sym As cSymBacktest)
    On Error GoTo errHandle
    FinalStatus = strStatus(Sym.Status(1))
    Dim oTrade As cTrade
    Set oTrade = Sym.Trade(Sym.TradeCount(1), 1)
    
'    'MeanRev stuff
'    ClosedTrades = ClosedTrades + 1 'Once current trade closes
'    arrPnl(ClosedTrades, 2) = getPnl(PrevStatus, EntryPrice, getFinalPrice(bypassManualStop:=True))
'    If arrPnl(ClosedTrades, 2) > 0.05 And MeanRevEnabled Then MeanRevNext = True
'    If Sym.Status = 2 Or Sym.Status = -2 Then MeanRevCurrent = True  'put this in cSymBacktest

    'Check if trade just exited
    If oTrade.ExitDate = Sym.curCandle.TimeStamp Then
        aMessage = Sym.SymbolShort & ": " & "**Exit " & strStatus(oTrade.Status) & "** (from " _
                    & Format(oTrade.EntryPrice, getPriceFormat(Sym.AltStatus)) & ", PnL: " & Format(oTrade.PnLFinal, "Percent") & ")" _
                    & " | **Entered " & FinalStatus & "** at: " & Format(Sym.curTrade(1).EntryPrice, getPriceFormat(Sym.AltStatus))
        Discord.sendMessage ch.Orders, aMessage
    End If
    
    'Adjust stops for each user
    For Each oUser In collUsers
        checkOrders oUser, Sym
    Next
    
    If Not Sym.AltStatus Then strFunding = " | " & getFundingString(getUser("Jayme").Bitmex)

    aMessageFinal = aMessageFinal & "[" & Sym.SymbolShort & "](" & Sym.UrlShort & "): **" _
                        & Format(Sym.curTrade(1).PnLCurrent, "Percent") & "** | " _
                        & FinalStatus & " from " & Format(Sym.curTrade(1).EntryPrice, getPriceFormat(Sym.AltStatus)) _
                        & " | C: " & Format(Sym.curCandle.Clse, getPriceFormat(Sym.AltStatus)) _
                        & " \n " & getTradeSwitch(Sym) _
                        & strFunding _
                        & " | ema: " & getEmaConfidence(Sym.curCandle.ema200, Sym.curCandle.ema50, Sym) _
                        & Sym.UserMsg _
                        & " \n"
cleanup:
    On Error Resume Next
    Exit Sub
errHandle:
    sendErrMsg "checkSymbol"
    Resume cleanup
End Sub

Sub checkOrders(User As cUser, Sym As cSymBacktest)
    On Error GoTo errHandle
    Dim symbol As cSymbol
    Set symbol = User.getSymbol(Sym.SymbolBitmex)
    
    With symbol
        If .PercentBalance = 0 And .hasOrder(StopBuy) Then 'Cancel Orders
            User.Bitmex.CancelOrder "Single", .Order(StopBuy).OrderID
            Discord.sendMessage ch.Orders, "x-x-x-x-x-x **Canceled Order**: " & User.Name & " | " _
                                            & .NameSimple & ", " & .Order(StopBuy).ClOrdID
        End If
        
        If .PercentBalance > 0 Then
            .Confidence = getEmaConfidence(Sym.curCandle.ema200, Sym.curCandle.ema50, Sym)
            .StopPx = Sym.nextStopPx
            .LongShort = Sym.Side(1) 'LongShort is current side of current position > set stops with opposite side
            .EmaActive = Sym.EmaActive
            User.Bitmex.amendStopLimit symbol
        End If

        If .AvgEntryPrice <> 0 Then
            Sym.UserMsg = "\n           " & User.NameShort & ": (" & Format(.AvgEntryPrice, getPriceFormat(Sym.AltStatus)) & ", " _
                        & Round(.MaintMargin, 3) & ", " & Format(.UnrealizedPnlPcnt, "Percent") _
                        & ", " & Format(.UnrealizedRoePcnt, "Percent") & ", **" & Format(.UnrealizedPnl, "0.000") & "**)"
        End If
    End With

cleanup:
    On Error Resume Next
    Exit Sub
errHandle:
    sendErrMsg "checkOrders"
    Resume cleanup
End Sub

Sub Turtle_Timer_5Min()
    On Error GoTo errHandle
    check5MinVol
    checkOrders5Min
    On Error Resume Next
    Application.OnTime TimeValue(getNextTime(True)), "Turtle_Timer_5Min", schedule:=False
    On Error GoTo errHandle
    Application.OnTime TimeValue(getNextTime(True)), "Turtle_Timer_5Min" '& Chr(34) & NextTimeDate & Chr(34) & "'"
cleanup:
    Exit Sub
errHandle:
    sendErrMsg "Turtle_Timer_5Min"
End Sub

Function loadArray(StartDate As Date, interval, symbol As String, _
                    Optional EndDate, Optional Table As String = "Bitmex_OHLC") As Variant
    On Error GoTo errHandle
    Dim Cols As Long
    Cols = 28
    Dim aArray() As Variant
    Dim Query As String
    
    If Not StopRefreshDB Then refreshCandles symbol 'stoprefresh not used?
    
    'Add EndDate into query
    If IsMissing(EndDate) = False Then EndDateLimit = "AND CloseTime <='" & EndDate & "' "

    Query = "SELECT Round(CAST(CONVERT(datetime, CloseTime) as float),6) + 2, [Open], High, Low, [Close], VolBTC FROM " & Table _
            & " WHERE Interval = " & interval & " AND Symbol='" & symbol & "'" _
            & " AND CloseTime >='" & StartDate & "' " & EndDateLimit & "ORDER BY CloseTime"
    
    Dim db As New cDB
    db.OpenConn
    db.rs.Open Query, db.conn, adOpenStatic, adLockReadOnly
    
    loadArray = db.DS(Cols)

cleanup:
    On Error Resume Next
    db.rs.Close
    Exit Function
errHandle:
    sendErrMsg "LoadArray"
    Resume cleanup
End Function
Function getUser(sUser As String) As cUser
    On Error GoTo errHandle
    For Each oUser In collUsers
        If oUser.Name = sUser And oUser.isInit Then
            Set getUser = oUser
            Exit For
        End If
    Next
cleanup:
    On Error Resume Next
    Exit Function
errHandle:
    sendErrMsg "getUser"
    Resume cleanup
End Function
Sub checkOrders5Min() 'Need to fix this global user thing
    On Error GoTo errHandle
    Dim aMsg As String
    aMsg = "Filled: \n "
    Dim startTime As Date
    startTime = UtcConverter.ConvertToUtc(DateAdd("n", -5, Now))
    Dim job As cJobject
    Dim User As cUser
    
    'loop Users
    If Not collUsers Is Nothing Then
        Set User = getUser("Jayme")
        Else
        Set collUsers = New Collection
    End If
    
    If User Is Nothing Then
        Debug.Print "Setting new user -" & Now
        Set User = New cUser
        User.NameShort = "Ja"
        User.initFromDB getRSUsers
        Set User.Bitmex.User = User
        collUsers.add User
    End If
    
    Set job = User.Bitmex.getFilledOrders(startTime:=startTime)

    
    If job.children.count < 1 Then GoTo cleanup
    User.clearOrders
    User.addOrders job

    Dim oOrder As cOrder
    With User.collFilledOrders
        For i = 1 To .count
            Set oOrder = .Item(i)
            aMsg = aMsg & "         " _
                        & Left(oOrder.symbol, 3) _
                        & ": **" & Format(oOrder.OrderQty, "#,###") & "** at " _
                        & oOrder.Price & " \n "
        Next i
    End With
    

    Discord.sendMessage ch.Orders, aMsg
    
cleanup:
    Exit Sub
errHandle:
    sendErrMsg "checkOrders5Min"
    Resume cleanup
End Sub
Sub check5MinVol()
    On Error GoTo errHandle
    aPeriods = 9 '1.5hrs
    Dim aMessageVolume As String
    
    TimeOffset = -1 * 5 * aPeriods
    MaxDate = DateAdd("n", TimeOffset, UtcConverter.ConvertToUtc(Now))
    
    arrSymbols = Array("XBTUSD", "ADAU19", "XRPU19", "EOSU19", "TRXU19", "LTCU19", "BCHU19", "ETHU19") 'make this load from DB only when empty? >yes
    Dim collSymCandles As New Collection
    Dim oSymCandle As cSymCandle
    For i = 0 To UBound(arrSymbols)
        Set oSymCandle = New cSymCandle
        oSymCandle.Name = arrSymbols(i)
        collSymCandles.add oSymCandle
        strFilter = strFilter & "~" & arrSymbols(i) & "~,"
    Next i
    strFilter = Left(strFilter, Len(strFilter) - 1)
    
    strBase = "https://www.bitmex.com/api/v1/trade/bucketed?binSize=5m&partial=false&reverse=false"
    strFilter = "&filter=" & EncodeReplace("{~symbol~:[" & strFilter & "]}")
    strColumns = "&columns=" & EncodeReplace("[~open~,~high~,~low~,~close~,~volume~]")
    strDate = "&startTime=" & EncodeReplace(Format(MaxDate, "yyyy-mm-dd hh:mm:00"))
    
    strRequest = strBase & strFilter & strColumns & strDate
    'Debug.Print strRequest
    
    Set MyRequest = CreateObject("WinHttp.WinHttpRequest.5.1")
    MyRequest.Open "GET", strRequest
    MyRequest.send
    
    response = MyRequest.responseText
    response = "{""result"":" & response & "}"
    'Debug.Print response
    
    Set json = JsonConverter.ParseJson(response)
    NumCandleResult = json("result").count
    'PRNT "NumCandleResult", NumCandleResult

    Dim oCandle As cCandle
    Dim curCandle As cCandle
    Dim curSymCandle As cSymCandle
    
    For i = 1 To NumCandleResult
        For Each oSymCandle In collSymCandles
            With oSymCandle
                If .Name = json("result")(i)("symbol") Then
                    Set oCandle = New cCandle
                    With oCandle
                        .TimeStamp = JsonConverter.ParseIso(CStr(json("result")(i)("timestamp")))
                        .Opn = json("result")(i)("open")
                        .High = json("result")(i)("high")
                        .Low = json("result")(i)("low")
                        .Clse = json("result")(i)("close")
                        .Vol = json("result")(i)("volume")
                    End With
                    .collCandles.add oCandle
                    Exit For
                End If
            End With
        Next
    Next i
    
    For Each oSymCandle In collSymCandles
        With oSymCandle
            If .NewestCandle.Vol > .AvgVolume * 10 And Abs(.NewestCandle.PercentOCd) > 0.001 Then
                aMessageVolume = aMessageVolume _
                            & "__" & Left(.Name, 3) & "__: " _
                            & .NewestCandle.PercentOC _
                            & " | **" & Format(.NewestCandle.Vol, getPriceFormatMil(.NewestCandle.Vol)) & "**" _
                            & " (aV: " & Format(.AvgVolume, getPriceFormatMil(.AvgVolume)) & ")" _
                            & " | H: " & Format(.NewestCandle.High, getPriceFormat(.AltStatus)) _
                            & " | L: " & Format(.NewestCandle.Low, getPriceFormat(.AltStatus)) _
                            & " | C: " & Format(.NewestCandle.Clse, getPriceFormat(.AltStatus)) & " \n"
            End If
        End With
    Next
    
    'Debug.Print aMessageVolume
    Discord.sendMessage ch.Vol, aMessageVolume

End Sub

Sub testRefreshCandles()
    refreshCandles ".BADAXBT"
End Sub
    
Sub refreshCandles(symbol As String)
    On Error GoTo errHandle
    Dim TimeStamp As Date
    aInterval = 1
    ReCount = 0
    NumCandles = 750
    EarliestDate = #12/1/2017#
    
    UTCTimeCurrent = UtcConverter.ConvertToUtc(Now)
            
    Query = "Select Top 1 * From Bitmex_OHLC " _
            & "Where Symbol='" & symbol & "' " _
            & "Order By CloseTime DESC"
    
    Dim db As New cDB
    db.OpenConn
    db.rs.Open Query, db.conn, adOpenStatic, adLockBatchOptimistic
    
    MaxDate = db.rs!CloseTime
    If IsNull(MaxDate) Then MaxDate = EarliestDate
    CheckDate = DateAdd("h", -1, UTCTimeCurrent)
'    db.rs.Close
    
    If MaxDate > CheckDate Then
'        Debug.Print "MaxDate > CheckDate - don't need to refresh"
        GoTo cleanup
        Else
        PRNT "MaxDate < CheckDate - refreshing table"
    End If
    
    'MaxDate = #1/1/2017#
    
    Do While MaxDate < UTCTimeCurrent
        PRNT "MaxDate", MaxDate
        strRequest = "https://www.bitmex.com/api/v1/trade/bucketed?binSize=1h&partial=false&symbol=" & symbol & "&columns=%5B%22open%22%2C%22high%22%2C%22low%22%2C%22close%22%2C%22" _
                    & "volume%22%5D&count=" & NumCandles & "&reverse=false&startTime=" & Format(MaxDate, "yyyy-mm-dd%20hh") & "%3A00%3A00"
        'Debug.Print strRequest ^could also url encode this
            
        Set MyRequest = CreateObject("WinHttp.WinHttpRequest.5.1")
        MyRequest.Open "GET", strRequest
        MyRequest.send
        response = MyRequest.responseText
        response = "{""result"":" & response & "}"
        'Debug.Print Response
        
        Set json = JsonConverter.ParseJson(response)
        NumCandleResult = json("result").count
        'PRNT "NumCandleResult", NumCandleResult
        
        With db.rs
            For i = 1 To NumCandleResult
                TimeStamp = parseTimestamp(CStr(json("result")(i)("timestamp")))
                
                If !CloseTime < TimeStamp Then
                    'Debug.Print "adding new", i
                    .AddNew
                    !symbol = symbol
                    !interval = aInterval
                    !CloseTime = TimeStamp
                    !Open = json("result")(i)("open")
                    !High = json("result")(i)("high")
                    !Low = json("result")(i)("low")
                    !Close = json("result")(i)("close")
                    !VolBTC = json("result")(i)("volume")
                    '.update
                    
                    RowsAdded = RowsAdded + 1
                    
                    Else
                    dpCount = dpCount + 1
                End If
            Next i
            .UpdateBatch
        End With

        PRNT "RowsAdded", RowsAdded
        PRNT "Duplicates skipped", dpCount
        DoEvents
        MaxDate = DateAdd("h", 750 - 1, MaxDate)
    Loop
    
cleanup:
    On Error Resume Next
    db.rs.Close
    ReCount = 0
    Exit Sub
errHandle:
    sendErrMsg "refreshCandles"
    Resume cleanup
End Sub


Sub displayPnlTables(Optional P1Enabled, Optional P2Enabled)
    'TradePnl table/chart
'    If P1Enabled = True Then
'        Set tbl2 = Sheet8.ListObjects(1)
'        Set dbr2 = tbl2.DataBodyRange
'        ClearTable dbr2
'        Set aRng2 = tbl2.Range.Resize(ClosedTrades + 1, dbr2.Columns.count)
'        tbl2.Resize aRng2
'        For i = 1 To ClosedTrades
'            If arrPnl(i, 2) > 0 Then GoodTrade = GoodTrade + 1
'        Next i
'        Dim aRng3 As Range
'        Set aRng3 = tbl2.DataBodyRange.Resize(ClosedTrades, dbr2.Columns.count - 2)
'        aRng3 = arrPnl
'
'        For y = 8 To 11
'            tbl2.ListColumns(y).DataBodyRange.NumberFormat = getPriceFormat(True)
'        Next y
'    End If
'
'    If P2Enabled = True Then
'        Set tbl2 = Sheet9.ListObjects(1)
'        Set dbr2 = tbl2.DataBodyRange
'        ClearTable dbr2
'        Set aRng2 = tbl2.Range.Resize(ClosedTrades2 + 1, dbr2.Columns.count)
'        tbl2.Resize aRng2
'        For i = 1 To ClosedTrades2
'            If arrPnl2(i, 2) > 0 Then GoodTrade2 = GoodTrade2 + 1
'        Next i
'        Set aRng3 = tbl2.DataBodyRange.Resize(ClosedTrades2, dbr2.Columns.count - 2)
'        aRng3 = arrPnl2
'    End If
End Sub
'Sub refreshOHLC1hr() 'Only bitfinex
'    On Error GoTo errHandle
'    aInterval = 1
'    ReCount = 0
'
'    TimeOffset = getTimeOffset
'    UTCTimeLower = (DateAdd("h", TimeOffset - 20, Now) - DateValue("1/1/1970")) * 86400
'
'    loadDB
'
'    'Check if database needs to be refreshed
'    aQuery = "SELECT Max(CloseTime) as MaxOfCloseTime FROM " & getTable & " WHERE Interval =" & aInterval
'    Set rs = db.OpenRecordset(aQuery, dbOpenDynaset)
'    MaxDate = rs.Fields("MaxOfCloseTime")
'    CheckDate = Now + (TimeOffset - 1) / 24
'    rs.Close
'    Set rs = Nothing
'    If MaxDate > CheckDate Then
'        Debug.Print "MaxDate > CheckDate"
'        GoTo cleanup
'    End If
'
'SetRequest:
'    'Get current 24h vol from JSON request
'    Set MyRequest = CreateObject("WinHttp.WinHttpRequest.5.1")
'    MyRequest.Open "GET", "https://api.cryptowat.ch/markets/bitfinex/btcusd/ohlc?periods=3600&after=" & UTCTimeLower 'SET TIME PROPERLY
'    MyRequest.send
'
'    response = MyRequest.responseText
'
'    Set json = JsonConverter.ParseJson(response)
'    NumCandles = json("result")("3600").count
'
'    Set rs = db.OpenRecordset(getTable, dbOpenTable)
'
'    'Change this to index/search
'    With rs
'        Beforecount = .RecordCount
'        For i = 1 To NumCandles - 1 'last candle isn't closed
'            .AddNew
'            .Fields("Interval") = aInterval
'            .Fields("CloseTime") = DateAdd("s", json("result")("3600")(i)(1), #1/1/1970#)
'            .Fields("Open") = json("result")("3600")(i)(2)
'            .Fields("High") = json("result")("3600")(i)(3)
'            .Fields("Low") = json("result")("3600")(i)(4)
'            .Fields("Close") = json("result")("3600")(i)(5)
'            .Fields("VolBTC") = json("result")("3600")(i)(6)
'            .Fields("VolUSD") = json("result")("3600")(i)(7)
'            .update
'next_i:
'        Next i
'        RowsAdded = .RecordCount - Beforecount
'    End With
'
'    If RowsAdded < 1 Then
'        If ReCount <= 10 Then
'            dpCount = 0
'            rs.Close
'            Set rs = Nothing
'            Application.Wait Now + #12:00:02 AM#
'            ReCount = ReCount + 1
'            GoTo SetRequest
'        Else
'            Debug.Print "ReCount: " & ReCount
'            Err.Raise 500, Description:="No row(s) added to database."
'        End If
'    End If
'
'cleanup:
'    On Error Resume Next
'    ReCount = 0
'    CleanupRS
'    Debug.Print "RowsAdded: " & RowsAdded
'    Debug.Print "Duplicates skipped: " & dpCount
'    Exit Sub
'errHandle:
'    If Err.Number = 3022 Then
'        dpCount = dpCount + 1
'        Resume next_i 'Duplicate records
'    End If
'    sendErrMsg "JSON_OHLC"
'    Resume cleanup
'End Sub
Sub writeUserBalanceGoogle(collUsers As Collection, Optional collSyms As Collection)
    On Error GoTo errHandle
    Dim oUser As cUser
    Dim rngBalance As String
    Dim rngTrades As String
    Dim arrBalance As Variant
    
'    aUsers = 4
'    StartRow = 2
'    endRow = StartRow + aUsers - 1
'    rngBalance = "B" & StartRow & ":C" & endRow
    rngBalance = "B2:C5"
    
    ReDim arrBalance(1 To 4, 1 To 2) As Variant
    For Each oUser In collUsers
        With oUser
            arrBalance(.gRow, 1) = .UnrealisedPnl
            arrBalance(.gRow, 2) = .TotalBalanceMargin
        End With
    Next
    arrBalance(4, 1) = Format(UtcConverter.ConvertToUtc(Now), "yyyy-mm-dd hh:mm")
    
    'Write last 10 trades
    Dim arrTrades(1 To 13, 1 To 21) As Variant
    Dim Sym As cSymBacktest
    Dim i As Integer
    rngTrades = "A2:U16"
    arrTrades(13, 2) = Format(UtcConverter.ConvertToUtc(Now), "yyyy-mm-dd hh:mm")
    
    For Each Sym In collSyms
        aRow = aRow + 1
        y = Sym.Trades.count
        colLastTrades = 11

        arrTrades(aRow, 1) = Sym.SymbolShort
        
        Dim User As cUser
        Set User = getUser("Jayme")
        
        arrTrades(10, 2) = User.UnrealisedPnl
        arrTrades(10, 3) = User.TotalBalanceMargin
        arrTrades(aRow, 4) = Sym.curCandle.Clse
        
        If User.hasSymbol(Sym.SymbolBitmex) Then
            With User.getSymbol(Sym.SymbolBitmex)
                arrTrades(aRow, 2) = .PositionQty
                arrTrades(aRow, 3) = .AvgEntryPrice
                arrTrades(aRow, 4) = .LastPrice 'bit sketch, overwriting 1hr candle close if we have lastprice from bitmex open position
                arrTrades(aRow, 5) = .UnrealizedPnl
                arrTrades(aRow, 6) = .UnrealizedPnlPcnt
                arrTrades(aRow, 7) = .UnrealizedRoePcnt
                arrTrades(aRow, 8) = .MaintMargin
                arrTrades(aRow, 9) = .Order(eOrd.StopBuy).StopPx
                arrTrades(aRow, 10) = .Order(eOrd.StopClose).StopPx
            End With
            
            Else
            For b = 2 To 6 'skip inactive symbols
                arrTrades(aRow, b) = 0
            Next b
        End If
        
        For i = y To y - 9 Step -1
            colLastTrades = colLastTrades + 1
            arrTrades(aRow, colLastTrades) = Sym.Trade(i, 1).PnLFinal
        Next i
    Next
    
    Dim sheetAccess As New cSheetsV4
    With sheetAccess
        .setAuthName("drivesheetsexternal").setSheetId (getMySheetId())
        .setValues arrBalance, "UserSettings", rngBalance
        .setValues arrTrades, "Bitmex", rngTrades
    End With
    
cleanup:
    Exit Sub
errHandle:
    sendErrMsg "writeUserBalanceGoogle"
    Resume cleanup
End Sub


