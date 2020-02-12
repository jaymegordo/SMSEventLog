Public emaSpread As Double
Public emaMultiplier As Double
Public emaConfidence As Double
Public ema200 As Double
Public ema50 As Double
Public EmaActive As Boolean

Function Normalize(aValue As Double, rMax As Double, rMin As Double, tMax As Double, tMin As Double)
    Normalize = ((aValue - rMin) / (rMax - rMin)) * (tMax - tMin) + tMin
End Function
Sub calcMomentum()
    '% difference open - close multiplied by volume
    For i = 1 To UBound(aArray, 1)
        aArray(i, 7) = aArray(i, 6) * (Abs(aArray(i, 2) - aArray(i, 5)) / ((aArray(i, 2) + aArray(i, 5)) / 2)) / 1000
    Next i
End Sub
Sub calcVolatilityEma(Sym As cSymBacktest, i As Long)
    'load current 24h rolling period into arrays
    ReDim vol24High(1 To 24) As Double
    ReDim vol24Low(1 To 24) As Double
    For y = 1 To UBound(vol24High)
        vol24High(y) = Sym.DS(i - 24 + y, 3)
    Next y
    For y = 1 To UBound(vol24Low)
        vol24Low(y) = Sym.DS(i - 24 + y, 4)
    Next y
    
    With Application.WorksheetFunction
        Max24 = .Max(vol24High)
        Min24 = .min(vol24Low)
    End With
    
    curSpread24 = Abs(Max24 - Min24) / ((Max24 + Min24) / 2)
    
    'calc temporary hourly ema
    tempEma24 = FinalEma24 + alphaVol24 * (curSpread24 - FinalEma24)
    NormalEma24 = Normalize(tempEma24, 0.2, 0.01, 4, 1.2)
    NormalEma24TakeProfit = Normalize(tempEma24, 0.2, 0.01, 4, 0.5)
    'NormalEma24 = 1
    
    If hour(Sym.curCandle.TimeStamp) = 0 Then FinalEma24 = FinalEma24 + alphaVol24 * (curSpread24 - FinalEma24)
    
End Sub


Function getSize(DefaultSpeed, HighLow As Integer, Trend As Integer, ByVal modUp As Double, ByVal modDown As Double) As Integer
    
    Select Case HighLow
        Case 1
            Select Case Trend
                Case 1
                    getSize = CInt(DefaultSpeed * modDown)
                Case -1
                    getSize = CInt(DefaultSpeed * modUp)
            End Select
        Case -1
            Select Case Trend
                Case 1
                    getSize = CInt(DefaultSpeed * modUp)
                Case -1
                    getSize = CInt(DefaultSpeed * modDown)
            End Select
    End Select
    
End Function



Function getEmaConfidence(ema200, ema50, Sym As cSymBacktest, Optional BypassMeanRev As Boolean = False) As Double
    On Error GoTo errHandle
    winConfActive = True
    
    If (Sym.MeanRev Or MeanRevNext) And Not BypassMeanRev Then 'add MeanRevNext to sym
        getEmaConfidence = 1.5

        Exit Function
    End If
    
    midPoint = Sym.MaxSpread / 2
    emaSpread = Abs(getEmaSpread(ema200, ema50))
    
    emaConfidence = Round(1.5 - emaExp(emaSpread, getC(Sym.MaxSpread)), 3)
    
    If Sym.RecentWinConf <= 0.5 And winConfActive Then
        getEmaConfidence = Sym.RecentWinConf
        Else
        getEmaConfidence = emaConfidence
    End If

cleanup:
    Exit Function
errHandle:
    Stop
    sendErrMsg "getEmaConfidence"
End Function
Function getEmaSpread(ema200, ema50)
    getEmaSpread = Round((ema50 - ema200) / ((ema50 + ema200) / 2), 6)
End Function
Function emaExp(X As Double, c As Double) As Double
    Dim convNeg As Boolean
    
    If X < 0 Then
        X = Abs(X)
        convNeg = True
    End If
    
    aLim = 2
    a = -1000
    b = 3
    'C = getC(x)
    d = -3
    g = 1.7
    
    y = Round((a * X ^ b + d * X ^ g) / (aLim * a * X ^ b + aLim * d * X ^ g + c), 6)
    
    If convNeg = True Then
        emaExp = y * -1
        Else
        emaExp = y
    End If
    
End Function
Function getC(MaxSpread)
    m = -2.9
    b = 0.135
    getC = Round(m * MaxSpread + b, 2)
End Function
Sub calcEMA(DS, inputPeriod As Integer, emaCol As Integer, aDec As Integer)
    Dim alpha As Double
    Dim LastRow As Integer
    Dim aRow As Integer
    Dim temp As Double
    Dim closeCol As Integer
    
    LastRow = UBound(DS, 1)
    closeCol = 5
    
    alpha = 2 / (inputPeriod + 1)
    
    For j = 1 To inputPeriod
        temp = temp + DS(j, closeCol)
    Next j
    
    'start with average of n previous values
    DS(inputPeriod, emaCol) = temp / inputPeriod
    
    For i = inputPeriod + 1 To LastRow
        DS(i, emaCol) = Round(DS(i - 1, emaCol) + alpha * (DS(i, closeCol) - DS(i - 1, emaCol)), aDec + 2)
    Next i
    
End Sub


Function emaSlopeExp(X As Double) As Double
    aLim = 2
    a = 0
    b = 1 'doesn't matter
    c = -0.7
    d = -3
    g = 1.7
    
    y = Round((a * X ^ b + d * X ^ g) / (aLim * a * X ^ b + aLim * d * X ^ g + c), 6)
    emaSlopeExp = y
End Function


