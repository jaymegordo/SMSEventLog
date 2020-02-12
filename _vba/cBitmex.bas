'Option Explicit
Public verb, Signature, postdata, symbol, url, replyText, nonceStr As String
Public nonce As Double
Public json As Object
Public job As cJobject
Public JsonCount As Integer
Dim OrderID As Variant
Dim aSymbol As String
Public FundingTime As Date

Private pstrFilter As String
Private pUser As cUser
Private pUrlBase As String


Private Property Get UrlBase() As String
    UrlBase = pUrlBase
End Property
Private Property Let UrlBase(ByVal sUrlBase As String)
    pUrlBase = sUrlBase
End Property
Public Property Get User() As cUser
    Set User = pUser
End Property
Public Property Set User(oUser As cUser)
    Set pUser = oUser
    If pUser.Testnet Then
        pUrlBase = "https://testnet.bitmex.com"
        Else
        pUrlBase = "https://www.bitmex.com"
    End If
End Property

Public Sub amendStopLimit(symbol As cSymbol)
    On Error GoTo errHandle
    Dim XBTPnL As Double
    Dim LimitClosePrice As Double

'    PRNT "--------------", Symbol.SymbolBitmex
    tStamp = "-" & getNonce
    
    PRNT "stopPx", symbol.StopPx
    If symbol.PositionQty * symbol.LongShortNew > 0 And Not MeanRevNext Then 'Opposite of the bot
        strOppPosition = pUser.Name & " - " & symbol.SymbolBitmex & " " & getPositionSide(symbol.PositionQty) & ", stops not adjusted."
        PRNT "strOppPosition", strOppPosition
        Discord.sendMessage ch.Orders, CStr(strOppPosition)
        GoTo cleanup ' need to check to make sure StopClose exists
    End If
    
    Select Case MeanRevCurrent
        Case False 'Amend current StopClose
'            If getStopCloseOn = True Then
'                stopPx = getStopClosePrice
'                ElseIf getManStopOn = True Then
'                    stopPx = getManStopPrice(LongShort * -1)
'            End If
            If Round(symbol.StopPx, 8) = Round(symbol.Order(StopClose).StopPx, 8) And _
               Abs(symbol.PositionQty) = symbol.Order(StopClose).OrderQty Then
                PRNT "StopClose amount and stopPX equal, don't adjust."
                GoTo setStopBuy
            End If
            
            If symbol.PositionQty <> 0 Then
                If symbol.PositionQty * symbol.LongShortNew > 0 Then 'already in position, dont chage it /// make Symbol.InPosition??
                    PRNT "Already in position, goto StopBuy"
                    GoTo setStopBuy
                End If
                
                If symbol.Order(StopClose).OrderID <> "" Then 'Amend StopClose
                    PRNT "      Amend StopClose", symbol.Order(StopClose).OrderID
                    postdata = "orderID=" & symbol.Order(StopClose).OrderID & "&orderQty=" & symbol.OrderQtyStopClose & "&stopPx=" & symbol.StopPx
                    response = BitmexMain("amendOrder", postdata)
                    PRNT "Response", response
                    
                    Else 'Post new StopClose
                    PRNT "Post new StopClose"
                    postOrder "Stop", symbol:=symbol.SymbolBitmex, StopPx:=symbol.StopPx, execInst:="Close,IndexPrice", OrderQty:=symbol.OrderQtyStopClose, ClOrdID:="StopClose" & tStamp
                End If
                
                Else
                If symbol.Order(StopClose).OrderID <> "" Then
                    CancelOrder "Single", symbol.Order(StopClose).OrderID
                    PRNT "StopClose with no corresponding position closed."
                End If
            End If
        
        Case True ' MeanRev = true
            LimitClosePrice = symbol.TargetPrice ' this should probably go into Symbol?
            XBTPnL = getXBTPnlAtTarget(symbol)
            NextPositionNewContracts = CLng(getContracts((pUser.TotalBalanceWallet + XBTPnL), symbol.Leverage, symbol.TargetPrice, symbol.LongShort, symbol.AltStatus) _
                                        * pUser.PercentBalance * symbol.PercentBalance * symbol.Confidence)
            'NextPositionNewContracts = 425 'kill
            
            If Abs(NextPositionNewContracts) > Abs(symbol.PositionQty) Then
                PRNT "Next position contracts > current position. Don't set limit close."
                GoTo setStopBuy
            End If
            
            LimitCloseNewContracts = CLng(-1 * (symbol.PositionQty - NextPositionNewContracts)) ' Confirm if this math is right
            
            PRNT "NextPositionNewContracts", NextPositionNewContracts
            PRNT "LimitCloseNewContracts", LimitCloseNewContracts
            
            'LimitCloseNewContracts = 500 'kill
            
            If symbol.Order(LimitIfTouchedEnter).OrderID = "" And symbol.PositionQty <> 0 Then 'LimitEnter filled > good, check LimitClose
                
                If symbol.Order(StopCloseMeanRev).OrderID = "" Then 'Set new MeanRev StopClose
                    PRNT "Post new MeanRev StopClose."
                    MeanRevStopClosePrice = CLng(symbol.AvgEntryPrice + symbol.AvgEntryPrice * symbol.LongShortNew * 0.1) 'stop out at -10%
                    PRNT "Current Position Qty", symbol.PositionQty 'kill
                    postOrder "Stop", symbol:=symbol.SymbolBitmex, StopPx:=MeanRevStopClosePrice, execInst:="Close,IndexPrice", OrderQty:=symbol.OrderQtyStopClose, ClOrdID:="StopCloseMeanRev" & tStamp
                End If
                
                If symbol.Order(LimitClose).OrderID = "" Then 'Set new LimitClose
                    PRNT "Post new MeanRev LimitClose."
                    postOrder "Limit", symbol:=symbol.SymbolBitmex, Price:=LimitClosePrice, OrderQty:=LimitCloseNewContracts, ClOrdID:="LimitClose" & tStamp
                    
                    ElseIf Bitmex.PriceMeanRev = LimitClosePrice And Bitmex.OrderQtyMeanRev = LimitCloseNewContracts Then
                        PRNT "LimitClose price and OrderQty equal, don't adjust."
                        
                        Else 'Amend LimitClose
                        postdata = "orderID=" & symbol.Order(LimitClose).OrderID & "&orderQty=" & LimitCloseNewContracts & "&price=" & LimitClosePrice
                        response = BitmexMain("amendOrder", postdata)
                        PRNT "Response", response
                End If
                
                Else
                PRNT "LimitBuy not filled yet." '-->Don't set LimitClose -->Need to stop adjusting LimitBuy and wait now?
                PRNT "OrderID LimitBuy", symbol.Order(LimitIfTouchedEnter).OrderID
            End If
    End Select

'STOP BUY
setStopBuy:
    'Amend new StopBuy order contracts (# contracts varies based on TotalWallet +/- PnL and emaConfidence)
    
    Select Case MeanRevNext
        Case False
            'If MeanRevCurrent Then LongShort = LongShort * -1  'Keep stopbuy on the same side, doesnt affect MeanRev LimitBuy, already in a MeanRev Position
'            If getManStopOn = True Then
'                stopPx = getManStopPrice(LongShort * -1)
'                Else
'                stopPx = TargetPrice
'            End If
            
            XBTPnL = getXBTPnlAtTarget(symbol)
'            PRNT "XBTPnL", XBTPnL
'            PRNT "TotalBalanceWallet", TotalBalanceWallet
'            PRNT "TargetPrice", TargetPrice
'            PRNT "StopBuy LongShort", LongShort
            symbol.OrderQtyStopBuy = getContracts((pUser.TotalBalanceWallet + XBTPnL), symbol.Leverage, symbol.TargetPrice, symbol.LongShortNew, symbol.AltStatus) _
                                        * pUser.PercentBalance * symbol.PercentBalance * symbol.Confidence
            
            If MeanRevCurrent Then
                If Abs(symbol.OrderQtyStopBuy) < Abs(symbol.PositionQty) Then 'addNewContracts to the cSymbol?
                    GoTo cleanup 'don't need a StopBuy
                    Else
                    symbol.OrderQtyStopBuy = (Abs(symbol.OrderQtyStopBuy) - Abs(symbol.PositionQty)) * symbol.LongShortNew
                End If
            End If
            PRNT "Symbol.OrderQtyStopBuy", symbol.OrderQtyStopBuy
            
            If symbol.Order(StopBuy).OrderID = "" Then 'Set new StopBuy
                PRNT "Post new StopBuy."
                postOrder "Stop", symbol:=symbol.SymbolBitmex, StopPx:=symbol.StopPx, execInst:="IndexPrice", OrderQty:=symbol.OrderQtyStopBuy, ClOrdID:="StopBuy" & tStamp ', clOrdLinkID:="abc123"

                ElseIf Round(symbol.StopPx, 8) = Round(symbol.Order(StopBuy).StopPx, 8) And symbol.Order(StopBuy).OrderQty = Abs(symbol.OrderQtyStopBuy) Then
                    PRNT "StopBuy equal, don't adjust."
                    GoTo cleanup
                    
                    Else 'Amend StopBuy
                    PRNT "      Amend StopBuy", symbol.Order(StopBuy).OrderID
                    postdata = "orderID=" & symbol.Order(StopBuy).OrderID & "&orderQty=" & symbol.OrderQtyStopBuy & "&stopPx=" & symbol.StopPx
                    response = BitmexMain("amendOrder", postdata)
            End If
                
        Case True 'Check MeanRev LimitIfTouchedEnter
           PRNT "Limit buy ordID", Symbol.Order(LimitIfTouchedEnter).OrderID
           TargetPriceMeanRev = CLng(Symbol.TargetPrice * (1 + 0.005 * Symbol.LongShortNew)) 'set at +/-0.5%
           XBTPnL = getXBTPnlAtTarget(Symbol.TargetPrice)

           'FIX THIS
           Bitmex.NewContracts = pUser.PercentBalance * LongShort * -1 * Leverage * TargetPriceMeanRev * (pUser.TotalBalanceWallet + XBTPnL) * Symbol.Confidence

           If Symbol.Order(LimitIfTouchedEnter).OrderID = "" Then 'Set new LimitIfTouchedEnter > trigger price has to be higher than close but lower than limit price
               PRNT "Post new LimitIfTouchedEnter", Symbol.Order(LimitIfTouchedEnter).OrderID
               postOrder ordType:="LimitIfTouched", Symbol:=Symbol, Price:=TargetPriceMeanRev, stopPx:=TargetPrice, OrderQty:=Bitmex.NewContracts, execInst:="IndexPrice", ClOrdID:="LimitIfTouchedEnter" & tStamp

               ElseIf Bitmex.PriceMeanRev = TargetPriceMeanRev And Bitmex.OrderQtyMeanRev = Abs(Bitmex.NewContracts) Then
                   PRNT "LimitIfTouchedEnter price and OrderQty equal, don't adjust. Order not filled yet."
                   GoTo cleanup

                   Else 'Amend LimitBuy
                   postdata = "orderID=" & Symbol.Order(LimitIfTouchedEnter).OrderID & "&orderQty=" & Bitmex.NewContracts & "&price=" & TargetPriceMeanRev
                   response = BitmexMain("amendOrder", postdata)
                   PRNT "Amend LimitIfTouchedEnter", response
           End If
    End Select
    
cleanup:
    On Error Resume Next
    XBTPnL = 0
    Exit Sub
errHandle:
    sendErrMsg "AmendStopLimit"
    Resume cleanup
End Sub



Private Function getNonce()
    If nonce = 0 Then
        nonce = DateDiff("s", "1/1/1970", JsonConverter.ConvertToUtc(Now))
        Else
        nonce = nonce + 1
    End If
    getNonce = nonce
End Function
Public Function getOpenPosition()
    BitmexMain "getOpenPosition"
End Function
Public Function getOpenOrders()
    BitmexMain "getOpenOrders"
End Function
Public Function getFilledOrders(Optional ordStatus As String, Optional startTime As Date, Optional numOrders As Integer) As cJobject ' should just change to get orders
    On Error GoTo errHandle
    ordStatus = "Filled" 'always filled for now
    If ordStatus <> "" Then pstrFilter = "~ordStatus~:~" & ordStatus & "~,"
    If IsDate(startTime) Then pstrFilter = pstrFilter & " ~startTime~:~" & Format(startTime, "yyyy-mm-dd hh:nn") & "~"
    
    If Right(pstrFilter, 1) = "," Then pstrFilter = Left(pstrFilter, Len(pstrFilter) - 1) 'chop last comma > should really make this a funciton!!
'    Debug.Print "pstrFilter", pstrFilter
    
    pstrFilter = EncodeReplace("{" & pstrFilter & "}") & "&reverse=true"
    If numOrders > 0 Then pstrFilter = pstrFilter & "&count=" & numOrders
    
    Set getFilledOrders = BitmexMain("getFilledOrders")

cleanup:
    On Error Resume Next
    Exit Function
errHandle:
    sendErrMsg "getFilledOrders"
    Resume cleanup
End Function
Public Function getTotalBalance()
    BitmexMain "getTotalBalance"
End Function
'Sub CloseOpenOrderMarket()
'    'If no qty specified, closes entire position
'    Symbol = "XBTUSD"
'    execInst = "Close"
'    'price = 8400
'    ordType = "Market"
'
'    ordStatus = BitmexMain("closeOrder", , Symbol, , , , ordType, execInst)
'    Debug.Print ordStatus 'return params for market or limit?
'
'End Sub

Public Function getFunding() As Double
    getFunding = BitmexMain("getFunding")
End Function
Public Function getPositionSide(lPositionQty)
    Select Case lPositionQty
        Case Is > 0
            getPositionSide = "Long"
        Case Is < 0
            getPositionSide = "Short"
        Case Is = 0
            getPositionSide = "Neutral"
    End Select
End Function
Sub CancelOrder(SingleAll As String, Optional OrderID)
    On Error GoTo errHandle
    Select Case SingleAll
        Case "Single"
            postdata = "orderID=" & OrderID
            response = BitmexMain("cancelSingle", postdata)
        Case "All"
            response = BitmexMain("cancelAll")
    End Select
            
    If response = True Then
        Debug.Print "Order(s) successfully cancelled."
        Else
        Err.Raise 400, Description:="ERROR! ORDER(S) NOT CANCELLED."
    End If
    
cleanup:
    On Error Resume Next
    Exit Sub
errHandle:
    sendErrMsg "CancelOrder"
    Resume cleanup
End Sub
Function getXBTPnlAtTarget(symbol As cSymbol) As Double
    On Error GoTo errHandle
    With symbol
        If .AvgEntryPrice <> 0 Then
            PRNT "avgEntry", .AvgEntryPrice
            getXBTPnlAtTarget = getPnlXBT(.PositionQty, .AvgEntryPrice, .TargetPrice, .AltStatus)
            Else
            getXBTPnlAtTarget = 0
        End If
    End With
    PRNT "XBTPnL", getXBTPnlAtTarget
cleanup:
    On Error Resume Next
    Exit Function
errHandle:
    sendErrMsg "getXBTPnlAtTarget"
    Resume cleanup
End Function
Sub postOrderMarket(OrderQty) ' make postorder market and limit share return variables
    symbol = "XBTUSD"
    OrdType = "Market"
    
    postdata = "symbol=" & symbol & "&quantity=" & OrderQty & "&ordType=" & OrdType
    OrderStatus = BitmexMain("postOrder", postdata)
    Debug.Print OrderStatus
End Sub
Sub BuyMarket()
    postOrder "Buy", "Market" 'this doesnt work
End Sub
Sub BuyLimit(Price, LongShort)
    postOrder "Limit", Price, LongShort:=LongShort
End Sub
Sub SetStopLimit(Price, StopPx, Optional ByVal LongShort)
'    If LongShort <> -1 Then LongShort = 1
    postOrder "StopLimit", Price, StopPx, execInst:="IndexPrice", LongShort:=LongShort
End Sub
Function postOrder(OrdType, Optional Price, Optional StopPx, Optional execInst, Optional OrderQty, Optional ClOrdID As String, Optional LongShort, Optional symbol)
    'Buys max position value, needs price to work
    
    On Error GoTo errHandle
    Leverage = 5
    'If Symbol = "" Then Symbol = "XBTUSD"
    
    ErrPos = "OrderQtyCheck"
    If IsNumeric(OrderQty) = False Then
        
        'AvailBalance = BitmexMain("GetAvailBalance") / 100000000# 'just use getOpenPosition to set this
        
        OrderQty = CLng(pUser.AvailableMargin * Leverage * Price * (1 - 0.0083) * LongShort * 0.99)
        Debug.Print "Set max OrderQty: " & OrderQty
    End If
    
    If OrderQty = 0 Then GoTo cleanup
    
    ErrPos = "postdata"
    Select Case OrdType
        Case "Limit"
            postdata = "symbol=" & symbol & "&price=" & Price & "&quantity=" & OrderQty & "&ordType=Limit"
        Case "Market"
            postdata = "symbol=" & symbol & "&quantity=" & OrderQty & "&ordType=" & OrdType
        Case "Stop"
            postdata = "symbol=" & symbol & "&stopPx=" & StopPx _
                        & "&quantity=" & OrderQty & "&ordType=" & OrdType & "&execInst=" & execInst & "&clOrdID=" & ClOrdID
        Case "StopLimit"
            postdata = "symbol=" & symbol & "&price=" & Price & "&stopPx=" & StopPx _
                        & "&quantity=" & OrderQty & "&ordType=" & OrdType & "&execInst=" & execInst & "&clOrdID=" & ClOrdID
        Case "LimitIfTouched"
            postdata = "symbol=" & symbol & "&price=" & Price & "&stopPx=" & StopPx _
                        & "&quantity=" & OrderQty & "&ordType=" & OrdType & "&execInst=" & execInst & "&clOrdID=" & ClOrdID
    End Select

    BitmexMain "postOrder", postdata
    
    PRNT "orderStatus", json("ordStatus")
    PRNT "  symbol", json("symbol")
    PRNT "  price", json("price")
    PRNT "  stopPx", json("stopPx")
    PRNT "  orderQty", Format(json("orderQty"), "#,###")
    PRNT "  orderID", json("orderID")
    
cleanup:
    On Error Resume Next
    OrderQty = Null
    ErrPos = ""
    Exit Function
errHandle:
    sendErrMsg "postOrder - " & ErrPos
    Resume cleanup
End Function

Public Function BitmexMain(RequestType, Optional postdata, Optional symbol, Optional Price, _
                 Optional OrdType, Optional execInst, Optional BulkOrder As String) As Variant
    
    PRNT "RequestType", RequestType
    On Error GoTo errHandle
    Dim ReCount As Integer
    Dim replyText As String
    
    ReCount = 0
    If IsMissing(symbol) Then symbol = "XBTUSD"
    
    ErrPos = "RequestType"
    Select Case RequestType
        Case "postOrder"
            verb = "POST"
            url = "/api/v1/order"
        
        Case "postOrderBulk"
            verb = "POST"
            url = "/api/v1/order/bulk?orders=" & BulkOrder
            
        Case "amendOrderBulk"
            verb = "PUT"
            url = "/api/v1/order/bulk?orders=" & BulkOrder
            
        Case "deleteOrderBulk"
            verb = "DELETE"
            url = "/api/v1/order?orderID=" & BulkOrder

        Case "getOpenOrdersP2"
            verb = "GET"
            url = "/api/v1/order?symbol=" & symbol & "&filter=%7B%22open%22%3A%20true%7D&count=100&reverse=false"
        
        Case "getOpenOrders"
            verb = "GET"
            url = "/api/v1/order?filter=%7B%22ordStatus%22%3A%22New%22%7D&count=100&reverse=true"
        
        Case "getFilledOrders"
            verb = "GET"
            url = "/api/v1/order?filter=" & pstrFilter
            
        Case "amendOrder"
            verb = "PUT"
            url = "/api/v1/order"
        
        Case "closeOrder"
            verb = "POST"
            url = "/api/v1/order"
            Select Case OrdType
                Case "Limit"
                    Err.Raise 444, , "Limit close not built yet!!"
                Case "Market"
                    postdata = "symbol=" & symbol & "&ordType=" & OrdType & "&execInst=" & execInst
            End Select
        
        Case "getTotalBalance"
            verb = "GET"
            url = "/api/v1/user/margin?currency=XBt"
            
        Case "getOpenPosition"
            verb = "GET"
            url = "/api/v1/position"
        
        Case "cancelAll"
            verb = "DELETE"
            url = "/api/v1/order/all"
        
        Case "cancelSingle"
            verb = "DELETE"
            url = "/api/v1/order"
            
        Case "getFunding"
            verb = "GET"
            url = "/api/v1/instrument?symbol=" & symbol & ""
            
    End Select
    If IsMissing(postdata) = True Then postdata = ""
    
    'Talk to BitmexMain
    ErrPos = "httpSettings"
    Dim httpObj As Object
    Set httpObj = CreateObject("MSXML2.ServerXMLHTTP")
    
httpConnect:
    nonceStr = getNonce
    ErrPos = "Signature"
    Signature = HexHash(verb + url + nonceStr + postdata, pUser.apiSecret, "SHA256")
    
    ErrPos = "httpConnect"
    With httpObj
        .Open verb, UrlBase & url, False
        .setRequestHeader "If-Modified-Since", nonceStr
        .setRequestHeader "Content-Type", "application/x-www-form-urlencoded"
        .setRequestHeader "api-nonce", nonceStr
        .setRequestHeader "api-key", pUser.apiKey
        .setRequestHeader "api-signature", Signature
        .send (postdata)
        replyText = .responseText
    End With
    
    Set Me.json = JsonConverter.ParseJson(replyText)
    Me.JsonCount = json.count
    'Debug.Print replyText
    
    ErrPos = "httpStatus"
    Select Case httpObj.Status 'Check for response errors
        Case 200 'all good
        Case 503 'system overload, wait 2 seconds then retry
            If ReCount <= 10 Then
                WaitTime = CStr(Round(2 + 0.7 * ReCount, 0))
                Debug.Print "503: retry in " & WaitTime & "s"
                Application.Wait Now + TimeValue("00:00:0" & WaitTime)
                ReCount = ReCount + 1
                GoTo httpConnect
            End If
    End Select
    If httpObj.Status <> 200 Then Err.Raise httpObj.Status, , "Http: " & json("error")("message") & " | " & aUser & "'s stop not adjusted."
    
    ErrPos = "RequestTypeFinal"
    Select Case RequestType
        Case "postOrder"
            BitmexMain = json("ordStatus")
            
        Case "amendOrder"
            BitmexMain = json("text")
                    
        Case "closeOrder"
            BitmexMain = json("ordStatus")
            
        Case "GetOpenOrderQty"
            OpenOrderQty = json(1)("openOrderBuyQty")

        Case "getOpenOrdersP2"
            'Debug.Print replyText
        
        Case "getOpenPosition"
            For i = 1 To Me.JsonCount
                aSymbol = json(i)("symbol")
                If pUser.hasSymbol(aSymbol) Then
                    With pUser.getSymbol(aSymbol)
                        'Debug.Print "name", .Name
                        .AvgEntryPrice = json(i)("avgEntryPrice")
                        .LastPrice = json(i)("lastPrice")
                        .PositionQty = json(i)("currentQty")
                        .UnrealizedPnl = json(i)("unrealisedPnl") / 100000000#
                        .UnrealizedPnlPcnt = json(i)("unrealisedPnlPcnt")
                        .UnrealizedRoePcnt = json(i)("unrealisedRoePcnt")
                        .MaintMargin = json(i)("maintMargin") / 100000000#
                        
    '                    PRNT "Json(i)(unrealisedPnl)", Json(i)("unrealisedPnl")
    '                    PRNT "Json(i)(unrealisedPnlPcnt)", Json(i)("unrealisedPnlPcnt")
    '                    PRNT "Json(i)(unrealizedRoePcnt)", Json(i)("unrealisedRoePcnt")
                    End With
                End If
            Next i
            
        Case "getOpenOrders"
            For i = 1 To Me.JsonCount ' loop all open orders
                aSymbol = json(i)("symbol")
                If pUser.hasSymbol(aSymbol) Then
                    pUser.getSymbol(aSymbol).addOrder _
                        CStr(json(i)("clOrdID")), _
                        CStr(json(i)("orderID")), _
                        json(i)("orderQty"), _
                        json(i)("Price"), _
                        json(i)("stopPx")
                End If
            Next i
        
        Case "getFilledOrders"
            
            Set BitmexMain = JSONParse(replyText)
            GoTo cleanup
            
'            For i = 1 To Bitmex.JsonCount ' loop all open orders
'                aName = json(i)("symbol")
'                If pUser.hasSymbol(aName) Then
'                    pUser.getSymbol(aName).addOrder _
'                        CStr(json(i)("clOrdID")), _
'                        CStr(json(i)("orderID")), _
'                        json(i)("orderQty"), _
'                        json(i)("Price"), _
'                        json(i)("stopPx")
'                End If
'            Next i

        Case "getTotalBalance"
            With pUser
                .AvailableMargin = json("excessMargin") / 100000000# 'total available/unused > only used in postOrder maybe..?
                .TotalBalanceMargin = json("marginBalance") / 100000000# 'unrealized + realized > don't actually use this
                .TotalBalanceWallet = json("walletBalance") / 100000000# 'realized
                .UnrealisedPnl = json("unrealisedPnl") / 100000000#
            End With
            
        Case "cancelAll", "cancelSingle"
            If json(1)("ordStatus") = "Canceled" Then 'This only checks the status of the first order, but should confirm all cancelled
                BitmexMain = True
                Else
                BitmexMain = False
            End If
        
        Case "getFunding"
            BitmexMain = json(1)("fundingRate")
            FundingTime = UtcConverter.ParseIso(CStr(json(1)("fundingTimestamp")))
    End Select
    
cleanup:
    On Error Resume Next
    postdata = ""
    verb = ""
    ReCount = 0
    Set RequestType = Nothing
    Set httpObj = Nothing
    Set Bimex = Nothing
    Exit Function
errHandle:
    sendErrMsg "BitmexMain Function | ErrPos: " & ErrPos & " | RequestType: " & RequestType
    Resume cleanup
End Function

Private Sub class_initialize()
    pNumOrders = 100
'    If aUser = "" Then
'        aUser = getUser
'        initUser aUser
'        Debug.Print "User initialized: " & aUser
'    End If
End Sub
