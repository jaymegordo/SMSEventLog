Attribute VB_Name = "Functions"
Option Compare Text

Sub BuildFullPath(ByVal FullPath)
    setFso
    If Not FSO.FolderExists(FullPath) Then
        BuildFullPath FSO.GetParentFolderName(FullPath)
        FSO.createFolder FullPath
    End If
End Sub

Sub centerUserform(usr As Object)
    usr.top = Application.top + Application.height / 2 - usr.height / 2
    usr.Left = Application.Left + Application.width / 2 - usr.width / 2
End Sub

Function CharPos(SearchString As String, Char As String, Instance As Long)
     'Function purpose:  To return the position of the (first character of the )
     'nth occurance of a specific character set in a range
     
    Dim x As Integer, n As Long
     
     'Loop through each letter in the search string
    For x = 1 To Len(SearchString)
         'Increment the number of characters search through
        CharPos = CharPos + 1
         
         'check if the next character(s) match the text being search for
         'and increase n if so (to count how many matches have been found
        If Mid(SearchString, x, Len(Char)) = Char Then n = n + 1
         
         'Exit loop if instance matches number found
        If n = Instance Then Exit Function
    Next x
     
     'The error below will only be triggered if the function was not
     'already exited due to success
    CharPos = CVErr(xlErrValue)
End Function



Sub cleanupDB()
    On Error Resume Next
    rs.Close
    Set rs = Nothing
    rs2.Close
    Set rs2 = Nothing
    rs4.Close
    Set rs4 = Nothing
    rs5.Close
    Set rs5 = Nothing
    rs6.Close
    Set rs6 = Nothing
'    db.Close
'    Set db = Nothing
End Sub

Function ClearFilter(tbl)
    On Error Resume Next
    With tbl
        If .AutoFilter Is Nothing Then Exit Function
        If .AutoFilter.FilterMode = True Then
            .AutoFilter.ShowAllData
        End If
    End With
End Function

Function ClearTable(tbl)
    With tbl
        If .DataBodyRange.Rows.Count > 1 Then
            .ListRows(2).Range.Resize(.DataBodyRange.Rows.Count - 1).ClearContents
            .DataBodyRange.RemoveDuplicates 1
        End If
    End With
End Function

'Sub closeDB()
'    On Error Resume Next
'    db.Close
'    Set db = Nothing
'    db2.Close
'    Set db2 = Nothing
'End Sub

Function CountFilesInFolder(strDir As String, Optional strType As String)
    Dim File As Variant, i As Integer
    If Right(strDir, 1) <> "\" Then strDir = strDir & "\"
    File = Dir(strDir & strType)
    While (File <> "")
        i = i + 1
        File = Dir
    Wend
    CountFilesInFolder = i
End Function

Function createUID() As Double
    createUID = 1 & Format(Now, "ddhhnnssms")
End Function

Function disableCummins()
    If checkCummins = True Then
        MsgBox "This feature not yet enabled for Cummins."
        End
    End If
End Function

Function dLine() As String
    dLine = Chr(10) & Chr(10)
End Function

Sub expandCollapseCols(Optional dummy As Boolean = False, Optional bState As Boolean = False)
    On Error GoTo errHandle
    Set ws = ActiveSheet
    Application.ScreenUpdating = False
    Application.EnableEvents = False
    
    If Not dummy Then
        bState = getState("col")
        With ws
            Select Case bState
                Case True 'hidden, > expand em
                    .Columns("D:I").Hidden = False
                Case False 'visible > collapse em
                    .Columns("D:I").Hidden = True
            End Select
        End With
        Else
        ws.Columns("D:I").Hidden = bState
    End If
cleanup:
    Application.ScreenUpdating = True
    Application.EnableEvents = True
    Exit Sub
errHandle:
    sendErrMsg "expandCollapseCols"
    Resume cleanup
End Sub

Sub expandCollapseRows(Optional dummy As Boolean = False, Optional bState As Boolean = False)
    On Error GoTo errHandle
    Set ws = ActiveSheet
    Set tbl = ws.ListObjects(1)
    Set dbr = tbl.DataBodyRange
    Application.ScreenUpdating = False
'    Application.EnableEvents = False
    
    Set aRng = dbr.Cells(1, 2).Resize(dbr.Rows.Count, 7)
    
    If Not dummy Then
        bState = getState("row")
        With ws
            Select Case bState
                Case False 'hidden, > expand em
                    aRng.WrapText = True
                Case True 'visible > collapse em
                    aRng.WrapText = False
            End Select
        End With
        Else
        aRng.WrapText = bState
    End If
cleanup:
    Application.ScreenUpdating = True
    Application.EnableEvents = True
    Exit Sub
errHandle:
    sendErrMsg "expandCollapseRows"
    Resume cleanup
End Sub

Function getActiveRow(tbl, Target)
    getActiveRow = Target.row - tbl.HeaderRowRange.row
End Function

Function getCumminsPath()
    If Application.UserName <> "Jayme Gordon" Then
        getCumminsPath = "N:\Cummins Event Log"
        Else
        getCumminsPath = "C:\Users\jgordon\Desktop\Cummins Event Log"
    End If
End Function

Function getDatabasePath(Optional fType)
    On Error GoTo errHandle
    If IsMissing(fType) Then fType = getTable
    
    aPath = "P:\Fort McMurray\service\5. Reliability Department\37. Analytical Tools\"
    
    If checkCummins = True Then
        aDatabasePath = getCumminsPath & "\Event Log Database.accdb"
        GoTo checkPath
    End If
    
    Select Case fType
        Case "fault0"
            aDatabasePath = aPath & "Fault Code History\Fault Code Database.accdb"
        Case "haul"
            aDatabasePath = aPath & "Payload and Fault Analyzer\PLM Database.accdb"
        Case "EventLog"
            aDatabasePath = "P:\Regional\SMS West Mining\SMS Event Log\Event Log Database.accdb"
            'aDataBasePath = "C:\Users\jgordon\Desktop\Event Log Database.accdb"
    End Select
    
checkPath:
    If Not Dir(aDatabasePath, vbDirectory) = vbNullString Then
        'Found path exists
        getDatabasePath = aDatabasePath
        Exit Function
        Else
        Err.Raise 555, "Can't connect to database."
    End If
    
Exit Function
errHandle:
    sendErrMsg "getDatabasePath" & dLine & "Make sure you are connected to the SMS/(or Cummins) network/VPN, " _
                & "then open a folder on the P: (or N:) Drive to make the connection active."
    End
End Function

Function getDateFormat(Optional aMineSite As String)
    If aMineSite = "" Then aMineSite = getMineSite
    Select Case aMineSite
        Case "BaseMine"
            getDateFormat = "mm-dd-yyyy"
        Case Else
            getDateFormat = "yyyy-mm-dd"
    End Select
End Function

Function getFiles(folder As Object, coll As Collection, Optional FirstFolder As Boolean = True) As Collection
    Dim SubFolder As Scripting.folder
    For Each SubFolder In folder.subfolders
        Set coll = getFiles(SubFolder, coll, False)
    Next
    If Not FirstFolder Then
        Dim File As Scripting.File
        For Each File In folder.Files
            If isPicture(File.Type) Then coll.add File
        Next
    End If
    Set getFiles = coll
End Function

Function getGreeting()
    If hour(Now) < 12 Then
        getGreeting = "Morning"
        Else
        getGreeting = "Afternoon"
    End If
End Function

Function getMineSite(Optional RootMineSite As Boolean = False)
    sMineSite = Range("MineSite")
    If Not RootMineSite Then
        getMineSite = sMineSite
        ElseIf sMineSite Like "*_*" Then
            getMineSite = Left(sMineSite, InStr(1, sMineSite, "_") - 1)
            Else
            getMineSite = sMineSite
    End If
End Function
Function getSubSiteFilter() As String
    sMineSite = getMineSite
    If hasSubSite Then
        sFilter = "='" & Right(sMineSite, Len(sMineSite) - InStr(1, sMineSite, "_")) & "' "
        Else
        sFilter = " Is Null "
    End If
    getSubSiteFilter = "SubSite" & sFilter
End Function
Function hasSubSite() As Boolean
    If getMineSite Like "*_*" Then hasSubSite = True
End Function
Function checkCummins()
    If getMineSite Like "*CWC*" Then
        checkCummins = True
        Else
        checkCummins = False
    End If
End Function

Function getOutlookFolder(oTopFolder, sFolder As String) As Object
        For Each Fldr In oTopFolder.Folders
            If Fldr.Name = sFolder Then
                Set getOutlookFolder = Fldr
                Exit For
                
                Else
                Set getOutlookFolder = getOutlookFolder(Fldr, sFolder)
            End If
        Next Fldr
End Function

Function getSaveCount(iws) As Range
    Select Case iws
        Case 1
            Set getSaveCount = Sheet1.Range("J2")
        Case 2
            Set getSaveCount = Sheet2.Range("D2")
        Case 10
            Set getSaveCount = Sheet10.Range("C1")
    End Select
End Function

Function getSlowConn()
    getSlowConn = Sheet1.Range("J1").value
End Function

Function getState(sState)
    Set ws = ActiveSheet
    Select Case sState
        Case "col"
            getState = ws.Columns(4).Hidden
        Case "row"
            getState = ws.Cells(6, 8).WrapText
    End Select
End Function

Function getTable(Optional FC As Boolean)
    If FC = False Then
        getTable = "EventLog"
        Else
        getTable = "FactoryCampaign"
    End If
End Function

Function getUIDQuery(Optional dUID As Double) As String
    On Error GoTo errHandle
    If dUID = 0 Then dUID = aUID
        
    getUIDQuery = "SELECT * FROM EventLog WHERE UID=" & dUID
    Exit Function
errHandle:
    sendErrMsg "getUIDQuery"
End Function

Function getWarrantyOnly()
    getWarrantyOnly = Sheet2.Range("D1").value
End Function

Function getWorkSheet(iws) As Worksheet
    For Each ws In ThisWorkbook.Worksheets
        If ws.CodeName = "Sheet" & iws Then
            Set getWorkSheet = ws
            Exit Function
        End If
    Next ws
End Function

Function getWriteMode()
    getWriteMode = Sheet1.Range("H1").value
End Function

Function getWSInt(aCodeName As String) As Integer
    'get using worksheet CodeName property (which doesn't change)
    NumLen = 1
    If IsNumeric(Right(aCodeName, 2)) Then NumLen = 2
    getWSInt = CInt(Right(aCodeName, NumLen))
End Function

Sub highlightRow(Optional HighlightHeader As Boolean = False, Optional StartCol As Integer = 1, _
                Optional aWidth As Integer, Optional boldCol As Boolean = False, Optional ClearOnly As Boolean = False)
    'FC Summary - Highlights the FC subject and unit header for easier confirmation of selected row/unit.
    'Everything else - highlights selected row
    'Was it excessive to make this? maybe. > Update - no its actually really useful

    On Error GoTo errHandle
    Application.ScreenUpdating = False
    Set tbl = ActiveSheet.ListObjects(1)
    Set dbr = tbl.DataBodyRange
    Dim sRange As Range
    Set sRange = Application.Selection
    
    'If Intersect(sRange, dbr) Is Nothing Then Exit Sub
    If Intersect(sRange, dbr) Is Nothing Then ClearOnly = True
    
    If aWidth < 1 Then aWidth = dbr.Columns.Count - StartCol + 1
    
    'Clear all rows
    With dbr.Cells(1, StartCol).Resize(dbr.Rows.Count, aWidth)
        .Interior.Color = xlNone
        If boldCol Then .Font.bold = False
    End With
    
    'Clear unit header
    If HighlightHeader Then
        With tbl.HeaderRowRange
            .Interior.Color = xlNone
            .Font.ColorIndex = 2
        End With
    End If
    
    If ClearOnly Then GoTo cleanup
    
    'Highlight row
    aRow = sRange.row - tbl.HeaderRowRange.row
    If sRange.row <= tbl.HeaderRowRange.row Then Exit Sub
    With dbr.Cells(aRow, StartCol).Resize(, aWidth)
        .Interior.Color = RGB(255, 255, 100)
    End With
    If boldCol Then dbr.Cells(aRow, 2).Font.bold = True
    
    'Highlight unit header
    If HighlightHeader Then
        UnitCol = aWidth + 2
        aCol = sRange.Column - UnitCol
        Dim hdrRng As Range
        Set hdrRng = tbl.HeaderRowRange.Range(Cells(1, UnitCol), Cells(1, tbl.ListColumns.Count))
        If aCol < 0 Then Exit Sub
        With hdrRng.Cells(1, aCol + 1)
            .Interior.Color = RGB(255, 255, 100)
            .Font.Color = xlBlack
        End With
    End If

cleanup:
    On Error Resume Next
    'Application.ScreenUpdating = True
    If Not ClearOnly Then Application.EnableEvents = True
    Exit Sub
errHandle:
    sendErrMsg "highlightRow"
    Resume cleanup
End Sub

Function IntersectCheck(dbr As Range, Optional Target As Range, Optional Complian As Boolean = True) As Boolean
    If IsMissing(Target) Then Set Target = ActiveCell
    If Intersect(Target, dbr) Is Nothing Then
        If Complain Then MsgBox "Select a row from the table.", vbExclamation
        IntersectCheck = False
        End
        Else
        IntersectCheck = True
    End If
End Function

Function isFolderEmpty(folder As Object) As Boolean
    Dim SubFolder As Scripting.folder
    For Each SubFolder In folder.subfolders
         If Not isFolderEmpty(SubFolder) Then Exit Function
    Next
    If folder.Files.Count < 1 Then isFolderEmpty = True
End Function

Function IsInArray(stringToBeFound As String, arr As Variant) As Boolean
  IsInArray = (UBound(Filter(arr, stringToBeFound)) > -1)
End Function

Function isPicture(sName As String) As Boolean
    arrPics = Array("jpg", "jpeg", "png", "tiff", "Data Base File")
    For i = 0 To UBound(arrPics)
        If LCase(sName) Like "*" & LCase(arrPics(i)) & "*" Then
            isPicture = True
            Exit For
        End If
    Next
End Function

Sub launchCopyWorksheet()
    CopyWorksheet.Show
End Sub

Sub launchRefreshDateRange()
    RefreshDateRange.Show
End Sub

Function Line() As String
    Line = Chr(10)
End Function


Sub loadKeyVars(iws, Target As Range)
    On Error GoTo errHandle
    setTblVars iws
    IntersectCheck dbr, Target
    i = getActiveRow(tbl, Target)
    
    With dbr
        Select Case iws
            Case 8 'fc summary
                aFCNumber = .Cells(i, 1)
            Case 15 'componentCO
                aUnit = .Cells(i, getCol(iws, "Unit"))
                aComponent = .Cells(i, 2)
                aModifier = .Cells(i, 3)
                aDate = .Cells(i, getCol(iws, "DateAdded"))
                
            Case Else
                aUID = .Cells(i, 1)
                aDate = .Cells(i, getCol(iws, "DateAdded"))
                aUnit = .Cells(i, getCol(iws, "Unit"))
                aTitle = Trim(.Cells(i, getCol(iws, "Title")))
                If iws = 2 Or iws = 10 Then aPartNo = .Cells(i, getCol(iws, "PartNo"))
        End Select
    End With
    
cleanup:
    Exit Sub
errHandle:
    sendErrMsg "loadKeyVars"
    Resume cleanup
End Sub

Function pasteIntoEmail(wdDoc, strbody)
    With wdDoc
        With .Range(0, 1).Font
          .Name = "Calibri"
          .size = 11
        End With
        .Range(1, 1).InsertBreak
        .Range(2, 2).Paste 'Special wdChartPicture
        .Range(0).insertBefore strbody
    End With
    
    Set ObjSel = wdDoc.Windows(1).Selection
    With ObjSel
        .MoveDown Unit:=5, Count:=1, Extend:=1 'wdLine=5, wdExtend=1
        .Collapse Direction:=0 'wdCollapseEnd
        .InsertParagraph
        .Move 6, -1 'wdStory=6
    End With
End Function

Function RandomGen()
    Application.Volatile
    Do
        i = i + 1
            rChar = Round(9 * Rnd)
        Rand = Rand & rChar
    Loop Until i = 9
    RandomGen = Rand
End Function

Sub refreshDate(rng As Range)
    rng.value = "Last refresh: " & Format(Now, "yyyy-mm-dd hh:mm")
End Sub

Sub sendErrMsg(ErrMsg As String)
    
    aMessage = ErrMsg & " | " & Err.Number & " - " & Err.Description
    Err.clear
    
    If Application.UserName = "Jayme Gordon" Then Debug.Print aMessage
        
    aMessage = aMessage & dLine & "If this is a critical error, please take a screenshot of this " _
        & "message and email Jayme (jgordon@smsequip.com) with a description of what you were doing when the error ocurred."
    MsgBox aMessage, vbCritical, ErrMsg

End Sub

Function setMineSite(aMineSite As String)
    Sheet1.Range("H2").value = aMineSite
End Function

Sub setStartupColsSheets()
    On Error GoTo errHandle
    Application.ScreenUpdating = False
    
    If Not checkCummins Then
        For Each ws In ThisWorkbook.Worksheets
            If ws.CodeName <> "Sheet3" And ws.CodeName <> "Sheet9" And ws.CodeName <> "Sheet17" _
                And ws.CodeName <> "Sheet18" And ws.CodeName <> "Sheet4" Then ws.visible = xlSheetVisible
        Next
    End If
    
    Set ws = Sheet2
    With ws
        If Not checkCummins Then
            Select Case getMineSite(True)
                Case "BaseMine"
                    .Columns("G:H").EntireColumn.Hidden = True
                    .Columns("F").EntireColumn.Hidden = False
                    .Columns("L").EntireColumn.Hidden = False
                Case "FortHills", "FH-TKMC", "Bighorn", "HeavyMetal"
                    .Columns("G:H").EntireColumn.Hidden = False
                    .Columns("F").EntireColumn.Hidden = False
                    .Columns("L").EntireColumn.Hidden = False
            End Select

            Else
            .Columns("F").EntireColumn.Hidden = True
            .Columns("L").EntireColumn.Hidden = True
            
            Sheet7.visible = xlSheetHidden
            Sheet8.visible = xlSheetHidden
            Sheet9.visible = xlSheetHidden
            Sheet10.visible = xlSheetHidden
            Sheet12.visible = xlSheetHidden
            Sheet13.visible = xlSheetHidden
            Sheet14.visible = xlSheetHidden
            Sheet15.visible = xlSheetHidden
            Sheet16.visible = xlSheetHidden
            Sheet17.visible = xlSheetHidden
            Sheet18.visible = xlSheetHidden
        End If
    End With
    
    Exit Sub
errHandle:
    sendErrMsg "setStartupColsSheets"
End Sub

Sub setTblVars(iws)
    On Error GoTo errHandle
    Set ws = getWorkSheet(iws)
    Set tbl = ws.ListObjects(1)
    Set dbr = tbl.DataBodyRange
cleanup:
    Exit Sub
errHandle:
    sendErrMsg "setTblVars"
    Resume cleanup
End Sub

Sub showDetails()
Attribute showDetails.VB_ProcData.VB_Invoke_Func = "D\n14"
    
    On Error GoTo errHandle
    Application.EnableEvents = False
    Dim ufDetails As Details
    Set ufDetails = New Details
    ufDetails.Show
    
cleanup:
    On Error Resume Next
    Application.EnableEvents = True
    Exit Sub
errHandle:
    sendErrMsg "showDetails"
    Resume cleanup
End Sub

Sub showMineSiteSwap()
Attribute showMineSiteSwap.VB_ProcData.VB_Invoke_Func = "M\n14"
    MineSiteSwap.Show
End Sub

Function sortCollection(collectionObject As Collection) As Collection 'BUBBLE SORT IT
    On Error GoTo errHandle
    For i = collectionObject.Count To 2 Step -1
        For j = 1 To i - 1
            If collectionObject(j) > collectionObject(j + 1) Then
                collectionObject.add collectionObject(j), After:=j + 1
                collectionObject.remove j
            End If
        Next j
    Next i
    Set sortCollection = collectionObject
cleanup:
    Exit Function
errHandle:
    sendErrMsg "sortCollection"
    Resume cleanup
End Function

Sub startTimer()
    timeInactive = Now + TimeValue("00:05:00")
    Application.OnTime timeInactive, "closeDB", schedule:=True
End Sub

Sub stopTimer()
    On Error Resume Next
    Application.OnTime timeInactive, "closeDB", schedule:=False
End Sub

Sub WriteCheck()
If getWriteMode <> "Write" Then
    MsgBox "Hey don't touch that, you're not in 'write' mode!" & dLine & "Changes not updated."
    End
End If
End Sub

