Attribute VB_Name = "WorkOrders"
'Option Compare Text
Public OpenedFromWarranty As Boolean
Sub showWorkOrders()
    WorkOrder.Show
End Sub
Sub addNewWO()
    OpenedFromWarranty = True
    AddEvent.Show
End Sub

Sub closeWO()
'    On Error GoTo errHandle
    
    MsgBox "This isnt set up yet."
    Exit Sub
'
'    disableCummins
'    Dim aDateReturned As Date
'
'    Application.EnableEvents = False
'    iws = 2
'    loadKeyVars iws, ActiveCell
'    i = ActiveCell.row - tbl.HeaderRowRange.row
'
'    If getMineSite = "FortHills" And dbr.Cells(i, getCol(iws, "Warranty")) <> "No" Then 'Need better logic here!
'        'Check if WO has shipped date
'        aQuery = "SELECT DateReturned FROM EventLog WHERE UID=" & aUID
''        loadDB
'        Set rs = db.OpenRecordset(aQuery, dbOpenDynaset)
'        With rs
'            If IsNull(!DateReturned) Then
'                ans = MsgBox("Has component been returned?", vbYesNo + vbQuestion, "Component returned?")
'                If ans = vbYes Then
'                    aDateReturned = Application.InputBox(prompt:="Enter date:", Title:="Date Returned", Default:=Format(Now, getDateFormat))
'                    If aDateReturned = #12:00:00 AM# Then  'this is returned if user clicks 'cancel'
'                        GoTo cleanup
'
'                        Else
'                        .Edit
'                        !DateReturned = aDateReturned
'                         .Update
'                    End If
'
'                    Else
'                    MsgBox "Work order cannot be closed till component has been returned."
'                    GoTo cleanup
'                End If
'            End If
'            .Close
'        End With
'    End If
'
'    Set Target = dbr.Cells(i, 2)
'    Target.value = "Closed"
'    If dbr.Cells(i, getCol(iws, "DateClosed")) = "" Then dbr.Cells(i, getCol(iws, "DateClosed")) = DateValue(Now)
'
'    updateRecord Target, iws
'
'    emailWORequest False
'cleanup:
'    Application.EnableEvents = True
'    Exit Sub
'errHandle:
'    sendErrMsg " | closeWO"
'    Resume cleanup
End Sub
Sub emailWORequest(OpenClose As Boolean)
    disableCummins
    On Error GoTo errHandle
    Application.ScreenUpdating = False
    loadKeyVars 2, ActiveCell
    
    Select Case OpenClose
        Case True
            Instruction = "Please open a warranty work order for: "
            OpenCloseSubj = "Open"
            Select Case getMineSite
                Case "BaseMine"
                    StartCopy = 6
                    SelectionOffset = 9
                    delDateClosedCol = 7
                Case Else
                    StartCopy = 6
                    SelectionOffset = 12
                    delDateClosedCol = 9
            End Select
        
        Case False
            Instruction = "Please close the following work order: "
            OpenCloseSubj = "Close"
            Select Case getMineSite
                Case "BaseMine"
                    StartCopy = 2
                    SelectionOffset = 13
                Case Else
                    StartCopy = 2
                    SelectionOffset = 15
            End Select

    End Select
    
    strbody = "Good " & getGreeting & "," & vbNewLine & Instruction
    
    highlightRow ClearOnly:=True
    dbr.Rows.Hidden = True
    ActiveCell.Rows.Hidden = False
    tbl.ListColumns(StartCopy).Range.Resize(, SelectionOffset).Copy
    
    Set outlookApp = CreateObject("Outlook.Application")
    Set outMail = outlookApp.CreateItem(olMailItem)
    Set outMail2 = outlookApp.CreateItem(olMailItem)
    
    If aTitle Like "*FC*" Or aTitle Like "*F.C*" Then
        If OpenClose = False Then
            With outMail2
                .To = getEmailList("FCCancelled")
                .cc = "mhonarkhah@smsequip.com"
                .Subject = OpenCloseSubj & " WO Request - " & aUnit & " - " & aTitle
    
                Set wdDoc = .GetInspector.WordEditor
                pasteIntoEmail wdDoc, strbody
                With wdDoc
                    .Tables(1).Columns(11).Delete
                    .Tables(1).Columns(9).Delete
                    .Tables(1).Columns(8).Delete
                    .Tables(1).Columns(4).Delete
                    .Tables(1).Columns(3).Delete
                End With
                .display
            End With
        End If
    End If
    
    With outMail
        .To = getEmailList("WORequest")
        .Subject = OpenCloseSubj & " WO Request - " & aUnit & " - " & aTitle
            'Get Word Editor & Paste
            Set wdDoc = outMail.GetInspector.WordEditor
            pasteIntoEmail wdDoc, strbody
            With wdDoc
                .Tables(1).Rows(1).height = 12
                If OpenClose = True Then .Tables(1).Columns(delDateClosedCol).Delete
            End With
        .display
    End With

cleanup:
    On Error Resume Next
    Application.EnableEvents = True
    Application.CutCopyMode = False
    tbl.Range.Rows.Hidden = False
    ActiveCell.EntireRow.Hidden = False
    Application.ScreenUpdating = True
    Exit Sub
errHandle:
    sendErrMsg "emailWORequest"
    Resume cleanup
End Sub


Sub getWOFromOutlook()
Attribute getWOFromOutlook.VB_ProcData.VB_Invoke_Func = "W\n14"
    On Error GoTo errHandle
    Dim olNs As Object 'Outlook.Namespace
    Dim Fldr As Object ' Outlook.MAPIFolder
    Dim Items As Object 'Outlook.Items
    Dim objMsg As Object 'Outlook.MailItem
    Dim searchAgain As Boolean
    
    disableCummins
    loadKeyVars 2, ActiveCell
    aRow = i
    
    TitleSearch = "WO Request - " & aUnit & " - " & aTitle

    Set outlookApp = CreateObject("Outlook.Application")
    Set olNs = outlookApp.GetNamespace("MAPI")
    Set Fldr = getOutlookFolder(olNs.GetDefaultFolder(6).parent, "Wo Request")
    
searchFolder:
    Set Items = Fldr.Items
    Items.Sort "[ReceivedTime]", False
    MsgCount = Items.Count
    
    MinMsg = 1
    If MsgCount > 301 Then MinMsg = MsgCount - 300
    
    For i = MsgCount To MinMsg Step -1
        With Items(i)
'            Debug.Print i, .Subject
            If .Subject Like "*" & TitleSearch & "*" Then
                dbr.Cells(aRow, 4) = getWOString(Items(i))
                
                'Init an event to check the folder variables
                Set e = createEventTable(ActiveCell) '
                Set EventFolder = createFolder(e)
                GoTo cleanup
            End If
        End With
    Next i
    
    'try again with inbox
    If searchAgain = False Then
        searchAgain = True
        Set Fldr = olNs.GetDefaultFolder(6) 'olFolderInbox
        GoTo searchFolder
    End If
    
    ans = MsgBox("Could not find correct email in 'Inbox' or 'WO Request' Folder. Would you like to manually select email?", vbYesNo, "Can't Find WO Email")
    If ans = vbYes Then
        outlookApp.ActiveExplorer.display
        MsgBox "Press ok when email is selected."
        Set objMsg = outlookApp.ActiveExplorer.Selection(1)
        dbr.Cells(aRow, 4) = getWOString(objMsg)
        Else
        GoTo cleanup
    End If
    
cleanup:
    Exit Sub
errHandle:
    sendErrMsg "getWOFromOutlook"
    Resume cleanup
End Sub
Function getWOString(objMsg) As String
    On Error GoTo errHandle
    Dim woStart As Long
    With objMsg
        woNum = " "
        woStart = 1
        lenBody = Len(.HTMLBody)
                
        Do While IsNumeric(woNum) <> True
            woStart = InStr(woStart, .HTMLBody, "wo", vbTextCompare)
            If woStart = 0 Then
                ans = MsgBox("Could not find WO number in email: '" & .Subject & "'." & dLine & _
                        "Would you like to show the email?", vbYesNo + vbQuestion, "Missing WO Number")
                If ans = vbYes Then .display
                GoTo cleanup
            End If
'            Debug.Print "woStart", woStart
            woNum = Mid(.HTMLBody, woStart + 2, 7)
'            Debug.Print "woNum", woNum
            woStart = woStart + 1
        Loop

        getWOString = Mid(.HTMLBody, woStart - 1, 9)
    End With
cleanup:
    Exit Function
errHandle:
    getWOString = ""
    sendErrMsg "getWOString"
    Resume cleanup
End Function
Sub emailPRP()
    On Error GoTo errHandle
    disableCummins
    Application.ScreenUpdating = False
    loadKeyVars 2, ActiveCell
    
    Set outlookApp = CreateObject("Outlook.Application")
    Set outMail = outlookApp.CreateItem(olMailItem)
    
    strbody = "Good " & getGreeting & ", " & dLine & "The following component has been returned: "
    
    highlightRow ClearOnly:=True
    dbr.Rows.Hidden = True
    ActiveCell.Rows.Hidden = False
    StartCopy = 2
    SelectionOffset = 15
    tbl.ListColumns(StartCopy).Range.Resize(, SelectionOffset).Copy
    
    With outMail
        .To = getEmailList("PRP")
        .Subject = "PRP Return - " & aUnit & " - " & aTitle
        Set wdDoc = .GetInspector.WordEditor
        pasteIntoEmail wdDoc, strbody
        .display
    End With
    
cleanup:
    On Error Resume Next
    Application.EnableEvents = True
    Application.CutCopyMode = False
    tbl.Range.Rows.Hidden = False
    ActiveCell.EntireRow.Hidden = False
    Application.ScreenUpdating = True
    Exit Sub
errHandle:
    sendErrMsg "emailPRP"
    Resume cleanup
End Sub
Sub emailComponentReturns()
    disableCummins
    Application.ScreenUpdating = False
    setTblVars 2
    RefreshTable "ComponentReturns"
    highlightRow ClearOnly:=True
    
    strbody = "Good " & getGreeting & ", " & dLine & "The following components have been returned this week: "
    
    StartCopy = 2
    SelectionOffset = 15
    tbl.ListColumns(StartCopy).Range.Resize(, SelectionOffset).Copy
    
    Set outlookApp = CreateObject("Outlook.Application")
    Set outMail = outlookApp.CreateItem(olMailItem)
    With outMail
        .To = getEmailList("PRP")
        .Subject = "Component Returns - "
        Set wdDoc = .GetInspector.WordEditor
        pasteIntoEmail wdDoc, strbody
        .display
    End With
    
cleanup:
    On Error Resume Next
    Application.EnableEvents = True
    Application.CutCopyMode = False
    Application.ScreenUpdating = True
    Exit Sub
errHandle:
    sendErrMsg "emailComponentReturns"
    Resume cleanup
End Sub
