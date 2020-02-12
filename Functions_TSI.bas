Attribute VB_Name = "Functions_TSI"

Function getUserInfo(User, aType)
    On Error GoTo errHandle
    Dim Query As String
    Query = "Select * From Users Where UserName='" & User & "'"
    Dim rs As ADODB.Recordset
    Set rs = getQuery(Query:=Query)
    
    With rs
        Select Case aType
            Case "Title"
                getUserInfo = User & ", " & !Title
            Case "Manager"
                getUserInfo = !Manager
        End Select
    End With
    
cleanup:
    rs.Close
    Exit Function
errHandle:
    sendErrMsg "Couldn't get user title of: " & User & dLine & "Ensure user title is entered into the Users table of the Event Log Database."
    Resume cleanup
End Function

Function getTSIWebpage()
    On Error GoTo errHandle
    Set objShell = CreateObject("Shell.Application")
    ieCount = objShell.Windows.Count
    marker = 0
    
    For x = 0 To ieCount - 1
        On Error Resume Next
        my_url = objShell.Windows(x).Document.Location
        my_title = objShell.Windows(x).Document.Title
    
        If my_title Like "*" & "Create TSI" & "*" Then 'compare to find if the desired web page is already open
            Set getTSIWebpage = objShell.Windows(x)
            marker = 1
            Exit For
        End If
next_x:
    Next x
    
    If marker <> 1 Then
        ans = MsgBox("TSI webpage not found, please log in and open the 'Create TSI' page. Would you like to open the TSI page now?", vbYesNo, "TSI Webpage not found")
        If ans = vbYes Then
            Dim ie As Object 'InternetExplorer
            Set ie = CreateObject("InternetExplorer.Application")
            ie.visible = True
            ie.navigate "https://smap.komatsu.co.jp/cgi-bin/webdriver"
        End If
        End
    End If
    
cleanup:
    On Error Resume Next
    Exit Function
errHandle:
    If Err.Number = 438 Then Resume next_x 'no ie open
    sendErrMsg "getTSIWebpage"
End Function

'Sub loadTSIVars() ' put into event
'    On Error GoTo errHandle
'    iws = 10
'    setTblVars iws
'    IntersectCheck dbr
'    i = getActiveRow(tbl, ActiveCell)
'
'    With dbr
'        aUID = .Cells(i, 1)
'        aDate = .Cells(i, getCol(iws, "DateAdded"))
'        aWorkOrder = .Cells(i, getCol(iws, "WorkOrder"))
'        aUnit = .Cells(i, getCol(iws, "Unit"))
'        aModel = .Cells(i, 9)
'        aTitle = .Cells(i, getCol(iws, "Title"))
'        aUnitSMR = .Cells(i, getCol(iws, "UnitSMR"))
'        aPartSMR = .Cells(i, getCol(iws, "PartSMR"))
'        aPartName = .Cells(i, 13)
'        aPartNo = .Cells(i, getCol(iws, "PartNo"))
'        aPartSerial = .Cells(i, 15)
'        aUser = .Cells(i, 17)
'    End With
'cleanup:
'    Exit Sub
'errHandle:
'    sendErrMsg "loadTSIVars"
'    Resume cleanup
''End Sub
'Function getDescription() As String
'    On Error GoTo errHandle
'    'aUID = 1101632151015#
'    loadDB
'    aQuery = "SELECT Description FROM EventLog WHERE UID =" & aUID
'    Set rs4 = db.OpenRecordset(aQuery, dbOpenDynaset)
'    With rs4
''        Debug.Print .RecordCount
''        Debug.Print !Description
'        If .RecordCount = 1 And Len(!Description) > 0 Then
'            getDescription = !Description
'            Else
'            getDescription = "No description in event log"
'        End If
'    End With
'cleanup:
'    rs4.Close
'    Set rs4 = Nothing
'    cleanupDB
'    Exit Function
'errHandle:
'    sendErrMsg "getDescription"
'    Resume cleanup
'End Function
