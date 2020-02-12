
Private pBalance As Double
Private pMax As Double
Private pCollTxns As Collection
Private pTxn As cTxn
Public Enum wm
    wk
    mth
End Enum

Private Sub class_initialize()
    pBalance = 1
    Set pCollTxns = New Collection
End Sub

Public Property Get Balance() As Double
    If pBalance < 0.01 Then
        Balance = Round(0.01, 3)
        Else
        Balance = Round(pBalance, 3)
    End If
End Property
Public Property Get Max() As Double
    Max = Round(pMax, 3)
End Property

Public Sub modify(xbt As Double, dtTimeStamp As Date)
    Set pTxn = New cTxn
    With pTxn
        .Amount = xbt
        .DateTx = dtTimeStamp
        .AcctBalance = Me.Balance
    End With
    pCollTxns.add pTxn
    pBalance = pBalance + xbt
    If pBalance > pMax Then pMax = pBalance
End Sub
Public Sub reset()
    pBalance = 1
End Sub

Public Sub printTxns()
    For Each pTxn In pCollTxns
        pTxn.printTxn
    Next pTxn
End Sub

Public Sub printSummary(Optional lType As Long = wm.mth)
    Dim iPeriod As Integer
    Dim prevTxn As cTxn
    iPeriod = getPeriodNum(lType, pCollTxns.Item(1).DateTx)
    For Each pTxn In pCollTxns
        If getPeriodNum(lType, pTxn.DateTx) <> iPeriod Then
            If prevTxn Is Nothing Then Set prevTxn = pTxn
            Debug.Print iPeriod, pTxn.AcctBalance, Round(aChange, 3), getPercentChange(prevTxn.AcctBalance, CDbl(aChange))
            Set prevTxn = pTxn
            aChange = 0
            iPeriod = getPeriodNum(lType, pTxn.DateTx)
        End If
        aChange = aChange + pTxn.Amount
        
    Next pTxn
End Sub
Private Function getPeriodNum(lType As Long, dtTimeStamp As Date) As Integer
    Select Case lType
        Case mth
            getPeriodNum = month(dtTimeStamp)
        Case wk
            getPeriodNum = Application.WorksheetFunction.WeekNum(dtTimeStamp)
    End Select
End Function
Private Function getPercentChange(Balance As Double, Change As Double) As String
    getPercentChange = Format(Change / Balance, "Percent")
End Function

