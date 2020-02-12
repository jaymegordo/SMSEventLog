Attribute VB_Name = "Functions_PicsDLS"



Function getTablePicsDLS(fType) 'merge with other getTable
    Select Case fType
        Case "fault0"
            getTable = "Fault Code Database"
        Case "haul"
            getTable = "PLM Database"
    End Select
End Function

Function sendErrMsg_PicsDLS(Optional ErrType, Optional aUnit, Optional ErrMsg, Optional aFile)

    If IsMissing(ErrType) Then ErrType = "Fault"
    If IsMissing(ErrMsg) Then ErrMsg = ""
    'If IsMissing(aUnit) Then aUnit = ""
    
    If Err.Number <> 0 Then
        aMessage = "Error: " & Err.Number & " | " & Err.Description & " | " & ErrMsg
        Err.clear
    End If
    Debug.Print "aMessage: "; aMessage & " | sendErrMsg_PicsDLS"
    If Application.UserName = "Jayme Gordon" Then Exit Function
    
    Dim outlookApp As Object 'Outlook.Application
    Set outlookApp = CreateObject("Outlook.Application")
    Dim outMail As Object 'Outlook.MailItem
    Set outMail = outlookApp.CreateItem(olMailItem)
    
    With outMail
        .To = "mhonarkhah@smsequip.com; jdewaal@smsequip.com; macarter@smsequip.com; mdegiano@smsequip.com; clemoignan@smsequip.com"
        Select Case ErrType
            Case "plmMissing"
                .Subject = "PLM Missing Unit - " & aUnit
                .HTMLBody = "<a href=""" & aFile & """>" & aFile & "</a > "
            Case "Fault"
                .Subject = "Import Error - " & aUnit & " - " & Format(Now, "dd-Mmm-yyyy hh:nn")
                .HTMLBody = aMessage
        End Select
        .send
    End With
    
    Set outlookApp = Nothing
    Set outMail = Nothing
    
End Function



