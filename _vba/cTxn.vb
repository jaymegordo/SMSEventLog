Private pDateTx As Date
Private pAmount As Double
Private pAcctBalance As Double


Public Property Get Amount() As Double
    Amount = Round(pAmount, 3)
End Property

Public Property Let Amount(ByVal dAmount As Double)
    pAmount = dAmount
End Property

Public Property Get DateTx() As Date
    DateTx = pDateTx
End Property

Public Property Let DateTx(ByVal dtDateTx As Date)
    pDateTx = dtDateTx
End Property

Public Sub printTxn()
    Debug.Print Format(Me.DateTx, "yyyy-mm-dd HH"), Me.AcctBalance, Me.Amount
End Sub

Public Property Get AcctBalance() As Double
    AcctBalance = pAcctBalance
End Property

Public Property Let AcctBalance(ByVal dAcctBalance As Double)
    pAcctBalance = dAcctBalance
End Property