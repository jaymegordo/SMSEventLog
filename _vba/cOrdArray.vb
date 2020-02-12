
Private pMaxFilled As Integer
Private pAnchorPrice As Double
Private pOrdType As Long
Private pOrderSpread As Double
Private pActive As Boolean
Private pFilled As Boolean
Private pNumOrders As Integer
Private pTrade As cTrade

Public Enum eOrdType
    Ord = 1
    Stp = 2
    Tp = 3
End Enum

Public Sub init(OrdType As Long, AnchorPrice As Double, OrderSpread As Double, Trade As cTrade)
    pOrdType = OrdType
    pAnchorPrice = AnchorPrice
    pOrderSpread = OrderSpread
    Set pTrade = Trade
End Sub
Private Sub class_initialize()
    pNumOrders = 4
End Sub

Public Sub checkOrders(oCandle As cCandle)
    Dim b As Integer
    Dim bContracts As Double
    Dim bOrderPrice As Double
    Dim TargetContracts As Long
    
    If Not pActive Then Exit Sub
    If (pOrdType = 2 Or pOrdType = 3) And pTrade.Contracts = 0 Then Exit Sub
    
    Select Case pTrade.Side * EnterExit
        Case 1
            ReachedPrice = oCandle.High
        Case -1
            ReachedPrice = oCandle.Low
    End Select
    
    Select Case pOrdType
        Case 1
            TargetContracts = pTrade.TargetContracts
        Case 2, 3
            TargetContracts = pTrade.Contracts
    End Select
    
    For b = pMaxFilled + 1 To pNumOrders
        bOrderPrice = getOrderPrice(pAnchorPrice, b, pOrderSpread, pTrade.Side, EnterExit)
        
        If pTrade.Side * EnterExit * (bOrderPrice - ReachedPrice) <= 0 Then
            pMaxFilled = b
            bContracts = TargetContracts * getFraction(b)
            
            If AddSubtract = -1 And b = pNumOrders Then bContracts = pTrade.Contracts ' close all remaining contracts
            
            pTrade.addContracts bContracts * AddSubtract 'may need to reverse adding contracts and modifying balance
            
            Select Case pOrdType
                Case 1
                    pTrade.EntryPrice = (pTrade.EntryPrice * pTrade.Contracts + bOrderPrice * bContracts) / (pTrade.Contracts + bContracts)
                
                Case 2, 3
                    pTrade.ExitPrice = (pTrade.ExitPrice * pTrade.Contracts + bOrderPrice * bContracts) / (pTrade.Contracts + bContracts)
                    Account.modify getPnlXBT(bContracts, pTrade.EntryPrice, bOrderPrice, pTrade.Sym.AltStatus), oCandle.TimeStamp
            End Select
        End If
    Next b
    
    If pMaxFilled >= pNumOrders Then pFilled = True
'    If pOrdType = 2 And oCandle.i = 347 Then Err.Raise 444
    
    pTrade.Sym.DS(oCandle.i, colEntry2) = pTrade.Sym.DS(oCandle.i, colEntry2) & " " & Ltr & pMaxFilled
    
End Sub

Public Property Get AnchorPrice() As Double
    AnchorPrice = pAnchorPrice
End Property
Public Property Get Active() As Boolean
    Active = pActive
End Property
Public Property Let Active(bActive As Boolean)
    pActive = bActive
End Property
Public Property Get Filled() As Boolean
    Filled = pFilled
End Property
Private Property Get EnterExit() As Integer
    Select Case pOrdType
        Case 1
            EnterExit = -1
        Case 2
            EnterExit = -1
        Case 3
            EnterExit = 1
    End Select
End Property
Private Property Get AddSubtract() As Integer
    Select Case pOrdType
        Case 1
            AddSubtract = 1
        Case 2
            AddSubtract = -1
        Case 3
            AddSubtract = -1
    End Select
End Property
Public Property Get Ltr() As String
    Select Case pOrdType
        Case 1
            Ltr = "O"
        Case 2
            Ltr = "S"
        Case 3
            Ltr = "T"
    End Select
End Property
