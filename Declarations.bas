Attribute VB_Name = "Declarations"
Public rs As DAO.Recordset
Public rs2 As DAO.Recordset
Public rs3 As DAO.Recordset
Public rs4 As DAO.Recordset
Public rs5 As DAO.Recordset
Public rs6 As DAO.Recordset
Public rsSunBench As DAO.Recordset

Public collConns As Collection
Public gConn As cConn



Public db As DAO.Database
Public db2 As DAO.Database
Public tbl As ListObject
Public dbr As Range
Public wb As Workbook
Public wbn As Workbook
Public ws As Worksheet

Public e As cEvent
Public EventFolder As cEventFolder

Public outlookApp As Object
Public outMail As Object
Public outMail2 As Object
Public wdDoc As Object
Public wdApp As Object
Public FSO As FileSystemObject
Public aFolder As Object 'Folder
Public fDialog As Object 'FileDialog
Public fDialog2 As Object
Public aPath As Variant
Public timeInactive As Date

Public Target As Range
Public SaveCount As Range
Public iws As Integer
Public RefreshType As String
Public wbUpdate As Boolean
Public ErrMsg As String

Public aUID As Double
Public aUnit As String
Public aModel As Variant
Public aSerial As String
Public aDate As Date
Public aTitle As String
Public aFC As String
Public aUnitSMR As Long
Public aSMR As Long
Public aDateAdded As Date
Public aDateCreated As Date
Public aTimeCalled As Date
Public aFCNumber As String
Public i As Integer
Public DateLower As Date
Public DateUpper As Date
Public aSubject As String
Public aClassification As String
Public aReleaseDate As Date
Public aExpiryDate As Date
Public aFloc As String
Public aComponent As String
Public aModifier As String
Public aRemovalReason As String
Public aSNRemoved As String
Public aSNInstalled As String
Public aSide As String
Public aPartSMR As Long
Public aPartName As String
Public aPartNo As String
Public aPartSerial As String
Public aWorkOrder As String
Public aSuncorWO As String
Public aWarrantyYN As String


Public aMessage As String
Public fType As String
Public aFile As String
Public Destination As Range
Public aArray As Variant
Public NumFiles As Integer


