Public Name As String
Public NameShort As String
Public collSymbols As Collection
Public PercentBalance As Double
Public gRow As Integer
Public AvailableMargin As Double
Public TotalBalanceMargin As Double
Public TotalBalanceWallet As Double
Public UnrealisedPnl As Double

Private pSym As cSymbol
Private pOrder As cOrder
Private pCollOrders As Collection
Private pBitmex As cBitmex
Private papiKey As String
Private papiSecret As String
Private pTestnet As Boolean

Private Sub class_initialize()
    Set collSymbols = New Collection
    Set pCollOrders = New Collection
    AvailableMargin = 0
    TotalBalanceMargin = 0
    TotalBalanceWallet = 0
    UnrealisedPnl = 0
End Sub

Public Property Get apiKey() As String
    apiKey = papiKey
End Property

Public Property Get apiSecret() As String
    apiSecret = papiSecret
End Property

Public Property Get Bitmex() As cBitmex
    If pBitmex Is Nothing Then Set pBitmex = New cBitmex
    Set Bitmex = pBitmex
End Property

Public Property Set Bitmex(ByVal oBitmex As cBitmex)
    Set pBitmex = oBitmex
End Property

Public Property Get Testnet() As Boolean
    Testnet = pTestnet
End Property

Public Sub addOrder(jobOrder As cJobject)
    Set pOrder = New cOrder
    pOrder.initJson jobOrder
    pCollOrders.add pOrder
End Sub

Public Sub addOrders(jobOrders As cJobject)
    For i = 1 To jobOrders.children.count
        addOrder jobOrders.children(i)
    Next i
End Sub

Public Sub clearOrders()
    Set pCollOrders = New Collection
End Sub

Public Function collFilledOrders() As Collection
    Set collFilledOrders = pCollOrders
End Function

Public Function getSymbol(SymbolBitmex As String) As cSymbol
    For Each pSym In collSymbols
        If pSym.SymbolBitmex = SymbolBitmex Then
            Set getSymbol = pSym
            Exit Function
        End If
    Next
End Function

Public Function hasSymbol(SymbolBitmex As String) As Boolean
    For Each pSym In collSymbols
        If pSym.SymbolBitmex = SymbolBitmex Then
            hasSymbol = True
            Exit Function
        End If
    Next
    hasSymbol = False
End Function

Public Sub initFromDB(rsUser As ADODB.Recordset)
    On Error GoTo errHandle
    With rsUser
        .Filter = "UserShort='" & Me.NameShort & "'"
        pTestnet = !Testnet
        Me.Name = !User
        Select Case getRemoteServer
            Case True
                papiKey = !apiKeyRemote
                papiSecret = !apiSecretRemote
            Case False
                papiKey = !apiKeyLocal
                papiSecret = !apiSecretLocal
        End Select
    End With
    
cleanup:
    On Error Resume Next
    Exit Sub
errHandle:
    sendErrMsg "initFromDB"
    Resume cleanup
End Sub

Public Function isInit() As Boolean
    If papiKey <> "" And papiSecret <> "" Then
        isInit = True
        Else
        isInit = False
    End If
End Function

Public Sub printSymbols()
    For Each pSym In collSymbols
        Debug.Print pSym.Name, pSym.NameSimple, pSym.SymbolBitmex
    Next
End Sub
