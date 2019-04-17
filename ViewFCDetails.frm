VERSION 5.00
Begin {C62A69F0-16DC-11CE-9E98-00AA00574A4F} ViewFCDetails 
   Caption         =   "Load FCs"
   ClientHeight    =   4890
   ClientLeft      =   90
   ClientTop       =   300
   ClientWidth     =   3336
   OleObjectBlob   =   "ViewFCDetails.frx":0000
   StartUpPosition =   1  'CenterOwner
End
Attribute VB_Name = "ViewFCDetails"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = False
Attribute VB_PredeclaredId = True
Attribute VB_Exposed = False
Private pf As cFilter
Private pIws As Integer

Private Sub ckMineSite_Click()
    With cbMineSite
        If .Enabled Then
            .Enabled = False
            Else
            .Enabled = True
        End If
    End With
End Sub

Private Sub ckModel_Click()
    With cbModel
        If .Enabled Then
            .Enabled = False
            Else
            populateCombobox cbModel, rs:=getQuery("Model")
            .Enabled = True
        End If
    End With
End Sub



Private Sub userform_initialize()
    On Error GoTo errHandle
    
    Set pf = New cFilter
    Dim ws As Worksheet
    Set ws = Worksheets("Lists")
    Dim tbl As ListObject
    Set tbl = ws.ListObjects("MineSite_Table")
    
    pIws = getWSInt(ActiveSheet.CodeName)
    
    populateCombobox cbMineSite, rs:=getQuery("MineSite")
    MineSite = getMineSite(True)
    cbMineSite.value = MineSite
    If MineSite = "FortHills" Or MineSite = "BaseMine" Then
        ckModel.value = True
        cbModel.value = "980*"
    End If
    centerUserform Me
    ckOpenOnly.value = True

cleanup:
    On Error Resume Next
    Exit Sub
errHandle:
    sendErrMsg "ViewFCDetails.userform_initialize"
    Resume cleanup
End Sub
Private Sub btnOkay_Click()
    On Error GoTo errHandle
    Dim sFilter As String
    Dim sField As String
    Dim RefreshType As String
    
    Select Case pIws
        Case 8
            dbTable = "UnitID"
        Case 7
            dbTable = "t1"
    End Select
    
    'MineSite
    If cbMineSite.Enabled Then pf.add dbTable & ".MineSite=", cbMineSite
    
    'OpenOnly
    If ckOpenOnly.value Then
        Select Case pIws
            Case 8
                pf.add "(tFCS.ManualClosed ='False' OR tFCS.ManualClosed Is Null)"
            Case 7
                RefreshType = "AllOpenFC"
        End Select
    End If
    
    'CustomerFriendly
    If ckCustomerFriendly.value Then
        sFilter = "(FCSummary.NotCustomerFriendly<>'True' Or FCSummary.NotCustomerFriendly Is Null)"
        Select Case pIws
            Case 8
                f.add sFilter
            Case 7
                pf.Filter2.add sFilter
        End Select
    End If
    
    'Delivered Only
    If ckDeliveredOnly Then
        sFilter = "UnitID.DeliveryDate Is Not Null"
        Select Case pIws
            Case 8
                f.add sFilter
            Case 7
                pf.Filter2.add sFilter
        End Select
    End If
    
    'ManualClosed
    If Not ckManualClosed.value Then
        Select Case pIws
            Case 8
                dbTable = "tFCS"
            Case 7
                dbTable = "FCSummaryMineSite"
        End Select
        pf.add "(" & dbTable & ".ManualClosed<>'True' OR " & dbTable & ".ManualClosed Is Null)"
    End If
    
    'Exclude FAF
    If ckFAF.value Then
        sField = "FactoryCampaign.Classification<>"
        Select Case pIws
            Case 8
                pf.add sField, "FAF"
            Case 7
                pf.Filter2.add sField, "FAF"
        End Select
    End If
    
    'Model
    If ckModel.value Then
        If cbModel.value Like "*" Then
            Comparison = " Like "
            Else
            Comparison = " = "
        End If
        
        sFilter = "UnitID.Model" & Comparison & " '" & Replace(cbModel.value, "*", "%") & "'"
        Select Case pIws
            Case 8
                pf.add sFilter
            Case 7
                pf.Filter2.add sFilter
        End Select
    End If
    
    'pF.printEach
    'pF.printFinal
    
    Me.Hide
    Select Case pIws
        Case 8
            refreshFCSummary pf
        Case 7
            RefreshTable RefreshType:=RefreshType, f:=pf
    End Select

cleanup:
    On Error Resume Next
    Application.EnableEvents = True
    Unload Me
    Exit Sub
errHandle:
    sendErrMsg "ViewFCDetails.btnOkay_Click"
    Resume cleanup
End Sub

Private Sub btnCancel_Click()
    Unload Me
End Sub
