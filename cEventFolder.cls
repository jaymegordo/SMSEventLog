VERSION 1.0 CLASS
BEGIN
  MultiUse = -1  'True
END
Attribute VB_Name = "cEventFolder"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = False
Attribute VB_PredeclaredId = False
Attribute VB_Exposed = False
Private pMineSite As String
Private pUnit As String
Private pSerial As String
Private pModel As String
Private pDate As Date
Private pstrDate As String
Private pWO As String
Private pTitle As String
Private pTitleCurrent As String
Private pYear As String
Private pUID As Double

Private pDateTemp As String
Private pWOTemp As String

Private pUnitPath As String
Private pBasePath As String
Private pFolderTitle As String
Private pFolderTitleCurrent As String
Private pFullPath As String
Private pFullPathCurrent As String
Private pFullPathDB As String
Private pPicsPath As String
Private pDlsPath As String
Private pReportTitle As String
Private parrFullPath() As String
Private parrFolderTitle() As String

Private pFromPath As String
Private pToPath As String

Private pFixFolder As Boolean

Private prsSerial As ADODB.Recordset
Private prsEvent As ADODB.Recordset
Private pFso As Scripting.FileSystemObject
Private pFolder As Scripting.folder
Private pPicsFolder As Scripting.folder
Private pFile As Scripting.File
Private pfDialog As FileDialog
Private pNumPics As Integer
Private pDls As Boolean

Public Sub init(Optional aTitle As String, Optional aMineSite As String, Optional FullPath As String, Optional e As cEvent)
    
    On Error GoTo errHandle
    
    If Not IsMissing(e) Then
        Debug.Assert Not e Is Nothing
        With e
            pUID = .UID
            pUnit = .Unit
            pDate = .DateEvent
            pWO = .WorkOrder
            pTitle = .Title
            Set prsEvent = .rsEvent
            'Debug.Print prsEvent.State, prsEvent.Source
        End With
    End If
    
    If FullPath <> "" Then
        pFullPathCurrent = FullPath 'dont actually use this
        
        Else
        setFullPathDB
        pFullPathCurrent = pFullPathDB 'Make pathDB a property get/set?
    End If
    
    'extract values from fullpath
    If pFullPathCurrent <> "" Then parseFolderTitle

    'Get variables last resorts
    If aTitle <> "" Then pTitle = aTitle
    If pTitleCurrent <> "" And pTitleCurrent <> pTitle Then pFixFolder = True
    If pTitle = "" And pTitleCurrent <> "" Then
        pTitle = pTitleCurrent ' If we don't have title yet, get it from the current folder
        ElseIf pTitle = "" And Not prsEvent Is Nothing Then
        pTitle = prsEvent!Title
    End If
    If pWO = "" And Not prsEvent Is Nothing Then 'get WO from DB
        If Not IsNull(prsEvent!WorkOrder) Then pWO = prsEvent!WorkOrder
    End If
    If aMineSite <> "" Then pMineSite = aMineSite
    
    Query = "Select * From UnitID Where Unit='" & pUnit & "'"
    Dim db As New cDB
    db.OpenConn
    db.rs.Open Query, db.conn, adOpenStatic, adLockReadOnly
    With db.rs
        If .RecordCount = 1 Then
            pMineSite = !MineSite
            pSerial = !Serial
            pModel = !Model
        End If
        .Close
    End With
    
    pstrDate = Format(pDate, getDateFormat(pMineSite))
    pYear = Year(pDate)
    
    'Set Unit folder
    Select Case pMineSite
        Case "Bighorn"
            pUnitPath = pModel & "\" & pUnit & " - " & pSerial
        Case Else
            pUnitPath = pUnit & " - " & pSerial
    End Select
    
    'set BasePath
    Select Case pMineSite
        Case "BaseMine"
            pBasePath = "P:\Fort McMurray\service\2. Customer Equipment Files\1. Suncor\1. Trucks\" _
                            & getModelPath(pUnit) _
                            & "\" & pUnitPath
        Case "FortHills"
            pBasePath = "P:\Fort Hills\02. Equipment Files\1. 980E Trucks\" _
                            & pUnitPath & "\Events\" & pYear
        Case "FH-TKMC"
            pBasePath = "P:\Fort McMurray\service\2. Customer Equipment Files\5. KMC\1. Trucks\1. 930E\" _
                            & pUnitPath & "\Events\" & pYear
        Case "HeavyMetal"
            pBasePath = "P:\Fort McMurray\service\2. Customer Equipment Files\16. Heavy Metal\1. Trucks\" _
                            & pUnitPath & "\Events\" & pYear
        Case "Bighorn"
            pBasePath = "P:\Acheson\COALSPUR - BIGHORN\02. Equipment Files\" _
                            & pUnitPath & "\Events\" & pYear
    End Select
    If pBasePath = "" Then Err.Raise 222, , "pBasePath not set, exiting Init function"
    
    'set Event/Failure folder title
    If pTitle = "" Then Err.Raise 223, , "Title not set, exiting Init function"
    Select Case pMineSite
        Case "BaseMine"
            pFolderTitle = pUnit & " - " & pstrDate & " - " & pTitle
            
        Case Else
            If hasWO Then 'WO not missing
                pFolderTitle = pUnit & " - " & pstrDate & " - " & pWO & " - " & pTitle
                Else 'WO missing
                pFolderTitle = pUnit & " - " & pstrDate & " - " & pWOTemp & " - " & pTitle
            End If
    End Select
    pReportTitle = pUnit & " - " & pstrDate & " - " & pTitle
    
    'Set FailurePath
    Select Case pMineSite
        Case "BaseMine"
            pFullPath = pBasePath & "\Failure Reports\" & pYear & "\" & pFolderTitle
        Case Else
            pFullPath = pBasePath & "\" & pFolderTitle
    End Select
    
    If pFullPathCurrent <> "" And pFullPathCurrent <> pFullPath Then pFixFolder = True
    
    If pFixFolder Then RenameFolder False
    
    'Pics/Dls
    If pMinsite <> "BaseMine" Then
        setRsEvent
        pPicsPath = pFullPath & "\Pictures"
        pDlsPath = pFullPath & "\Downloads"

        With pFso
            'Pictures - count files
            If .FolderExists(pPicsPath) Then
                Set pPicsFolder = .GetFolder(pPicsPath)

                'Get collection of all picture files in all folders
                Dim PicsColl As New Collection
                Set PicsColl = getFiles(pPicsFolder, PicsColl)
                
                'Move picture files to highest picture folder
                For Each pFile In PicsColl
                    'Debug.Print pFile.Type
                    If pFile.Name = "Thumbs.db" Then
                        pFile.Delete
                        Else
                        destpath = pPicsPath & "\" & pFile.Name
                        If pFso.fileExists(destpath) Then
                            Debug.Print "Cant Move:", destpath
                            Else
                            pFso.MoveFile pFile.path, destpath
                        End If
                    End If
                Next
                
                'Delete all empty folders
                For Each pFolder In pPicsFolder.subfolders
                    If isFolderEmpty(pFolder) Then pFso.DeleteFolder pFolder.path
                Next
                
                pNumPics = pPicsFolder.Files.Count
            End If
            
            'Downloads - Check if DLS folders exist
            If .FolderExists(pDlsPath) Then
                Set pFolder = pFso.GetFolder(pDlsPath)
                If Not isFolderEmpty(pFolder) Then pDls = True
            End If
        End With
        
        With prsEvent
            If !Pictures <> pNumPics Or !Downloads <> pDls _
                Or (IsNull(!Pictures) And pFso.FolderExists(pPicsPath)) Then  'Don't edit record if we don't need to
                !Pictures = pNumPics
                !Downloads = pDls
                .Update
            End If
        End With
        If CStr(e.val("Pics")) <> CStr(pNumPics) Then e.val("Pics") = pNumPics
        If e.val("DLS") <> pDls Then e.val("DLS") = pDls
        
    End If
    
cleanup:
'    PrintVars
    Exit Sub
errHandle:
    sendErrMsg "cEventFolder.init"
    Resume cleanup
End Sub
Private Sub parseFolderTitle()
    On Error GoTo errHandle
    
    parrFullPath = Split(pFullPathCurrent, "\")
    pFolderTitleCurrent = parrFullPath(UBound(parrFullPath, 1)) ' get the last part of the full path after "\"
    
    parrFolderTitle = Split(pFolderTitleCurrent, " - ")
    If UBound(parrFolderTitle) < 1 Then GoTo cleanup ' exit if the title isnt correct.
    
    pUnit = Trim(parrFolderTitle(0))
    pstrDate = parrFolderTitle(1)
    
    If IsDate(pstrDate) Then
        pDate = DateValue(pstrDate)
        ElseIf pstrDate = pDateTemp Then 'Try to fix temp date
            'Debug.Print "FixFolder TempDate"
            pFixFolder = True
    End If
    
    posDelim = 3
    str3 = parrFolderTitle(2)
    If isWorkOrder(CStr(str3)) Then
        pWO = str3
        ElseIf str3 Like "*WO      *" And hasWO Then 'Try to fix temp WO
            'Debug.Print "FixFolder WO"
            pFixFolder = True
            
            Else 'the rest is a title
            posDelim = 2
    End If
    
    strPos = CharPos(pFolderTitleCurrent, " - ", CLng(posDelim))
    pFolderTitleCurrent = Trim(Right(pFolderTitleCurrent, Len(pFolderTitleCurrent) - strPos - 2))

cleanup:
    Exit Sub
errHandle:
    sendErrMsg "cEventFolder.parseFolderTitle"
    Resume cleanup
End Sub

Public Sub RenameFolder(Optional Complain As Boolean = True)
    On Error GoTo errHandle
    setRsEvent
    
    'Set from and to paths
    pFromPath = pFullPathCurrent
    pToPath = pFullPath
    
    If Not pFso.FolderExists(pFromPath) Then
        If Not Complain Then GoTo cleanup
        MsgBox "Can't find old path, please select folder."
        Set pfDialog = Application.FileDialog(msoFileDialogFolderPicker)
        With pfDialog
            .Title = "Select Event Folder"
            .InitialFileName = pBasePath
            If .Show = -1 Then
                pFromPath = .SelectedItems(1)
                Else
                GoTo cleanup
            End If
        End With
    End If
    
    pFso.MoveFolder Source:=pFromPath, Destination:=pToPath

    'confirm if change successful > will likely get caught by an error with fso.movefolder^ first
    If Not pFso.FolderExists(pToPath) Then
        MsgBox "Folder not renamed."
        GoTo cleanup
    End If

    'only change Title and Filepath in db once folder is confirmed changed
    With prsEvent
        If !Title <> pTitle Then !Title = pTitle 'hmmmm
        !FilePath = pToPath
        .Update
    End With
    
    If Complain Then MsgBox "Folder renamed" & dLine & "From: " & Line & pFromPath & dLine & "To: " & Line & pToPath, , "Folder Renamed"

cleanup:
    On Error Resume Next
    cleanupDB 'Maybe don't need?
    Exit Sub
errHandle:
    If Err.Number = 70 Then 'permission denied
        ErrMsg = "Folder not able to be renamed. This is likely because someone has a file in the folder open. Ensure all users are closed out of  " _
                & "files in this folder and try again."
        If Complain Then
            MsgBox ErrMsg, vbCritical, "Permission Denied"
            Else
            Debug.Print ErrMsg
        End If
        GoTo cleanup
    End If
    sendErrMsg "cEventFolder.RenameFolder"
    Resume cleanup
End Sub

Public Property Get FullPath() As String
    FullPath = pFullPath
End Property
Public Property Get ReportTitle() As String
    ReportTitle = pReportTitle
End Property
Public Property Get DateEvent() As Date
    DateEvent = pDate
End Property
Public Property Get Title() As String
    Title = pTitle
End Property
Public Property Get Unit() As String
    Unit = pUnit
End Property
Public Property Get WO() As String
    WO = pWO
End Property
Public Property Get FolderTitle()
    FolderTitle = pFolderTitle
End Property
Public Property Get ImagePath()
    On Error GoTo errHandle
    
    'Basemine finds complete image path with partial path using unit & date, or have user select if not found
    'FH finds the exact picture folder, basemine checks for a folder with a matching unit & date
    Select Case pMineSite
        Case "BaseMine"
            ImgPath1 = pBasePath & "\Pictures\" & pYear & "\"
            ImgPath2 = pUnit & " - " & Format(pDate, "mm-dd-yyyy") & " - *"
            ImgPath3 = Dir(ImgPath1 & ImgPath2, vbDirectory) 'blank if can't find folder, returns the upper level folder?
            
            If ImgPath3 <> "" Then
                ImagePath = ImgPath1 & ImgPath3
                Else
                GoTo pathNotFound
            End If
        
        Case Else
            ImgPath1 = pBasePath
            ImgPath2 = checkFolderPath(ImgPath1 & "\" & pFolderTitle) 'this will check with normal title then fix (from db) if needed
            If ImgPath2 = False Then GoTo pathNotFound
            ImgPath3 = ImgPath2 & "\Pictures" 'this doesn't work if the event folder title has been changed...?
            
            If pFso.FolderExists(ImgPath3) Then
                ImagePath = ImgPath3
                Else
                GoTo pathNotFound
            End If
    End Select
    
    GoTo cleanup
    
pathNotFound:
    MsgBox "Image folder not found, please select."
    Set pfDialog = Application.FileDialog(msoFileDialogFolderPicker)
    With pfDialog
        .Title = "Select Picture Folder"
        .InitialFileName = ImgPath1
        If .Show = -1 Then ImagePath = .SelectedItems(1)
    End With
    
cleanup:
    Set pfDialog = Nothing
    Exit Function
errHandle:
    sendErrMsg "cEventFolder.ImgPath"
    Resume cleanup
End Property
Private Function checkFolderPath(aPath) As Variant
    On Error GoTo errHandle
    
    If pFso.FolderExists(aPath) Then
        checkFolderPath = aPath 'we gucci
        
        Else 'not gucci > check the db for filepath
        
        If pMineSite = "BaseMine" Then 'just create the failure reports folder for now
            'CreateEventFolder
            BuildFullPath aPath
            checkFolderPath = aPath
            Exit Function
        End If
        
        aPath = pFullPathDB
        
        If pFso.FolderExists(aPath) Then 'we gucci
            checkFolderPath = aPath
            
            Else 'not gucci
            answer = MsgBox("Can't find event folder. Would you like to link it now?", vbYesNo, "Missing Event Folder")
            If answer = vbYes Then
                Set pfDialog = Application.FileDialog(msoFileDialogFolderPicker)
                With pfDialog
                    .Title = "Select Event Folder"
                    .InitialFileName = pBasePath
                    If .Show = -1 Then
                        aPath = pfDialog.SelectedItems(1)
                        With prsEvent 'add path to db for next time
                            !FilePath = aPath
                            .Update
                        End With
                        MsgBox "Filepath successfully linked to event in database: " & Line & aPath, , "Filepath Linked"
                        checkFolderPath = aPath
                        
                        Else 'not gucci
                        MsgBox "Folder path not found.", vbCritical
                        checkFolderPath = False
                    End If
                End With
                Else
                checkFolderPath = False
            End If
        End If
    End If

cleanup:
    Exit Function
errHandle:
    sendErrMsg "checkFolderPath"
    checkFolderPath = False
End Function

Public Function hasEventFolder() As Boolean
    If pFso.FolderExists(pFullPath) Then
        hasEventFolder = True
        Else
        hasEventFolder = False
    End If
End Function
Public Sub CreateEventFolder(Optional ViewAfterBuild As Boolean = False)
    On Error GoTo errHandle
    Select Case pMineSite
        Case "BaseMine"
            BuildFullPath pFullPath 'not used yet
        Case Else
            BuildFullPath pPicsPath
            BuildFullPath pDlsPath
    End Select
    
    With prsEvent
        !FilePath = pFullPath
        .Update
        .Close
    End With
    
    If ViewAfterBuild = True Then
        answer = MsgBox("Event folder created. Open now?", vbYesNo, "Event Folder Created")
        If answer = vbYes Then ViewFolder
    End If

cleanup:
    Exit Sub
errHandle:
    sendErrMsg "cEventFolder.CreateEventFolder"
    Resume cleanup
End Sub
Public Sub ViewFolder()
    On Error GoTo errHandle
    Dim aPath As Variant
    aPath = checkFolderPath(pFullPath)
    If aPath <> False Then 'We Gucci
        ThisWorkbook.FollowHyperlink aPath
        Else
        ans = MsgBox("Folder does not exist. Create now?", vbYesNo + vbQuestion, "Create Folder")
        If ans = vbYes Then CreateEventFolder True
    End If
cleanup:
    Exit Sub
errHandle:
    sendErrMsg "cEventFolder.ViewFolder"
    Resume cleanup
End Sub

Private Function hasWO() As Boolean
    If Len(pWO) > 0 Then
        If isWorkOrder(pWO) Then
            hasWO = True
            Exit Function
        End If
    End If
    hasWO = False
End Function
Private Function hasDate() As Boolean
    
End Function
Public Property Get NumPics() As Integer
    NumPics = pNumPics
End Property
Private Function isWorkOrder(strWO As String) As Boolean
    strWO = Trim(strWO)
    If IsNumeric(Right(strWO, 7)) And Left(strWO, 2) = "WO" Then
        isWorkOrder = True
        Else
        isWorkOrder = False
    End If
End Function

Public Sub PrintVars()
    Debug.Print "pMineSite", pMineSite
    Debug.Print "pUnit", pUnit
    Debug.Print "pSerial", pSerial
    Debug.Print "pModel", pModel
    Debug.Print "pDate", pDate
    Debug.Print "pstrDate", pstrDate
    Debug.Print "pWO", pWO
    Debug.Print "pTitle", pTitle
    Debug.Print "pTitleCurrent", pTitleCurrent
    Debug.Print "pYear", pYear
    Debug.Print "pUID", pUID
'    Debug.Print "pDateTemp", pDateTemp
    Debug.Print "pUnitPath", pUnitPath
    Debug.Print "pBasePath", pBasePath
    Debug.Print "pFolderTitle", pFolderTitle
    Debug.Print "pFolderTitleCurrent", pFolderTitleCurrent
    Debug.Print "pFullPath", pFullPath
    Debug.Print "pFullPathCurrent", pFullPathCurrent
    Debug.Print "pFullPathDB", pFullPathDB
'    Debug.Print "pFromPath", pFromPath
'    Debug.Print "pToPath", pToPath
    Debug.Print "pNumPics", pNumPics
    Debug.Print "pDls", pDls
    Debug.Print "pFixFolder", pFixFolder
End Sub
Private Sub class_initialize()
    pMineSite = getMineSite(True)
    Set pFso = CreateObject("Scripting.FileSystemObject")
    
    'Set prsSerial = loadSerialRecordset(True)
    
    pDateTemp = "0000-00-00"
    pWOTemp = "WO              "
    pNumPics = 0
    pDls = False
    
End Sub
Private Sub setFullPathDB()
    setRsEvent
    If prsEvent Is Nothing Then Err.Raise 444, , "prsEvent not set."
    If Not IsNull(prsEvent!FilePath) Then pFullPathDB = prsEvent!FilePath
End Sub
Private Sub setRsEvent()
    On Error GoTo errHandle
    If pUID = 0 Then Exit Sub
    
    If prsEvent Is Nothing Then
        Dim db As New cDB
        db.OpenConn
        db.rs.Open getUIDQuery(pUID), db.conn, adOpenStatic, adLockOptimistic
        Set prsEvent = db.rs
    End If
    
cleanup:
    On Error Resume Next
    Exit Sub
errHandle:
    sendErrMsg "cEventFolder.setRsEvent"
    Resume cleanup
End Sub

Public Sub TearDown()
    On Error Resume Next
    prsEvent.Close
    Set prsEvent = Nothing
End Sub
