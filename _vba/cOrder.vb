
Public ClOrdID As String
Public OrderID As String
Public symbol As String

Private pSide As String
Private pStopPx As Double
Private pPrice As Double
Private pOrderQty As Long
Private pTimeStamp As Date

Public Enum eOrd
    StopBuy
    StopClose
    LimitIfTouchedEnter
    LimitClose
    StopCloseMeanRev
End Enum

Public Sub initJson(jobOrder As cJobject)
    
'    Debug.Print "*---------------------------------------------*"
'    Debug.Print jobOrder.stringify(True)
    
    With jobOrder
        OrderID = .child("orderID").Value
        ClOrdID = .child("orderID").Value
        symbol = .child("symbol").Value
        StopPx = .child("stopPx").Value
        Price = .child("price").Value
        pSide = .child("side").Value
        OrderQty = .child("orderQty").Value
        TimeStamp = .child("timestamp").Value
    End With
    
End Sub

Public Property Get OrdType() As Long
    Select Case True
        Case ClOrdID Like "*StopClose*" 'StopClose
            OrdType = StopClose
            
        Case ClOrdID Like "*StopBuy*" 'StopBuy
            OrdType = StopBuy
        
        Case ClOrdID Like "*LimitIfTouchedEnter*" 'LimitIfTouchedEnter
            OrdType = LimitIfTouchedEnter
             
        Case ClOrdID Like "*LimitClose*" 'LimitClose
            OrdType = LimitClose
            
        Case ClOrdID Like "*StopCloseMeanRev*" 'StopCloseMeanRev
            OrdType = StopCloseMeanRev
            
    End Select
End Property

'Properties
Public Property Get StopPx() As Variant 'stopPx
    StopPx = pStopPx
End Property
Public Property Let StopPx(ByVal dstopPx As Variant)
    If IsNumeric(dstopPx) Then
        pStopPx = dstopPx
        Else
        pStopPx = 0
    End If
End Property

Public Property Get Price() As Variant 'Price
    Price = pPrice
End Property
Public Property Let Price(ByVal dPrice As Variant)
    If IsNumeric(dPrice) Then
        pPrice = dPrice
        Else
        pPrice = 0
    End If
End Property

Public Property Get OrderQty() As Variant 'OrderQty
    If pSide = "Sell" Then
        OrderQty = CLng("-" & pOrderQty)
        Else
        OrderQty = pOrderQty
    End If
End Property
Public Property Let OrderQty(ByVal dOrderQty As Variant)
    If IsNumeric(dOrderQty) Then
        pOrderQty = CLng(dOrderQty)
        Else
        pOrderQty = 0
    End If
End Property

Public Property Get TimeStamp() As Variant 'TimeStamp
    TimeStamp = pTimeStamp
End Property
Public Property Let TimeStamp(ByVal dTimeStamp As Variant)
    
    If isIso(CStr(dTimeStamp)) Then
        pTimeStamp = UtcConverter.ParseIso(CStr(dTimeStamp))
        ElseIf IsDate(dTimeStamp) Then
        pTimeStamp = dTimeStamp
            Else
        
    End If
End Property

Public Function Age() As Integer 'add intervals? seconds?
    If Not pTimeStamp = 0 Then Age = Minute(Now - pTimeStamp)
End Function
Private Sub class_initialize()
    ClOrdID = ""
    OrderID = ""
    pStopPx = 0#
    pstopPxNew = 0#
    pPrice = 0#
    pPriceNew = 0#
    pOrderQty = 0
    pOrderQtyNew = 0#
    
End Sub
