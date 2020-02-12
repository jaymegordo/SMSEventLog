Public Name As String
Public NameSimple As String
Public SymbolBitmex As String
Public MsgStatus As String

Public UnrealizedPnl As Double
Public UnrealizedPnlPcnt As Double
Public UnrealizedRoePcnt As Double
Public PercentBalance As Double
Public MaintMargin As Double
Public PositionQty As Long
Public DecimalFigs As Long
Public OrderQtyStopBuy As Long
Public EmaActive As Boolean


Private pAvgEntryPrice
Private pStopPx As Double
Private pTargetPrice As Double
Private pLastPrice As Double
'Private pMaxHighExit As Double
'Private pMinLowExit As Double
Private pLongShort As Integer
Private pAltStatus As Boolean
Private pConfidence As Double

Private pOrder As cOrder
Private pCollOrders As Collection

Private Sub class_initialize()
    PositionQty = 0
    PercentBalance = 0
    Set pCollOrders = New Collection
    pConfidence = 1
End Sub

'Functions?
Public Sub addOrder(ClOrdID As String, OrderID As String, OrderQty, Optional Price, Optional StopPx)
    Set pOrder = New cOrder
    With pOrder
        .ClOrdID = ClOrdID
        .OrderID = OrderID
        .Price = Price
        .StopPx = StopPx
        .OrderQty = OrderQty
    End With
    pCollOrders.add pOrder
End Sub
Public Property Get Orders() As Collection
    Set Orders = pCollOrders
End Property
Public Function Order(OrdType As Long) As cOrder
    For Each pOrder In pCollOrders
        If pOrder.OrdType = OrdType Then
            Set Order = pOrder
            Exit Function
        End If
    Next
    Set Order = New cOrder
End Function
Public Function hasOrder(OrdType As Long) As Boolean
    For Each pOrder In pCollOrders
        If pOrder.OrdType = OrdType Then
            hasOrder = True
            Exit Function
        End If
    Next
    hasOrder = False
End Function
' Properties
Public Property Get CloseOnly() As Boolean
    If PercentBalance = 0 Then
        CloseOnly = True
        Else
        CloseOnly = False
    End If
End Property
Public Property Get AvgEntryPrice() As Variant 'AvgEntryPrice
    AvgEntryPrice = pAvgEntryPrice
End Property
Public Property Let AvgEntryPrice(ByVal dAvgEntryPrice As Variant)
    If IsNumeric(dAvgEntryPrice) Then
        pAvgEntryPrice = dAvgEntryPrice
        Else
        pAvgEntryPrice = 0
    End If
End Property
Public Property Get LastPrice() As Variant 'LastPrice
    LastPrice = pLastPrice
End Property
Public Property Let LastPrice(ByVal dLastPrice As Variant)
    If IsNumeric(dLastPrice) Then
        pLastPrice = dLastPrice
        Else
        pLastPrice = 0
    End If
End Property
Public Property Get AltStatus() As Boolean
    AltStatus = pAltStatus
End Property
Public Property Let AltStatus(bAltStatus As Boolean)
    pAltStatus = bAltStatus
End Property
Public Property Get Confidence() As Double
    Confidence = pConfidence
End Property
Public Property Let Confidence(ByVal dConfidence As Double)
    pConfidence = dConfidence
End Property
Public Property Get Leverage() As Double 'This should probably change
    If pAltStatus = False Then
        Leverage = 5
        Else
        Leverage = 2.5
    End If
End Property
Public Property Get TargetPrice() As Double 'TargetPrice
    If pTargetPrice = 0 Then pTargetPrice = pStopPx
    TargetPrice = Round(pTargetPrice, DecimalFigs) + DecimalsDouble * pLongShort * -1 'cause logic is >= but bitmex stops are just =
End Property
Public Property Let TargetPrice(dTargetPrice As Double)
    pTargetPrice = dTargetPrice
End Property
Public Property Get StopPx() As Double 'stopPx
    StopPx = Round(pStopPx, DecimalFigs) + DecimalsDouble * pLongShort * -1
End Property
Public Property Let StopPx(ByVal dstopPx As Double)
    pStopPx = dstopPx
End Property
Public Property Get LongShort() As Integer 'LongShort
    LongShort = pLongShort
End Property
Public Property Let LongShort(iLongShort As Integer)
    pLongShort = iLongShort
End Property
Public Property Get LongShortNew() As Integer 'LongShortNew
    LongShortNew = pLongShort * -1
End Property
Public Property Get OrderQtyStopClose() As Long
    OrderQtyStopClose = PositionQty * -1
End Property
Public Function DecimalsDouble() As Double
    DecimalsDouble = CDbl("1E-" & DecimalFigs)
End Function

Public Function printVars()
    PRNT Line & "--------------- " & SymbolBitmex
    PRNT "  AvgEntryPrice", AvgEntryPrice
    PRNT "  UnrealizedPnl", UnrealizedPnl
    PRNT "  UnrealizedPnlPcnt", UnrealizedPnlPcnt
    PRNT "  UnrealizedRoePcnt", UnrealizedRoePcnt
    PRNT "  PercentBalance", PercentBalance
    PRNT "  MaintMargin     ", MaintMargin
    PRNT "  AltStatus       ", AltStatus
    PRNT "  Leverage        ", Leverage
    PRNT "  TargetPrice     ", TargetPrice
    PRNT "  stopPx      ", StopPx
    PRNT "  MaxHighExit     ", MaxHighExit
    PRNT "  MinLowExit      ", MinLowExit
    PRNT "  LongShort       ", LongShort
    PRNT "  LongShortNew", LongShortNew
    PRNT "  PositionQty     ", PositionQty
    PRNT "  OrderQtyStopClose", OrderQtyStopClose
    PRNT "  OrderQtyStopBuy", OrderQtyStopBuy
'    PRNT "  DecimalsDouble", DecimalsDouble
End Function
Public Function printOrders()
    Debug.Print Line & "--------------- " & SymbolBitmex
    For Each pOrder In pCollOrders
        With pOrder
            Debug.Print "ClOrdID", .ClOrdID
            Debug.Print "OrderID", .OrderID
            Debug.Print "OrderQty", .OrderQty
            Debug.Print "Price", .Price
            Debug.Print "stopPx", .StopPx
        End With
    Next
End Function
