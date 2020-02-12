VERSION 1.0 CLASS
BEGIN
  MultiUse = -1  'True
END
Attribute VB_Name = "cwbExport"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = False
Attribute VB_PredeclaredId = False
Attribute VB_Exposed = False
'Workbook/Worksheet/Table Export/Copy

Private pBasePath As String
Private pFullPath As String
Private pDestName As String
Private pWbName As String

Private pwbDest As Workbook
Private pwbSource As Workbook
Private pCollws As Collection
Private pFso As Scripting.FileSystemObject

Public Property Get WbName() As String
    WbName = pWbName
End Property

Public Property Get DestName() As String
    DestName = pDestName
End Property
Public Property Let DestName(ByVal sDestName As String)
    pDestName = sDestName
End Property

Public Property Get FilePath() As String
    If pFullPath = "" Then pFullPath = pBasePath & pDestName
    FilePath = pFullPath
End Property
Public Property Get wbSource() As Workbook
    Set wbSource = pwbSource
End Property
Public Property Set wbSource(oWbSource As Workbook)
    Set pwbSource = oWbSource
End Property

Public Property Get wbDest() As Workbook
    Set wbDest = pwbDest
End Property
Public Property Set wbDest(oWbDest As Workbook)
    Set pwbDest = oWbDest
End Property

Public Function ws(num) As Worksheet
    Set ws = pCollws.Item(num)
End Function

Public Function addWs(ws As Worksheet, Optional wsReplace As Worksheet) As Worksheet
    On Error GoTo errHandle
    Dim replaceWS As Boolean
    Application.DisplayAlerts = False
    i = 1
    If wsReplace Is Nothing Then
        For Each wsReplace In pwbDest.Worksheets
            If wsReplace.Name = ws.Name Then
                i = wsReplace.Index - 1
                wsReplace.Delete
                Exit For
            End If
        Next
        
        Else
        sReplaceName = wsReplace.Name
        replaceWS = True
        i = wsReplace.Index - 1
        wsReplace.Delete
    End If
    
    ws.Copy After:=pwbDest.Sheets(i)
    Set ws = pwbDest.Sheets(ws.Name)
    ws.Tab.Color = False
    pCollws.add pwbDest.Sheets(ws.Name)
    If replaceWS Then ws.Name = sReplaceName
    
    'Set addWs = pwbDest.Sheets(ws.Name)
    
cleanup:
    On Error Resume Next
    Application.DisplayAlerts = True
    Exit Function
errHandle:
    sendErrMsg "cwbExport.addWs"
    Resume cleanup
End Function

Public Sub createWb(Optional sName As String)
    If sName <> "" Then pDestName = sName
    pFullPath = pBasePath & pDestName
    deleteDestWb
    Set pwbDest = Workbooks.add
    pwbDest.SaveAs fileName:=pFullPath, FileFormat:=fFormat
    copyColours
End Sub
Private Sub class_initialize()
    Set pwbSource = ThisWorkbook
    Set pCollws = New Collection
    Set pFso = New Scripting.FileSystemObject
    pBasePath = Environ$("temp") & "\"
    pWbName = trimExtension(pwbSource.Name)
End Sub
Public Sub deleteDestWb()
    If Dir(pFullPath) <> "" Then Kill pFullPath
End Sub
Private Function fFormat() As Long
    Select Case Extension
        Case ".xlsm"
            fFormat = xlOpenXMLWorkbookMacroEnabled
        Case ".xlsx"
            fFormat = xlOpenXMLWorkbook
    End Select
End Function
Private Function Extension() As String
    periodPos = InStrRev(pFullPath, ".")
    Extension = Right(pFullPath, Len(pFullPath) - periodPos + 1)
End Function
Private Function trimExtension(sName As String) As String
    periodPos = InStrRev(sName, ".")
    trimExtension = Left(sName, periodPos - 1)
End Function
Public Sub copyColours()
    'Copy colour theme to new wb
    Dim TempThemeFile As String
    Dim sourceTheme As Object
    Set sourceTheme = pwbSource.Theme.ThemeColorScheme
    TempThemeFile = Environ$("temp") & "\xltheme" & Format(Now, "dd-mm-yy h-mm-ss") & ".xml"
    sourceTheme.Save TempThemeFile
    pwbDest.Theme.ThemeColorScheme.Load TempThemeFile
    Kill TempThemeFile
End Sub


'------------------Export Code Modules------------------

Public Sub CopyModule(strModuleName As String) ' Export specific module from source to dest workbook
    Dim strFolder As String
    Dim strTempFile As String
    Dim FName As String
    
    If Trim(strModuleName) = vbNullString Then Exit Sub

    If pwbDest Is Nothing Then
        MsgBox "Error: Target Workbook " & pwbDest.Name & " doesn't exist (or closed)", vbCritical
        Exit Sub
    End If

    strFolder = pwbSource.path
    If Len(strFolder) = 0 Then strFolder = CurDir

    ' create temp file and copy "Module2" into it
    strFolder = strFolder & "\"
    strTempFile = strFolder & "~tmpexport.bas"

    On Error Resume Next
    FName = Environ("Temp") & "\" & strModuleName & ".bas"
    If Dir(FName, vbNormal + vbHidden + vbSystem) <> vbNullString Then
        Err.clear
        Kill FName
        If Err.Number <> 0 Then
            MsgBox "Error copying module " & strModuleName & "  from Workbook " & pwbSource.Name & " to Workbook " & pwbDest.Name, vbInformation
            Exit Sub
        End If
    End If

    ' remove "Module2" if already exits in destination workbook
    With pwbDest.VBProject.VBComponents
        .remove .Item(strModuleName)
    End With

    ' copy "Module2" from temp file to destination workbook
    pwbSource.VBProject.VBComponents(strModuleName).Export strTempFile
    pwbDest.VBProject.VBComponents.Import strTempFile

    Kill strTempFile
    On Error GoTo 0

End Sub

Public Sub ExportAllModules(Optional sBasePath As String)  'Export everything to folder
    On Error GoTo errHandle
    Dim bExport As Boolean
    Dim cmpComponent As VBIDE.VBComponent
    
    If sBasePath = "" Then sBasePath = Environ("userprofile") & "\Documents\VBA Projects\"
    If Right(sBasePath, 1) <> "\" Then sBasePath = sBasePath & "\"
    
    sExportFolder = sBasePath & pWbName
    If Not pFso.FolderExists(sExportFolder) Then BuildFullPath (sExportFolder)
    
    Debug.Print sExportFolder
    On Error Resume Next
        Kill sExportFolder & "\*.*"
    On Error GoTo errHandle
    
    For Each cmpComponent In pwbSource.VBProject.VBComponents
        bExport = True
        sFileName = cmpComponent.Name
        
        Select Case cmpComponent.Type
            Case vbext_ct_ClassModule
                sFileName = sFileName & ".cls"
            Case vbext_ct_MSForm
                sFileName = sFileName & ".frm"
            Case vbext_ct_StdModule
                sFileName = sFileName & ".bas"
            Case vbext_ct_Document 'This is a worksheet or workbook object.
                bExport = False
            Case Else
                bExport = False
        End Select
        
        If bExport Then cmpComponent.Export sExportFolder & "\" & sFileName
        
    Next cmpComponent
    
    ThisWorkbook.FollowHyperlink sExportFolder

cleanup:
    On Error Resume Next
    Exit Sub
errHandle:
    sendErrMsg "cwbExport.ExportAllModules"
    Resume cleanup
End Sub


Public Sub ImportModules()
    Dim wkbTarget As Excel.Workbook
    Dim objFSO As Scripting.FileSystemObject
    Dim objFile As Scripting.File
    Dim szTargetWorkbook As String
    Dim szImportPath As String
    Dim sFileName As String
    Dim cmpComponents As VBIDE.VBComponents

    If ActiveWorkbook.Name = ThisWorkbook.Name Then
        MsgBox "Select another destination workbook" & _
        "Not possible to import in this workbook "
        Exit Sub
    End If

    'Get the path to the folder with modules
    If FolderWithVBAProjectFiles = "Error" Then
        MsgBox "Import Folder not exist"
        Exit Sub
    End If

    ''' NOTE: This workbook must be open in Excel.
    szTargetWorkbook = ActiveWorkbook.Name
    Set wkbTarget = Application.Workbooks(szTargetWorkbook)
    
    If wkbTarget.VBProject.Protection = 1 Then
    MsgBox "The VBA in this workbook is protected," & _
        "not possible to Import the code"
    Exit Sub
    End If

    ''' NOTE: Path where the code modules are located.
    szImportPath = FolderWithVBAProjectFiles & "\"
        
    Set objFSO = New Scripting.FileSystemObject
    If objFSO.GetFolder(szImportPath).Files.Count = 0 Then
       MsgBox "There are no files to import"
       Exit Sub
    End If

    'Delete all modules/Userforms from the ActiveWorkbook
    Call DeleteVBAModulesAndUserForms

    Set cmpComponents = wkbTarget.VBProject.VBComponents
    
    ''' Import all the code modules in the specified path
    ''' to the ActiveWorkbook.
    For Each objFile In objFSO.GetFolder(szImportPath).Files
    
        If (objFSO.GetExtensionName(objFile.Name) = "cls") Or _
            (objFSO.GetExtensionName(objFile.Name) = "frm") Or _
            (objFSO.GetExtensionName(objFile.Name) = "bas") Then
            cmpComponents.Import objFile.path
        End If
        
    Next objFile
    
    MsgBox "Import is ready"
End Sub


Function DeleteVBAModulesAndUserForms()
        Dim VBProj As VBIDE.VBProject
        Dim VBComp As VBIDE.VBComponent
        
        Set VBProj = ActiveWorkbook.VBProject
        
        For Each VBComp In VBProj.VBComponents
            If VBComp.Type = vbext_ct_Document Then
                'Thisworkbook or worksheet module
                'We do nothing
            Else
                VBProj.VBComponents.remove VBComp
            End If
        Next VBComp
End Function




