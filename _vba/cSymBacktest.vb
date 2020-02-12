Public symbol As String
Public SymbolShort As String
Public SymbolBitmex As String
Public UrlShort As String
Private pPercentBalance As Double
Private pTrade As cTrade
Private pTrade2 As cTrade
Private pGoodTrades As Long
Private pDs() As Variant ' timeseries array
Private pCollTrades As Collection
Private pCollTrades2 As Collection
Private pCollCandles As Collection
Private pStartRow As Long
Private pCurCandle As cCandle
Private pPrevCandle As cCandle
Private pModUp As Double
Private pModDown As Double
Private pModUp2 As Double
Private pModDown2 As Double
Private pEnterSpeed As Integer
Private pExitSpeed As Integer
Private pHighEnter As Double
Private pLowEnter As Double
Private pHighExit As Double
Private pLowExit As Double
Private pHighEnter2 As Double
Private pLowEnter2 As Double
Private pStatus As Long
Private pStatus2 As Long
Private pEmaActive As Boolean
Private pMeanRevEnabled As Boolean
Private pMeanRev As Boolean
Private pStratActive As Boolean
Private pMaxSpread As Double
Private pSlippage As Double
Private pAltStatus As Boolean
Private pDec As Integer
Private pLeverage As Double
Private pW1 As Double
Private pW2 As Double
Private pMeanRevMin As Double
Private pstartdate As Date
Private pEndDate As Date
Private pP1Enabled As Boolean
Private pP2Enabled As Boolean
Private i As Long
Private pStopPercent As Double
Private pSw As cStopWatch
Private pTbl As ListObject
Private pDbr As Range
Private pUserMsg As String

Public Enum sts
    ShortMR = -2
    Short = -1
    Neutral = 0
    Lng = 1
    LngMR = 2
End Enum

Private Sub class_initialize()
    Set pCollTrades = New Collection
    Set pCollTrades2 = New Collection
    Set pCollCandles = New Collection
    Set pTbl = Sheet1.ListObjects(1)
    Set pDbr = pTbl.DataBodyRange
    pStatus = 0
    pStatus2 = 0
    pMaxSpread = 0.1
    pSlippage = 0.0044
    pEmaActive = True
    pEnterSpeed = 18
    pExitSpeed = 18
    pLeverage = 5
    pW1 = 1 'accept these from init
    pW2 = 1
    pMeanRevMin = 0.05
    pStopPercent = -0.06
    pModUp2 = 2
    pModDown2 = 1.5
End Sub

Public Property Get AltStatus() As Boolean 'FIX THISSS
    AltStatus = pAltStatus
End Property

'i is the row number, not the number of the candle in pCollCandles

Public Property Get Candle(i As Integer) As cCandle
    Set Candle = pCollCandles.Item(i)
End Property

Public Property Get collTrades(a As Integer) As Collection
    Select Case a
        Case 1
            Set collTrades = pCollTrades
        Case 2
            Set collTrades = pCollTrades2
    End Select
End Property

Public Property Get curCandle() As cCandle
    Set curCandle = pCurCandle
End Property

Public Property Get curTrade(iType As Integer) As cTrade
    Select Case iType
        Case 1
            Set curTrade = pTrade
        Case 2
            Set curTrade = pTrade2
    End Select
End Property

Public Property Get DS(row As Long, col As Integer) As Variant
    DS = pDs(row, col)
End Property

Public Property Let DS(row As Long, col As Integer, val As Variant)
    pDs(row, col) = val
End Property

Public Property Get DScopy() As Variant
    DScopy = pDs
End Property

Public Property Get DSCount() As Long
    DSCount = UBound(pDs, 1)
End Property

Public Property Get EmaActive() As Boolean
    EmaActive = pEmaActive
End Property

Public Property Get GoodTrades(iType As Integer) As Long
    pGoodTrades = 0
    Dim oTrade As cTrade
    For Each oTrade In collTrades(iType)
        If oTrade.Good Then pGoodTrades = pGoodTrades + 1
    Next
    GoodTrades = pGoodTrades
End Property

Public Property Get LastRow() As Long
    LastRow = UBound(pDs, 1)
End Property

Public Property Get MaxSpread() As Double
    MaxSpread = pMaxSpread
End Property

Public Property Get MeanRev() As Boolean
    MeanRev = pMeanRev
End Property

Public Property Get nextStatus() As Long
    nextStatus = Side(1) * -1
End Property

Public Property Get nextStopPx() As Double
    Select Case pStatus
        Case 1, -2
            nextStopPx = pLowExit
        Case -1, 2
            nextStopPx = pHighExit
    End Select
End Property

Public Property Get RecentWinConf() As Double
    Dim y As Integer
    ClosedTrades = TradeCount(1)
    If ClosedTrades < 3 Then
        ctOffset = ClosedTrades - 1
        Else
        ctOffset = 2
    End If
    For y = ClosedTrades To ClosedTrades - ctOffset Step -1
        If Trade(y, 1).PnLFinal > 0.05 Then RecentWin = True
    Next y
    If RecentWin Then
        RecentWinConf = 0.25
        Else
        RecentWinConf = 1
    End If
End Property

Public Property Get Side(iType As Integer) As Long
    Select Case iType
        Case 1
            aStatus = pStatus
        Case 2
            aStatus = pStatus2
    End Select
    
    Select Case True
        Case aStatus = 0
            Side = 0
        Case aStatus < 0
            Side = -1
        Case aStatus > 0
            Side = 1
    End Select
End Property

Public Property Get StartRow() As Long
    If pStartRow = 0 Then pStartRow = Application.match(Round(CDbl(pstartdate), 6), Application.Index(pDs, 0, 1), 0)
    
    StartRow = pStartRow
End Property

Public Property Get Status(iType As Integer) As Long
    Select Case iType
        Case 1
            Status = pStatus
        Case 2
            Status = pStatus2
    End Select
End Property

Public Property Let Status(iType As Integer, lStatus As Long)
    Select Case iType
        Case 1
            pPrevStatus = pStatus
            pStatus = lStatus
        Case 2
            pStatus2 = lStatus
    End Select
End Property

Public Property Get StopPercent() As Double
    StopPercent = pStopPercent
End Property

Public Property Get StratActive() As Boolean
    StratActive = pStratActive
End Property

Public Property Get Trade(i As Integer, iType As Integer) As cTrade
    If i > TradeCount(iType) Then i = TradeCount(iType)
    Set Trade = collTrades(iType).Item(i)
End Property

Public Property Get TradeCount(iType As Integer) As Long
    TradeCount = collTrades(iType).count
End Property

Public Property Get Trades() As Collection
    Set Trades = pCollTrades
End Property

Public Property Get UserMsg() As String
    UserMsg = pUserMsg
End Property

Public Property Let UserMsg(sUserMsg As String) 'This always appends the message, can't clear
    pUserMsg = pUserMsg & sUserMsg
End Property

Public Sub addUserMsg(sMsg As String)
    pUserMsg = pUserMsg & sMsg
End Sub

Private Sub checkTrade2()
    pTrade2.checkOrders
    If Not pTrade2.Active Then
        pTrade2.Exit_
        Set pTrade2 = Nothing
    End If
End Sub

Public Sub Decide(aRow As Long) 'decision logic
    i = aRow
    initCandle
    If i < pStartRow Then Exit Sub

    If Not pTrade Is Nothing Then pTrade.addCandle pCurCandle
    If Not pTrade2 Is Nothing Then pTrade2.addCandle pCurCandle
    
    If pP1Enabled Then 'Fix this! Don't pass array
        pHighEnter = getExtremum(pDs, MaxMin:=1, Size:=getSize(pEnterSpeed, 1, pCurCandle.Trend, pModUp, pModDown), StartRow:=i, aCol:=3)    

        pLowEnter = getExtremum(pDs, MaxMin:=-1, Size:=getSize(pEnterSpeed, -1, pCurCandle.Trend, pModUp, pModDown), StartRow:=i, aCol:=4) 

        pHighExit = pHighEnter
        pLowExit = pLowEnter
        
        'Main classifier
        Select Case pStatus
            Case Lng, ShortMR
                If pCurCandle.Low < pLowExit Then
                    exitTrade pLowExit * (1 - Slippage)
                        
                    ElseIf Not pTrade Is Nothing And Abs(pStatus) = 2 Then
                        If pTrade.isStopped Then exitTrade pTrade.StopPx
                End If
                
                Select Case pMeanRev
                    Case False 'normal --> Short Enter Check
                        If pCurCandle.Low < pLowEnter Then enterTrade Short

                    Case True 'opposite --> Long Enter Check, but on a low...
                        If pCurCandle.Low < pLowExit Then enterTrade Lng
                End Select
                
            Case Short, LngMR
                If pCurCandle.High > pHighExit Then
                    exitTrade pHighExit * (1 + Slippage)
                
                    ElseIf Not pTrade Is Nothing And Abs(pStatus) = 2 Then
                        If pTrade.isStopped Then exitTrade pTrade.StopPx
                End If
                
                Select Case pMeanRev
                    Case False 'normal --> Long Enter Check
                        If pCurCandle.High > pHighEnter Then enterTrade Lng
                    
                    Case True 'opposite --> Short Enter Check
                        If pCurCandle.High > pHighExit Then enterTrade Short
                End Select
                        
            Case Neutral
                If pCurCandle.High > pHighEnter Then enterTrade Lng
                If pCurCandle.Low < pLowEnter Then enterTrade Short

        End Select
    End If

    If pP2Enabled Then
        pDs(i, 24) = NormalEma24 ' this needs to move
        pDs(i, 25) = NormalEma24TakeProfit

        pHighEnter2 = getExtremum(pDs, MaxMin:=1, Size:=getSize(pEnterSpeed, -1, pCurCandle.Trend, pModUp2, pModDown2), StartRow:=i, aCol:=3)
        pLowEnter2 = getExtremum(pDs, MaxMin:=-1, Size:=getSize(pEnterSpeed, 1, pCurCandle.Trend, pModUp2, pModDown2), StartRow:=i, aCol:=4)

        Select Case pStatus2
            Case Lng, Short
                checkTrade2
                
            Case Neutral
                If pCurCandle.High > pHighEnter2 Then
                    pStatus2 = -1 'go short ' make entering the trade set the sym status
                    enterTrade2

                    ElseIf pCurCandle.Low < pLowEnter2 Then
                        pStatus2 = 1
                        enterTrade2
                End If
        End Select
    End If

    writeRow
End Sub

Public Sub DecideFull()
    For i = 1 To LastRow
        Decide i
    Next i
End Sub

Public Sub enterTrade(Side As Long)
    On Error GoTo errHandle
    Dim EntryPrice As Double
    Dim Contracts As Double
    
    Select Case Side
        Case Lng
            Select Case pMeanRev
                Case False
                    pStatus = Lng
                    EntryPrice = pHighEnter
                Case True
                    pStatus = LngMR
                    EntryPrice = pLowExit
            End Select
        Case Short
            Select Case pMeanRev
                Case False
                    pStatus = Short
                    EntryPrice = pLowEnter
                Case True
                    pStatus = ShortMR
                    EntryPrice = pHighExit
            End Select
    End Select
    If pEmaActive Then emaConfidence = getEmaConfidence(pCurCandle.ema200, pCurCandle.ema50, Me)
    
    If Not pMeanRev Then 'check this for meanrev entries - could make this 1 line with MeanRev as 1/-1
        EntryPrice = EntryPrice * (1 + pSlippage * Side)
        Else
        EntryPrice = EntryPrice * (1 - pSlippage * Side)
    End If
    
    If Not pStratActive Then
        pDs(i, colEntry1) = "Entry: " & Format(EntryPrice, getPriceFormat(AltStatus)) & " ema: " & emaConfidence
        Contracts = Round(getContracts(Account.Balance * pPercentBalance, pLeverage, EntryPrice, Side, pAltStatus) * emaConfidence * pW1, 0)
    End If
    
    If pTrade Is Nothing Then
        Set pTrade = New cTrade
        pTrade.addCandle pCurCandle
        Else
        Err.Raise 444, , "pTrade not nothing"
    End If
    pTrade.Enter EntryPrice, Contracts, Me
    
    ' If pTrade.Candle(1).isSwingFail(Me) Then
        ' Debug.Print "Exiting swingfail", i
        ' pDs(i, colEntry1) = pDs(i, colEntry1) & Line & "sfp exit: " & pTrade.Candle(1).Clse
        ' exitTrade pTrade.Candle(1).Clse
    End If
    
cleanup:
    On Error Resume Next
    Exit Sub
errHandle:
    sendErrMsg "enterTrade"
    Resume cleanup
End Sub

Sub enterTrade2()
    On Error GoTo errHandle
    Dim Contracts As Double
    Dim EntryPrice As Double
    Select Case pStatus2
        Case 1
            EntryPrice = pLowEnter2
        Case -1
            EntryPrice = pHighEnter2
    End Select
    Contracts = getContracts(Account.Balance * pPercentBalance, pLeverage, EntryPrice, pStatus2, pAltStatus) * pW2  'if not pstratactive?
    
    If pTrade2 Is Nothing Then
        Set pTrade2 = New cTrade
        pTrade2.addCandle pCurCandle
        pTrade2.Enter EntryPrice, Contracts, Me, i, 2
        Else
        Err.Raise 444, , "pTrade2 not nothing"
    End If
    
    If Not pStratActive Then pDs(i, colEntry2) = "Entry: " & Format(pTrade2.OrdArray(1).AnchorPrice, getPriceFormat) _
                                    & " Stop: " & Format(pTrade2.OrdArray(2).AnchorPrice, getPriceFormat) _
                                    & " Target: " & Format(pTrade2.OrdArray(3).AnchorPrice, getPriceFormat)
    Stop
    checkTrade2
cleanup:
    On Error Resume Next
    Exit Sub
errHandle:
    sendErrMsg "enterTrade2"
    Resume cleanup
End Sub

Public Sub exitTrade(ExitPrice As Double) 'Optional MeanRevEnabled, Optional EmaActive, Optional P2Enabled)
    On Error GoTo errHandle
    MaxPnl = 0
    minPnl = 0
    
    If Not pStratActive Then
        ' arrPnl(ClosedTrades, 3) = arrPnl(ClosedTrades, 2) * emaConfidence
        
        'Modify w1 according to trending profit
        ' If P2Enabled And WeightP2 Then setWeightW1Ema
        
        'Debug.Print emaConfidence
        ' If EmaActive Then arrPnl(ClosedTrades, 4) = Abs(getEmaSpread(aArray(EntryRow, colEma200), aArray(EntryRow, colEma50))) 'getEmaSpread at entry ema200/50
        
        ' MaxPnl = getPnl(pStatus, EntryPrice, getMaxMin(1, True)) ' Uses Longshort and aArray
        ' MinPnl = getPnl(pStatus, EntryPrice, getMaxMin(-1, True))
        
        If minPnl < pStopPercent And pMeanRev Then ExitPrice = getPrice(pStopPercent, EntryPrice) 'Get stopped out!
    End If
    
    pTrade.Exit_ ExitPrice
    
    If pMeanRev Then
        pMeanRev = False
        ElseIf pTrade.PnLCurrent(pCurCandle) > pMeanRevMin And pMeanRevEnabled Then pMeanRev = True
    End If
    
cleanup:
    On Error Resume Next
    Set pTrade = Nothing
    Exit Sub
errHandle:
    sendErrMsg "exitTrade"
    Resume cleanup
End Sub

Public Sub init(symbol As String, _
                StartDate As Date, _
                Optional modUp As Double = 1, _
                Optional modDown As Double = 1, _
                Optional MeanRevEnabled As Boolean = False, _
                Optional StratActive As Boolean = False, _
                Optional P1Enabled As Boolean = True, _
                Optional P2Enabled As Boolean = False, _
                Optional rsSym As ADODB.Recordset, _
                Optional PercentBalance As Double = 1, _
                Optional EndDate As Date)
    
    If Not rsSym Is Nothing Then
        With rsSym
            Me.SymbolShort = !SymbolSimple
            Me.UrlShort = !UrlShort
            Me.SymbolBitmex = !SymbolBitmex
            pAltStatus = !AltStatus
        End With
    End If
    
    ' Set pSw = New cStopWatch
    Me.symbol = symbol
    pstartdate = StartDate
    pPercentBalance = PercentBalance
    pModUp = modUp
    pModDown = modDown
    pMeanRevEnabled = MeanRevEnabled
    pStratActive = StratActive
    pP1Enabled = P1Enabled
    pP2Enabled = P2Enabled
    pDec = getDecimal(pAltStatus) ' should pass this in with a symbol?
    
    pDs = loadArray(CDate(pstartdate - 10), 1, symbol)
    pStartRow = StartRow
    
    calcEMA pDs, 200, colEma200, pDec
    calcEMA pDs, 50, colEma50, pDec
    calcEMA pDs, 10, colEma10, pDec
    ' calcMomentum ' only works for BTC, alt indexs have no volume 'need to tell it the DS
    
    i = 1 'StartRow
    initCandle
End Sub

Public Sub initarray() 'is this used?
    ReDim pDs(1 To 10, 1 To 5) As Variant
End Sub

Private Sub initCandle()
    Set pCurCandle = New cCandle
    With pCurCandle
        .TimeStamp = pDs(i, 1)
        .Opn = pDs(i, 2)
        .High = pDs(i, 3)
        .Low = pDs(i, 4)
        .Clse = pDs(i, 5)
        .ema200 = pDs(i, colEma200)
        .ema50 = pDs(i, colEma50)
        .ema10 = pDs(i, colEma10)
        .i = i
    End With
    pCollCandles.add pCurCandle
End Sub

Public Sub printFinal(Optional iType As Integer = 1)
    Debug.Print symbol, MinBTCValue, MaxBTCValue, FinalBTCValue, Me.GoodTrades(iType) & "/" & Me.TradeCount(iType)
End Sub

Public Sub printTrades(p As Integer)
    Dim oTrade As cTrade
    For Each oTrade In collTrades(p)
        oTrade.printLine
    Next
End Sub

Private Sub pStatus_Change()
    Debug.Print strStatus(pStatus)
End Sub

Public Sub Teardown()
    Erase pDs
End Sub

Private Sub writeRow() 'Save current balances to aArray
    pDs(i, colStatus1) = pStatus
    pDs(i, colStatus2) = pStatus2
    
    If Not pStratActive Then
        pDs(i, colBalanceBTC) = Account.Balance
        ' pDs(i, colBalanceUSD) = Account.Balance * pCurCandle.Clse 'USD value of margin balance
        
        If Not pTrade Is Nothing Then
            pDs(i, colContracts1) = pTrade.Contracts
            pDs(i, colProfit1) = Format(pTrade.PnLCurrent(pCurCandle), "Percent")
        End If
        
        If Not pTrade2 Is Nothing Then
            pDs(i, colContracts2) = pTrade2.Contracts
            pDs(i, colAvgEntry2) = pTrade2.EntryPrice
            pDs(i, colProfit2) = Format(pTrade2.PnLCurrent(pCurCandle), "Percent")
        End If
        pDs(i, colW1) = pW1
    End If
End Sub



