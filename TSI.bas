Attribute VB_Name = "TSI"
Dim iPic As Integer
Public OilSample As Boolean
Public FaultCodes As Boolean

Sub autoTSI() 'ReadWrite As Boolean
    On Error GoTo errHandle
    ReadWrite = True
    
    Dim htmlDoc As MSHTML.HTMLDocument
    Dim elem As MSHTML.HTMLInputElement
    Dim frame As MSHTML.HTMLWindow2
    Dim form As MSHTML.HTMLFormElement
    
    Set ie = getTSIWebpage
    
    Set e = createEventTable(ActiveCell, 10)
    
    With ie
        Set htmlDoc = .Document
        Set frame = htmlDoc.Frames("UPPER")
        Set form = frame.Document.Forms("BQUERY")
        
        With form
            .Elements("CATEGORY")(1).Checked = True
            .Elements("SUBJECT").value = e.Unit & " - " & e.Title
            .Elements("MODEL").value = Left(e.Model, InStr(1, e.Model, "-") - 1)
            .Elements("TYPE").value = Mid(e.Model, InStr(1, e.Model, "-") + 1, 1)
            .Elements("SN").value = e.UnitSerial
            .Elements("SMR").value = e.UnitSMR
            .Elements("HOURS").value = e.PartSMR
            .Elements("FAILURE_DATE").value = Format(e.DateEvent, "mmddyyyy")
            
            Select Case e.MineSite ' MineSite specific settings
                Case "Bighorn"
                    .Elements("USER").value = "Coalspur - Bighorn"
                    .Elements("LOCATION").value = "Hinton, AB"
                    .getElementsByTagName("SELECT")(4).value = 75 'APPLICATION
                    .getElementsByTagName("SELECT")(7).value = 14 'ENVIRONMENT
                    .getElementsByTagName("SELECT")(5).value = 17 'GROUND CONDITION
                    .getElementsByTagName("SELECT")(6).value = 99 'WORKING CONDITION
                    .Elements("SPECIAL").value = "Coal Mine"
                    
                Case Else
                    .Elements("USER").value = "SUNCOR INC."
                    .Elements("LOCATION").value = "Fort McMurray, AB"
                    .getElementsByTagName("SELECT")(4).value = 79 'APPLICATION
                    .getElementsByTagName("SELECT")(7).value = 14 'ENVIRONMENT
                    .getElementsByTagName("SELECT")(5).value = 35 'GROUND CONDITION
                    .getElementsByTagName("SELECT")(6).value = 35 'WORKING CONDITION
                    .Elements("SPECIAL").value = "Oil Sands"
            End Select
            
            .Elements("FUEL")(0).Checked = True
            .Elements("CPART_NM").value = e.PartName
            .Elements("CPART_NO").value = e.PartNo
            .Elements("COMPONENT_SN").value = e.PartSerial
            .Elements("MANAGER").value = getUserInfo(Application.UserName, "Manager")
            .Elements("KOS_HENKYK")(0).Checked = True 'Failed parts returnable y/n
            
            Select Case True 'Model specific settings
                Case e.Model Like "PC*"
                    .Elements("SENDTO_BMN_CD").value = "00010"
                    .Elements("SENDTO_BMN_NM").value = "Service"
                    .Elements("SENDTO_GENPO_CD").value = "EUD"
                    .Elements("SENDTO_GENPO_NM").value = "KGM"
                Case Else
                    .Elements("SENDTO_BMN_CD").value = "00140"
                    .Elements("SENDTO_BMN_NM").value = "Mining Service Support"
                    .Elements("SENDTO_GENPO_CD").value = "USA"
                    .Elements("SENDTO_GENPO_NM").value = "KAC"
            End Select
            
            .Elements("NATURE").value = "-"
            .Elements("CAUSE").value = "Uncertian."
            .Elements("FIELD").value = "Component replaced with new."
            .Elements("REQUEST").value = "Please see attached report for complete info."
        End With
        
        'click retrieve button
        Set elems = form.getElementsByTagName("input")
        For Each elem In elems
            If elem.getAttribute("value") = "Retrieve" Then
                elem.click
                Exit For
            End If
        Next
    End With

cleanup:
    On Error Resume Next
    Exit Sub
errHandle:
    sendErrMsg "autoTSI"
    Resume cleanup
End Sub

Function Copy_Fault_Codes(aUnit, DateUpper As Date) As Workbook
    Application.ScreenUpdating = False
    sPath = "P:\Fort McMurray\service\5. Reliability Department\37. Analytical Tools\Fault Code History\Suncor Trucks Fault Code History.xlsm"
    Set wb = Application.Workbooks.Open(sPath, False, True)
    Set ws = wb.Sheets("Individual Unit")
    Dim DateLower As Date
    DateLower = DateUpper - 90
    
    ws.Range("A2") = aUnit
    Application.Run "'" & wb.Name & "'!Sum_Faults", DateLower, DateUpper
    ws.ListObjects("Code_Sum_Table").Range.Copy
    Set Copy_Fault_Codes = wb
End Function

Sub createFailureReport()
    Select Case getMineSite
        Case "BaseMine"
        FailureReport viewReportOnly:=False, OilSample:=False, EmailReport:=False, FaultCodes:=True
        Case Else
        FailureReport viewReportOnly:=False, OilSample:=False, EmailReport:=False, FaultCodes:=False
    End Select
End Sub

Sub emailTSI()
    On Error GoTo errHandle
    iws = getWSInt(ActiveSheet.CodeName)
    setTblVars iws
    Application.ScreenUpdating = False
    Application.EnableEvents = False
    Dim sRange As Range
    Set sRange = Application.Selection
    hRow = tbl.HeaderRowRange.row
    failPath = ""
    
    dbr.Rows.Hidden = True
    For Each Target In sRange
        tbl.ListRows(Target.row - hRow).Range.Rows.Hidden = False
    Next

    highlightRow ClearOnly:=True
    tbl.ListColumns(3).Range.Resize(, 14).Select
    Selection.Copy
    
    strbody = "Good " & getGreeting & "," & vbNewLine & "The following TSI(s) have been submitted: "
    Set outlookApp = CreateObject("Outlook.Application")
    Set outMail = outlookApp.CreateItem(olMailItem)
    
    With outMail
        For Each Target In sRange
            loadKeyVars iws, Target
            Set e = createEventTable(Target, iws)
            Dim EventFolder As New cEventFolder
            EventFolder.init e:=e
            aPath = EventFolder.FullPath & "\" & EventFolder.ReportTitle & ".pdf"
            If Dir(aPath) <> vbNullString Then
                .Attachments.add aPath
                Else
                failPath = failPath & aPath & dLine
            End If
        Next
        
        .To = getEmailList("TSI")
        .Subject = "Failure Summary - " & e.MineSite & " - " & Format(e.DateEvent, getDateFormat)
        
        Set wdDoc = .GetInspector.WordEditor
        pasteIntoEmail wdDoc, strbody
        .display
    End With
    
    If Len(failPath) > 1 Then MsgBox "Couldn't find PDFs for: " & Line & failPath

cleanup:
    On Error Resume Next
    Application.EnableEvents = True
    Application.CutCopyMode = False
    tbl.Range.Rows.Hidden = False
    ActiveCell.EntireRow.Hidden = False
    Application.ScreenUpdating = True
    dbr.Cells(dbr.Rows.Count, 10).Select
    Exit Sub
errHandle:
    sendErrMsg "emailTSI"
    Resume cleanup
End Sub

Sub FailureReport(viewReportOnly As Boolean, OilSample, EmailReport, FaultCodes)
    On Error GoTo errHandle
    Application.ScreenUpdating = False
    
    Set e = createEventTable(ActiveCell, 10)
    Set EventFolder = createFolder(e)
    If Not EventFolder.hasEventFolder Then EventFolder.CreateEventFolder
    
    'MS Word
    docTemplateTitle = "Component Failure Summary Template.docx"
    docTemplatePathFull = "P:\Regional\SMS West Mining\SMS Event Log\TSI\" & docTemplateTitle
    docReportTitle = EventFolder.ReportTitle & ".docx"
    docReportPathFull = EventFolder.FullPath & "\" & docReportTitle
    
    'Check if word doc already exists
    If Dir(docReportPathFull) <> "" Then
        DocExists = True
        aDoc = docReportTitle
        aPathFull = docReportPathFull
        
        answer = MsgBox("File already exists, do you want to add pictures?", vbYesNo + vbQuestion, "File Exists")
        If answer = vbNo Then GoTo openWordDoc
        
        Else
        DocExists = False
        aDoc = docTemplateTitle
        aPathFull = docTemplatePathFull
        If viewReportOnly Then
            MsgBox "Failure report not found, please create first."
            GoTo cleanup
        End If
    End If
    
    If viewReportOnly = False Then 'Select Pictures
        aImagePath = EventFolder.ImagePath 'cant have a folder picker inside a file picker apparently
        Set fDialog = Application.FileDialog(msoFileDialogFilePicker)
        With fDialog
            .AllowMultiSelect = True
            .InitialView = 6 'msoFileDialogViewLargeIcons
            .Title = "Select Pictures"
            .InitialFileName = aImagePath
            If .Show = -1 Then
                NumPics = .SelectedItems.Count
                Else
                ans = MsgBox("No images selected, continue creating report?", vbYesNo)
                If ans <> vbYes Then GoTo cleanup
            End If
        End With
    End If

openWordDoc:
    On Error Resume Next
        Set wdApp = getObject(, "Word.Application")
    On Error GoTo errHandle
'    On Error GoTo 0
    
    If wdApp Is Nothing Then 'wdApp not open, open both
            Set wdApp = CreateObject("Word.Application")
            Set wdDoc = wdApp.Documents.Open(aPathFull, readOnly:=True)
            
        Else 'wdApp open, check wdDoc
            On Error Resume Next
            Set wdDoc = wdApp.Documents(aDoc)
            If wdDoc Is Nothing Then Set wdDoc = wdApp.Documents.Open(aPathFull) 'wdDoc not open, open it
    End If
    
    LoadingFailureReport.Show vbModeless
    With wdApp
        .visible = False
        .WindowState = 1
        .ScreenUpdating = False
    End With
    
    With wdDoc
        'dont need to do this if only adding pictures? or just do it
        With .Tables(1)
            .Cell(1, 2).Range.Text = Format(e.DateEvent, "yyyy-mm-dd")
            .Cell(1, 4).Range.Text = e.WorkOrder
            .Cell(3, 2).Range.Text = getUserInfo(Application.UserName, "Title") 'needs DB
            .Cell(7, 2).Range.Text = e.Model
            .Cell(8, 2).Range.Text = e.Unit
            .Cell(9, 2).Range.Text = e.UnitSerial
            .Cell(10, 2).Range.Text = Format(e.UnitSMR, "#,###")
            .Cell(7, 4).Range.Text = e.PartName
            .Cell(8, 4).Range.Text = e.PartNo
            .Cell(9, 4).Range.Text = e.PartSerial
            .Cell(10, 4).Range.Text = Format(e.PartSMR, "#,###")
        End With
        
        On Error Resume Next
        .Bookmarks("Description").Range.Text = e.Description
        On Error GoTo errHandle
'        On Error GoTo 0
        
        Dim wrdTbl As Object
        Dim PicTable As Object
        For Each wrdTbl In .Tables
            If wrdTbl.Title = "Pictures" Then
                Set PicTable = wrdTbl
                Exit For
            End If
        Next wrdTbl
        
        'Add Each Picture to Word Doc
        Countrows = PicTable.Rows.Count
        With PicTable
            LastRow = Countrows + NumPics
            iPic = 1
            
            If Countrows = 2 Then
                LastRow = LastRow - 1
                Else
                Countrows = Countrows + 1
            End If
            
            For i = Countrows To LastRow
                CurrCount = .Rows.Count
                If i <> 2 Then .Rows.add 'BeforeRow:=.Rows(1)

                Dim pic1 As Object 'Word.InlineShape
                Set pic1 = .Cell(i, 1).Range.InlineShapes.AddPicture(fileName:=fDialog.SelectedItems(iPic) _
                            , LinkToFile:=True, SaveWithDocument:=False)
                pic1.LockAspectRatio = 1 'msoCTrue
                pic1.width = 368.504 'pic1.Width = CentimetersToPoints(14)
                pic1.Range.InsertCaption label:="Figure", Title:=" - ", Position:=1 'wdCaptionPositionBelow
                        
                'Delete trailing space after caption
                .Cell(i, 1).Range.Select
                With wdApp.Selection
                    .EndOf 12, 0
                    .MoveLeft
                    .Delete
                End With
                iPic = iPic + 1
            Next i
        End With
        
        If DocExists = False Then .SaveAs2 (docReportPathFull)
        
        'FAULT CODES
        If FaultCodes = True Then
            On Error Resume Next
                AppActivate "Microsoft Excel"
                AppActivate "Excel"
            On Error GoTo errHandle
'            On Error GoTo 0
            
            answer = MsgBox("Include fault codes?", vbYesNo + vbQuestion, "Fault Codes")
            If answer = vbYes Then
                Set wb = Copy_Fault_Codes(e.Unit, e.DateEvent + 1)
                
                'Replace fault_code bookmark with table
                .Bookmarks("Fault_Codes").Range.Paste

                Application.CutCopyMode = False
                
                'Adjust table
                With .Tables(2)
                    .Range.Font.size = 8
                    .AutoFitBehavior (1)
                    .Columns.AutoFit
                    .Rows(1).height = 14
                End With
                wb.Close False
            End If
        End If
        
        'OIL SAMPLE
        If OilSample = True Then
            On Error Resume Next
                AppActivate "Microsoft Excel"
                AppActivate "Excel"
            On Error GoTo errHandle
'            On Error GoTo 0
            answer = MsgBox("Include oil sample?" & dLine & "'Fluidlie Database Query & Oil Sample Report.xlsm'" _
                            & " will be opened. This does not refresh the FL database (takes too long), make sure it has been " _
                            & "updated recently.", vbYesNo + vbQuestion, "Oil Sample")
            If answer = vbYes Then
                Open_FL_Oil_Report
                Select_Oil_Report.Show
                Application.Run "'Fluidlife Database Query & Oil Sample Report.xlsm'!Copy_Unit_Sample", e.Unit
        
                'Replace oil report bookmark with table
                .Bookmarks("Oil_Report").Range.Paste

                Workbooks("Fluidlife Database Query & Oil Sample Report.xlsm").Close False 'Close FL excel

                With .Tables(2) 'Adjust table
                    .Range.Font.size = 8
                    .AutoFitBehavior (1)
                    .Columns.AutoFit
                    .Rows(1).height = 14
                End With
            End If
        End If
    End With
    
    With wdApp
        .visible = True
        .ScreenUpdating = True
        .Activate
    End With

cleanup:
    On Error Resume Next
    LoadingFailureReport.Hide
    Set wdDoc = Nothing
    Set wdApp = Nothing
    Exit Sub
errHandle:
    sendErrMsg "FailureReport"
    Resume cleanup
End Sub

'Sub importTSITemp()
'    Set wb = Workbooks("Coalspur Bighorn - TSI.xlsx")
'    Set ws = wb.Sheets(1)
'    Set tbl = ws.ListObjects(1)
'    Set dbr = tbl.DataBodyRange
'
'    loadDB
'    Set rs = db.OpenRecordset("EventLog", dbOpenTable)
'    With rs
'        beforecount = .RecordCount
'        aUID = createUID
'
'        For i = 1 To dbr.Rows.Count
'            aUID = aUID + 1 'need to increment the unique ID for each row > no duplicates
'
'            .AddNew
'            !UID = aUID
'            !MineSite = "Bighorn"
'            !StatusTSI = dbr.Cells(i, 1)
'            !DateAdded = dbr.Cells(i, 2)
'            !DateInfo = dbr.Cells(i, 3)
'            !DateTSISubmission = dbr.Cells(i, 4)
'            !TSINumber = dbr.Cells(i, 5)
'            !WorkOrder = dbr.Cells(i, 6)
'            !Unit = dbr.Cells(i, 7)
'            '!Model > comes from unitID table
'            !Title = dbr.Cells(i, 9)
'            !SMR = dbr.Cells(i, 10)
'            !ComponentSMR = dbr.Cells(i, 11)
'            !TSIPartName = dbr.Cells(i, 12)
'            !PartNumber = dbr.Cells(i, 13)
'            !SNRemoved = dbr.Cells(i, 14)
'            !TSIDetails = dbr.Cells(i, 15)
'            !TSIAuthor = dbr.Cells(i, 16)
'            .Update
'        Next i
'    End With
'
'    Debug.Print "rows added: " & rs.RecordCount - beforecount
'End Sub

Sub openTSIfromWO()
    On Error GoTo errHandle
    
    iws = 2
    getWorkSheet(iws).Activate
    
    Set Target = Application.InputBox("Select event to create TSI.", "Link TSI", Type:=8)
    
    Set e = createEventTable(Target, iws)
    With e.rsEvent
        !StatusTSI = "Open"
        !TSIAuthor = Application.UserName
        .Update
    End With
    
    iws = 10
    RefreshTable "Dates", DateLower:=DateValue(Now - 31), DateUpper:=DateValue(Now), iws:=iws

cleanup:
    On Error Resume Next
    e.TearDown
    Exit Sub
errHandle:
    If Err.Number = 424 Then
        Err.clear
        Sheet10.Activate
        Resume cleanup
    End If
    sendErrMsg "openTSIfromEvent"
    
End Sub

Sub openTSINew()
    On Error GoTo errHandle
    Dim aTSINew As TSINew
    Set aTSINew = New TSINew
    aTSINew.Show
cleanup:
    On Error Resume Next
    Exit Sub
errHandle:
    sendErrMsg "openTSINew"
End Sub

Sub Open_FL_Oil_Report()
    Dim FLWB As Workbook
    Dim wbk As Workbook
    Dim WbkOpen As Boolean
    WbkOpen = False

    For Each wbk In Workbooks
        If wbk.Name = "Fluidlife Database Query & Oil Sample Report.xlsm" Then
        WbkOpen = True
        End If
    Next
        
    If WbkOpen = False Then
        Set FLWB = Workbooks.Open("P:\Fort McMurray\service\5. Reliability Department\7. Oil Analysis\Fluidlife Database Query & Oil Sample Report\" _
                & "Fluidlife Database Query & Oil Sample Report.xlsm")
        With FLWB
        .OpenedInCode = True
        .RunAutoMacros xlAutoOpen
        End With
    End If
End Sub


Sub refreshTSI()
    RefreshTable iws:=10
End Sub

