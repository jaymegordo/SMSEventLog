Attribute VB_Name = "Email"


Function getEmailList(eCol As String) As String 'Needs to come right from the DB!!!
    On Error GoTo errHandle
    
    Query = "SELECT Email FROM EmailList WHERE MineSite ='" & getMineSite & "' AND " & eCol & "='x'"
    
    Dim db As New cDB
    db.OpenConn
    db.rs.Open Query, db.conn, adOpenForwardOnly, adLockReadOnly
    
    With db.rs
        If .RecordCount < 1 Then
            MsgBox "No email addresses found in database for '" & getMineSite & "'.", vbExclamation
            getEmailList = ""
            GoTo cleanup
        End If
        Do While .EOF <> True
            eList = eList & !Email & "; "
            .MoveNext
        Loop
    End With
    
    getEmailList = eList
    
cleanup:
    On Error Resume Next
    db.rs.Close
    Exit Function
errHandle:
    sendErrMsg "getEmailList"
End Function
Sub deleteEmail()
    EmailTable RefreshOnly:=False, deleteEmail:=True
    
cleanup:
    On Error Resume Next
    Exit Sub
errHandle:
    sendErrMsg "deleteEmail"
    Resume cleanup
End Sub
Sub refreshEmailTable()
    EmailTable True
End Sub
Sub EmailTable(Optional RefreshOnly As Boolean, Optional deleteEmail As Boolean = False)
    Application.ScreenUpdating = False
    iws = getWSInt(ActiveSheet.CodeName)
    setTblVars iws
    aMineSite = getMineSite
    
    Dim db As New cDB
    db.OpenConn
    
    If RefreshOnly <> True Then
        'Add/update selected email
        Set Target = ActiveCell
        IntersectCheck dbr, Target
        i = getActiveRow(tbl, Target)
        With dbr
            aEmail = .Cells(i, 1)
            aPassover = .Cells(i, 2)
            aWORequest = .Cells(i, 3)
            aFCCancelled = .Cells(i, 4)
            aPicsDLS = .Cells(i, 5)
            aPRP = .Cells(i, 6)
            aFCSummary = .Cells(i, 7)
            aTSI = .Cells(i, 8)
        End With
        
        Query = "Select * From EmailList Where Email='" & aEmail & "' "
        db.rs.Open Query, db.conn, adOpenStatic, adLockOptimistic
        
        With db.rs
            beforecount = .RecordCount

            If beforecount < 1 And Not deleteEmail Then
                .AddNew
                ElseIf deleteEmail Then  'Delete it
                    strDelete = "Email: '" & aEmail & "' in MineSite: '" & aMineSite & "'"
                    ans = MsgBox("Are you sure you want to delete:" & Line & strDelete, vbYesNo + vbQuestion)
                    If ans <> vbYes Then GoTo cleanup
                    .Delete
                    MsgBox strDelete & " deleted."
                    GoTo cleanup
                    Else
                    
            End If
            !MineSite = aMineSite
            !Email = aEmail
            !Passover = aPassover
            !WORequest = aWORequest
            !FCCancelled = aFCCancelled
            !PicsDLS = aPicsDLS
            !PRP = aPRP
            !FCSummary = aFCSummary
            !TSI = aTSI
            .Update
        End With
        
        rowsadded = db.rs.RecordCount - beforecount
        
        If rowsadded > 0 Then
            aMessage = rowsadded & " new row(s) added to Email table." & dLine
            Else
            aMessage = "Record updated: " & dLine
        End If
        
        MsgBox aMessage _
                & "MineSite: " & aMineSite & Line _
                & "Email: " & aEmail & Line _
                & "Passover: " & aPassover & Line _
                & "WO Request: " & aWORequest & Line _
                & "FC Cancelled: " & aFCCancelled & Line _
                & "PicsDLS: " & aPicsDLS & Line _
                & "PRP: " & aPRP & Line _
                & "FC Summary: " & aFCSummary & Line _
                & "TSI: " & aTSI
    
        Else
        'RefreshOnly True
        Query = "SELECT Email, Passover, WORequest, FCCancelled, PicsDLS, PRP, FCSummary, TSI From EmailList WHERE MineSite='" & aMineSite & "' ORDER BY Email"
        db.rs.Open Query, db.conn, adOpenStatic, adLockReadOnly
        ClearTable tbl
        dbr.Cells(1, 1).CopyFromRecordset db.rs
    End If
        
cleanup:
    On Error Resume Next
    db.rs.Close
    Application.EnableEvents = True
    Exit Sub
errHandle:
    sendErrMsg "Uh oh, something went wrong! Not able to update email table in Access Database."
    Resume cleanup
End Sub

Sub emailPassover()
    On Error GoTo errHandle
    Application.ScreenUpdating = False
    Application.EnableEvents = False
    Set tbl = Sheets(1).ListObjects(1)
    Set dbr = tbl.DataBodyRange
    
    sortPassover
    
    shift = "Day Shift"
    TodayDate = Now
    Greeting = "Afternoon"
    
    If hour(Now) < 8 Then
        shift = "Night Shift"
        TodayDate = Now - 1
        Greeting = "Morning"
    End If
    
    If dbr.Cells(1, 2) <> "x" Then
        MsgBox "No rows marked for passover, try again!"
        End
    End If
    
    strbody = "Good " & Greeting & "," & vbNewLine & "Please see below for updates from " _
                & Format(TodayDate, "mmmm d") & " " & shift & ":"
    
    Autofit_Height
    Copy_Passover
    
    aCompany = "SMS"
    If checkCummins Then aCompany = "Cummins"
    
    Set outlookApp = CreateObject("Outlook.Application")
    Set outMail = outlookApp.CreateItem(olMailItem)

    With outMail
        .To = getEmailList("Passover")
        .Subject = aCompany & " Passover " & getMineSite & " - " & Format(TodayDate, "dd-mmm-yyyy") & " - " & shift
    
        'Format table in email, highlight date text red, cut old dates
        Dim wdDoc As Object 'Word.Document
        Dim rng As Object 'Word.Range
        Set wdDoc = .GetInspector.WordEditor
        pasteIntoEmail wdDoc, strbody
        With wdDoc
            With .Tables(1)
                .Columns(2).width = 30
                .Columns(3).width = 60
                .Columns(4).width = 250
                .Columns(5).width = 150
            End With

            Set tbl = Sheets(1).ListObjects(1)
            Set dbr = tbl.DataBodyRange
            aCut = 250 'this determines min length of date event to keep
            
            For i = 2 To .Tables(1).Rows.Count
                aText = dbr.Cells(i - 1, 6)
                aLen = Len(aText)
                If aLen < 10 Then GoTo next_i

                'Highlight dates red
                Do While strCutStart > -1
                    Set rng = .Tables(1).Cell(i, 4).Range
                    strCutStart = InStrRev(aText, Line, aLen, vbTextCompare)

                    strCutEnd = InStr(strCutStart + 1, aText, "-", vbTextCompare)
                    DateLen = strCutEnd - strCutStart - 1

                    With rng
                        .start = .start + strCutStart
                        .End = .start + DateLen
                        .Font.TextColor = 255
                    End With
                    aLen = strCutStart - 1
                    If strCutStart < 1 Then Exit Do
                Loop
                
                'Cut text longer than aCut
                aLen = Len(aText)
                If aLen > aCut Then
                    strCut = InStrRev(aText, Line, aLen - aCut, vbTextCompare)
                    If strCut > 0 Then
                        Set rng = .Tables(1).Cell(i, 4).Range
                        With rng
                            .start = .start
                            .End = .start + strCut
                            .Delete
                        End With
                    End If
                End If
next_i:
            Next i
            .Tables(1).Rows.HeightRule = 0 'wdRowHeightAuto
            .Tables(1).RightPadding = 5
            .Tables(1).BottomPadding = 5
        End With
'        If checkCummins = True Then 'Add 'cummins export' at end, it was messing up the word table range
'            sPath = CumminsExport
'            .Attachments.add sPath
'        End If
    End With
    
cleanup:
    On Error Resume Next
    Application.CutCopyMode = False
    Application.EnableEvents = True
    outMail.display
'    If checkCummins = True Then Kill sPath
    Exit Sub
errHandle:
    sendErrMsg "emailPassover"
    Resume cleanup
End Sub




