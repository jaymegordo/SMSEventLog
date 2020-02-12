Public Enum ch
    Jambot
    Vol
    Orders
End Enum

Private Function getChannel(Channel As Long)
    Select Case Channel
        Case 0
            getChannel = "https://discordapp.com/api/webhooks/506472880620568576/o1EkqIpGizc5ewUyjivFeEAkvgbU_91qr6Pi-FDLP0qCzu-j7yNFc9vskULJ53JZ6aC1"
        Case 1
            getChannel = "https://discordapp.com/api/webhooks/512030769775116319/s746HqzlZGedOfnSmgDeC8HJJT_5-bYcgUbgs8KWwvb6gw38gGR_WhQylFKdcWtGyTHi"
        Case 2
            getChannel = "https://discordapp.com/api/webhooks/546699038704140329/95ZgQfMEv7sj8qGGUciuaMmjHJuxpskG-0nYjOCSZCGBnnSr93MBj7j9_R7nfC1f3AIC"
    End Select
End Function

Sub sendMessage(Channel As Long, Message As String)
    On Error GoTo errHandle
    If Len(Message) > 2000 Then Err.Raise 2000, , "Discord message > 2000 characters"
    
    Dim JSONPayload As String
    JSONPayload = "{""content"":""" & Message & """}"
'    PRNT "len", Len(JSONPayload)
'    PRNT "JsonPayload", JSONPayload
    
    Dim httpObj As New MSXML2.XMLHTTP
    Set httpObj = CreateObject("MSXML2.XMLHTTP")
    With httpObj
        .Open "POST", getChannel(Channel), False
        '.Open "GET", aWebhook, False
        .setRequestHeader "Content-Type", "application/json"
        .send (JSONPayload)
        'PRNT "ResponseText", .ResponseText
    End With
cleanup:
    Set httpObj = Nothing
    Exit Sub
errHandle:
    If Err.Number = -2147467260 Then Resume cleanup
    Debug.Print Err.Number
End Sub
