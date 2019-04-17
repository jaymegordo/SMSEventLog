VERSION 5.00
Begin {C62A69F0-16DC-11CE-9E98-00AA00574A4F} FCSelector 
   Caption         =   "Select Factory Campaign"
   ClientHeight    =   1425
   ClientLeft      =   90
   ClientTop       =   366
   ClientWidth     =   7464
   OleObjectBlob   =   "FCSelector.frx":0000
   StartUpPosition =   1  'CenterOwner
End
Attribute VB_Name = "FCSelector"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = False
Attribute VB_PredeclaredId = True
Attribute VB_Exposed = False
Private pEvent As cEvent
Private pf As cFilter

Private Sub Cancel_Click()
    Unload Me
    AddEvent.CheckBox_FC.value = False
End Sub

Private Sub Okay_FC_Click()
    If pEvent Is Nothing Then Set pEvent = New cEvent

    'extract the 'FCNumber' from start of string till first blank space
    pEvent.FCNumber = Left(ComboBox_FC.value, InStr(1, ComboBox_FC.value, " "))
    aFC = Replace(ComboBox_FC.value, "|", "-")
    
    If tag = "FCNum" Then
        'run query with FC number
        Me.Hide
        Set pf = New cFilter
        pf.add "FactoryCampaign.FCNumber=", pEvent.FCNumber
        RefreshTable iws:=7, f:=pf
        Else
        'add to AddEvent form
        pEvent.msgFCExpired
        AddEvent.TextBox_Title.value = "FC " & aFC
    End If

    Unload Me
End Sub

Public Sub init(Evnt As cEvent)
    Set pEvent = Evnt
End Sub
Private Sub userform_initialize()
    On Error GoTo errHandle
    centerUserform Me
    
    Dim rs As ADODB.Recordset
    Set rs = loadFCRecords
    With rs
        ComboBox_FC.value = !FCNumber & " | " & !CalcSubj
        
        Do While .EOF <> True
            ComboBox_FC.AddItem !FCNumber & " | " & !CalcSubj
            .MoveNext
        Loop
    End With
    
    With ComboBox_FC
        .SelStart = 0
        .SelLength = .textLength
    End With
    
cleanup:
    On Error Resume Next
    rs.Close
    Exit Sub
errHandle:
    sendErrMsg "FCSelector_UserForm_Initialize"
    Resume cleanup
End Sub
