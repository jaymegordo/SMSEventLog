Private pEntryPrice As Double
Private pExitPrice As Double
Private pContracts As Double
Private pSide As Integer
Private pPnlFinal As Double
Private pSym As cSymBacktest
Private pStatus As Long
Private pType As Integer
Private pTradeNo As Long
Private pCollCandles As Collection
Private pStopPx As Double
Private pActive As Boolean

'P2
Private pEntryRow As Long
Private pNumOrders As Integer

Private pOrders As cOrdArray
Private pStops As cOrdArray
Private pTakeProfits As cOrdArray
Private pTargetContracts As Long

Private Sub class_initialize()
    Set pCollCandles = New Collection
End Sub

Public Property Get Active() As Boolean
    Active = pActive
End Property

Public Property Get Candle(i As Integer) As cCandle
    Set Candle = pCollCandles.Item(i)
End Property

Public Property Get Contracts() As Double
    Contracts = Round(pContracts, 0)
End Property

Public Property Get Duration() As Long 'Duration in hours
    Duration = pCollCandles.count
End Property

Public Property Get EntryPrice() As Double
    EntryPrice = pEntryPrice
End Property

Public Property Let EntryPrice(dEntryPrice As Double)
    pEntryPrice = dEntryPrice
End Property

Public Property Get ExitDate() As Date
    Dim oCandle As cCandle
    Set oCandle = pCollCandles.Item(Duration)
    ExitDate = oCandle.TimeStamp
End Property

Public Property Get ExitPrice() As Double
    ExitPrice = pExitPrice
End Property

Public Property Let ExitPrice(dExitPrice As Double)
    pExitPrice = dExitPrice
End Property

Public Property Get Extremum(HighLow As Integer) As Double
    Dim oCandle As cCandle
    
    'Entry candle
    Set oCandle = pCollCandles.Item(1)
    Select Case pStatus * HighLow
        Case 1, -2
            Select Case HighLow
                Case 1
                    Extremum = oCandle.High
                Case -1
                    Extremum = oCandle.Low
            End Select
        Case -1, 2
            Extremum = pEntryPrice 'this isnt correct for P2
    End Select
    
    'Middle candles
    For i = 2 To Duration - 1
        Set oCandle = pCollCandles.Item(i)
        Select Case HighLow
            Case 1
                If oCandle.High > Extremum Then Extremum = oCandle.High
            Case -1
                If oCandle.Low < Extremum Then Extremum = oCandle.Low
        End Select
    Next
    
    'Exit candle
    Set oCandle = pCollCandles.Item(Duration)
    Select Case pStatus * HighLow
        Case -1, 2
            fExt = pExitPrice
        Case 1, -2
            Select Case HighLow
                Case 1
                    fExt = oCandle.High
                Case -1
                    fExt = oCandle.Low
            End Select
    End Select
    
    If (fExt - Extremum) * HighLow > 0 Then Extremum = fExt
    
End Property

Public Property Get Good() As Boolean
    If pPnlFinal > 0 Then
        Good = True
        Else
        Good = False
    End If
End Property

Public Property Get isStopped() As Boolean ' meanrev
    If PnlMaxMin(-1) < pSym.StopPercent Then
        isStopped = True
        Else
        isStopped = False
    End If
End Property

Public Property Get OrdArray(oType As Long) As cOrdArray
    Select Case oType
        Case 1
            Set OrdArray = pOrders
        Case 2
            Set OrdArray = pStops
        Case 3
            Set OrdArray = pTakeProfits
    End Select
End Property

Public Property Get PnLCurrent(Optional oCandle As cCandle) As Double
    If oCandle Is Nothing Then Set oCandle = pCollCandles.Item(Duration)
    PnLCurrent = getPnlLongShort(pSide, pEntryPrice, oCandle.Clse)
End Property

Public Property Get PnLFinal() As Double
    PnLFinal = pPnlFinal
End Property

Public Property Get PnlMaxMin(MaxMin As Integer) As Double
    PnlMaxMin = getPnlLongShort(pSide, pEntryPrice, Extremum(pSide * MaxMin))
End Property

Public Property Get Side() As Integer 'long?
    Side = pSide
End Property

Public Property Get StartDate() As Date
    Dim oCandle As cCandle
    Set oCandle = pCollCandles.Item(1)
    StartDate = oCandle.TimeStamp
End Property

Public Property Get Status() As Long
    Status = pStatus
End Property

Public Property Get StopPx() As Double
    StopPx = pStopPx
End Property

Public Property Get Sym() As cSymBacktest
    Set Sym = pSym
End Property

Public Property Get TargetContracts() As Double
    TargetContracts = Round(pTargetContracts, 0)
End Property

Public Property Get TradeNo() As Long
    TradeNo = pTradeNo
End Property

Public Sub addCandle(oCandle As cCandle)
    pCollCandles.add oCandle
End Sub

Public Sub addContracts(lContracts As Double)
    pContracts = pContracts + lContracts
End Sub

Public Sub checkOrders() 'P2 Only
    If Duration > 5 Then pOrders.Active = False
    If pContracts <> 0 And Duration > 1 Then pTakeProfits.Active = True ' should maybe set this active only once?
    
    Dim oCandle As cCandle
    Set oCandle = pCollCandles.Item(Duration)
    
    pOrders.checkOrders oCandle
    pStops.checkOrders oCandle
    pTakeProfits.checkOrders oCandle
    
    If Not pOrders.Active And pContracts = 0 Then pActive = False
    If pStops.Filled Or pTakeProfits.Filled Then pActive = False
    
End Sub

Public Sub Enter(Price As Double, Contracts As Double, Sym As cSymBacktest, Optional EntryRow As Long, Optional iType As Integer = 1)
    pEntryPrice = Price
    Set pSym = Sym
    pType = iType
    pTradeNo = pSym.TradeCount(pType) + 1
    pStatus = pSym.Status(pType)
    pSide = pSym.Side(iType) ' sketch
    
    If iType = 1 Then '? lol
        pContracts = Contracts
    End If
    
    If Abs(pStatus) = 2 Then pStopPx = getPrice(pSym.StopPercent, pEntryPrice, pSide) 'meanrev only
    
    If iType = 2 Then 'set trade type
        pTargetContracts = Contracts

        pNumOrders = 4
        pEntryRow = EntryRow
        pActive = True
        
        Set pOrders = New cOrdArray
        pEntryPrice = pEntryPrice * (1 + NormalEma24 * 0.015 * pStatus * -1)
        pOrders.init 1, pEntryPrice, (0.002 * NormalEma24), Me
        pOrders.Active = True
        
        Set pStops = New cOrdArray
        pStops.init 2, getPrice(-0.01 * NormalEma24, pEntryPrice, pStatus), 0.001, Me
        pStops.Active = True
        
        Set pTakeProfits = New cOrdArray
        pTakeProfits.init 3, getPrice(0.02 * NormalEma24TakeProfit, pEntryPrice, pStatus), (0.0025 * NormalEma24TakeProfit), Me
        
    End If
    
End Sub

Public Sub Exit_(Optional Price As Double)
    Select Case pType
        Case 1
            pExitPrice = Price
            If Not pSym.StratActive Then _
                Account.modify getPnlXBT(pContracts, pEntryPrice, pExitPrice, pSym.AltStatus), _
                pSym.curCandle.TimeStamp   'Add or subtract profit from trade
        Case 2
        
    End Select
    
    pSym.collTrades(pType).add Me
    pSym.Status(pType) = 0
    pPnlFinal = getPnlLongShort(pSide, pEntryPrice, pExitPrice)
End Sub

Public Sub printLine()
    Debug.Print pTradeNo, _
                Format(StartDate, "yyyy-mm-dd HH:nn"), _
                pStatus, _
                Format(pEntryPrice, getPriceFormat(pSym.AltStatus)), _
                Format(pExitPrice, getPriceFormat(pSym.AltStatus)), _
                Duration, _
                Format(PnlMaxMin(1), "Percent"), _
                Format(PnlMaxMin(-1), "Percent"), _
                Format(PnLFinal, "percent")
End Sub

Public Sub printVars()
    Debug.Print Line & "*------- " & pTradeNo & "-------*"
    Debug.Print "Status", pStatus
    Debug.Print "StartDate", Format(StartDate, "yyyy-mm-dd HH:nn")
    Debug.Print "Duration", Duration
    Debug.Print "EntryPrice", pEntryPrice
    Debug.Print "ExitPrice", pExitPrice
    Debug.Print "Low", Extremum(-1)
    Debug.Print "High", Extremum(1)
    Debug.Print "Max Pnl", Format(PnlMaxMin(1), "Percent")
    Debug.Print "Min Pnl", Format(PnlMaxMin(-1), "Percent")
    Debug.Print "Final Pnl", Format(PnLFinal, "Percent")
End Sub

' Private Sub setSide()
'     Select Case True
'         Case pContracts > 0
'             pSide = 1
'         Case pContracts < 0
'             pSide = -1
'         Case pContracts = 0
'             pSide = 0
'     End Select
' End Sub

