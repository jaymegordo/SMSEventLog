VERSION 1.0 CLASS
BEGIN
  MultiUse = -1  'True
END
Attribute VB_Name = "cGeneralObject"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = False
Attribute VB_PredeclaredId = False
Attribute VB_Exposed = False
Option Explicit
' since we are going to enable timers using multiple shapes this class will provide
' a standard access to specific properties of multiple shapes
Private pVertical As Boolean
Private pObject As Object
Private pCenter As Boolean
Public Sub init(o As Object, Optional bVertical As Boolean = False, _
                                Optional bCenter As Boolean = False)
    Set pObject = o
    pVertical = bVertical
    pCenter = bCenter
    
End Sub
Public Property Get isaShape() As Boolean
    isaShape = (TypeName(pObject) = "Shape")
End Property
Public Property Get Object() As Object
    Set Object = pObject
End Property
Public Property Get size() As Double
    If pVertical Then
        size = height
    Else
        size = width
    End If
End Property
Public Property Get height() As Double
    If isaShape Then
        height = toShape.height
    Else
        height = toControl.height
    End If
End Property
Public Property Get width() As Double
    If isaShape Then
        width = toShape.width
    Else
        width = toControl.width
    End If
End Property
Public Property Get value() As String
    If isaShape Then
        value = toShape.TextFrame.Characters.Text
    ElseIf gTypeName = "Label" Then
        value = toLabel.Caption
    Else
        value = pObject.value
    End If
End Property
Public Property Get Fill() As Long
    If isaShape Then
        Fill = toShape.Fill.BackColor.RGB
    Else
        Fill = Object.BackColor
    End If
End Property
Public Property Get visible() As Boolean
    If isaShape Then
        visible = toShape.visible
    Else
        visible = Object.visible
    End If
End Property
Public Property Get gTypeName() As String
    
    If isaShape Then
        gTypeName = TypeName(toShape.OLEFormat.Object)
    Else
        gTypeName = TypeName(pObject)
    End If
    
End Property
Public Property Let height(p As Double)
    If isaShape Then
        toShape.height = p
    Else
        toControl.height = p
    End If
End Property
Public Property Let width(p As Double)
    If isaShape Then
         toShape.width = p
    Else
         toControl.width = p
    End If
End Property
Public Property Let value(p As String)
    If isaShape Then
        toShape.TextFrame.Characters.Text = p
    ElseIf gTypeName = "Label" Then
        toLabel.Caption = p
    Else
        pObject.value = p
    End If
End Property
Public Property Let Fill(p As Long)
    If isaShape Then
        toShape.Fill.Solid
        toShape.Fill.BackColor.RGB = p
    Else
        Object.BackColor = p
    End If
End Property
Public Property Let visible(p As Boolean)
    If isaShape Then
        toShape.visible = p
    Else
        Object.visible = p
    End If
End Property
Public Property Let size(p As Double)
    
    ' if we need to keep the object centered around the same spot, then we'd need
    ' to adapt the top and left

    If pCenter Then
        pObject.Left = (size - p) / 2 + pObject.Left
        pObject.top = (size - p) / 2 + pObject.top
    End If
    
    If pVertical Then
        height = p
    Else
        width = p
    End If
End Property
 Public Property Get toShape() As Shape
    Set toShape = pObject
 End Property
 Public Property Get toControl() As Control
    Set toControl = pObject
 End Property
 Public Property Get toLabel() As MSForms.label
    Set toLabel = pObject
 End Property
Public Property Get toTextBox() As MSForms.TextBox
    Set toTextBox = pObject
 End Property

