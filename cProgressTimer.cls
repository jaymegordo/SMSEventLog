VERSION 1.0 CLASS
BEGIN
  MultiUse = -1  'True
END
Attribute VB_Name = "cProgressTimer"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = False
Attribute VB_PredeclaredId = False
Attribute VB_Exposed = False
Option Explicit
' this class is a  progress or countdown bar.
' at a minimum it needs a label on a form to use to show progress
' Acknowledgement for the microtimer procedures used here to
' thanks to Charles Wheeler - http://www.decisionmodels.com/


#If VBA7 And Win64 Then
Private Declare PtrSafe Function getTickCount _
    Lib "kernel32" Alias "QueryPerformanceCounter" _
    (cyTickCount As Currency) As Long
Private Declare PtrSafe Function _
    GetDeviceCaps Lib "Gdi32" _
    (ByVal hDC As LongPtr, ByVal nIndex As Long) As Long
#Else
Private Declare Function getTickCount Lib "kernel32" _
Alias "QueryPerformanceCounter" (cyTickCount As Currency) As Long


Private Declare Function getFrequency Lib "kernel32" _
Alias "QueryPerformanceFrequency" (cyFrequency As Currency) As Long
#End If

Private pStart As Double                ' When the current timing session started (since last pause)
Private pCum As Double                  ' cumulative time passed so far
Private pTimeEstimate As Double          ' how long expected to last
Private pSize As Long                 ' original length of progress bar
Private pUpdateInterval As Long         ' how often to update progress bar
Private paProgressBar As Boolean    ' whether we are expanding of contracting to show progress
Private pShowPercentage As Boolean      ' whether to show %age progress on bar
Private psecondFormat                   ' format to use for showing time
Private pTimerColors As Variant           ' bar can change color as progresses
Private pOriginalFill As Long        ' the original background color

Private pTimer As cGeneralObject        ' the progress bar
Private pCountDown As cGeneralObject    ' where to display the number of seconds left
Private pElapsed As cGeneralObject      ' where to display the number of seconds elapsed
Private pbutPause As MSForms.ToggleButton  ' the toggle button that pauses/restarts

Private pScheduledUpdateProcess As String ' the procedure to call when time for an update
Private pWhenOutofTime As String        ' the procedure to call when time is up
Private pNextUpdate As Date             ' scheduled time of next update
Private pActiveScheduled As String      ' the name of the next scheduled procedure

Private pxlApp As Excel.Application     ' the excel object

Public Sub init(formBar As Object, _
                procToCall As String, _
                procOutOfTime As String, _
                Optional timeTarget As Double = 30, _
                Optional aProgressBar As Boolean = False, _
                Optional countDownText As Object = Nothing, _
                Optional elapsedText As Object = Nothing, _
                Optional pauseToggle As MSForms.ToggleButton = Nothing, _
                Optional updateInterval As Double = 1, _
                Optional showPercentage As Boolean = False, _
                Optional secondFormat As String = "#", _
                Optional barColors As Variant = Empty, _
                Optional barVertical As Boolean = False, _
                Optional barCenter As Boolean = False)
                
    ' constructor for countdown - called once to set up options for progress bar
    Set pTimer = New cGeneralObject
    pTimer.init formBar, barVertical, barCenter ' the object to show progress
    
    pTimeEstimate = timeTarget              ' estimated time of task
    pSize = pTimer.size                    ' remember the original length of the label
    

    paProgressBar = aProgressBar             ' whether to increase or decrease length to show progress
    pUpdateInterval = updateInterval        ' how often to update
    pScheduledUpdateProcess = procToCall    ' which provedure to call when time to update
    pActiveScheduled = ""                   ' which procedure is current scheduled
    pWhenOutofTime = procOutOfTime          ' procedure to call when time is up
    Set pbutPause = pauseToggle                 ' optional toggle button to allow pausing
    pShowPercentage = showPercentage        ' whether to chow percentage on progress bar
    psecondFormat = secondFormat            ' format to use when showing time in textboxes
   
    
    ' these are the default colors for the count down bar
    If IsEmpty(barColors) Then
        pTimerColors = Array(vbGreen, vbYellow, vbRed)
    Else
        pTimerColors = barColors
    End If
    pOriginalFill = pTimer.Fill
    
    ' we're going to need this for task scheduling to fully qualify application.
    ' otherwise multiple excel instances seem to be able to screw up the application. object
    Set pxlApp = getObject(, "Excel.Application")

    If Not countDownText Is Nothing Then
        Set pCountDown = New cGeneralObject
        pCountDown.init countDownText
        pCountDown.value = Format(pTimeEstimate, psecondFormat)    ' initialize with initial task estimate
    End If
    
    If Not elapsedText Is Nothing Then
        Set pElapsed = New cGeneralObject
        pElapsed.init elapsedText
        pElapsed.value = Format(0, psecondFormat)                  ' initialize with initial task estimate
    End If

End Sub
Public Sub Update()
' should be called for every scheduled update
    Dim n As Long, rat As Double, relapse As Double
    ' mark this one as executed
    pNextUpdate = 0
    
    If pTimeEstimate > 0 And Not isPaused Then
        flush
       
    End If

    ' schedule another
    scheduleUpdate
    
End Sub
Public Sub start()
    ' this will start a countdown session
    
    ' show the countdown timer
    pTimer.visible = True
    

    ' allow pausing of timer
    If Not pbutPause Is Nothing Then
        pbutPause.visible = True
        pbutPause.Enabled = True
        pbutPause.value = False
        pbutPause.Caption = "Pause"
    End If
    
    showValues vbWhite
    
    ' cumulative time passed
    pCum = 0
    reStart
    
    
End Sub
Public Sub reStart()

    ' start timing and schedule an update
    pStart = cMicroTimer
    Update

End Sub
Public Sub calloutExecuted()
    ' this sub must be executed during the outoftime call to stop further scheduling
    pNextUpdate = 0
End Sub
Public Sub Pause()
    ' this should be called when the pause toggle Button is pressed
    
    If isPaused Then
        ' pause requested
        pCum = Elapsed + pCum
        showValues vbRed
    
    Else
        ' restart requested
        pStart = cMicroTimer
        showValues vbWhite
        ' replot current state
        Update
    End If
End Sub
Public Sub destroy()

    If Not pTimer Is Nothing Then
        
        cancelScheduledUpdate
        pTimer.size = pSize
        pTimer.Fill = pOriginalFill
        pTimer.value = Empty
        pTimeEstimate = 0
        pStart = 0

    End If
   
End Sub
Public Sub flush()
    ' do the update process
    Dim n As Long, rat As Double, relapse As Double
    ' count down or progress bar?
    If Not paProgressBar Then
        pTimer.size = (1 - ratioElapsed) * pSize
    Else
        pTimer.size = ratioElapsed * pSize
    End If
    
    ' show the time left if needed
    If Not pCountDown Is Nothing Then
        pCountDown.value = Format(Remaining, psecondFormat)
    End If
    
    ' show the time elapsed if needed
    If Not pElapsed Is Nothing Then
        pElapsed.value = Format(timeElapsed, psecondFormat)
    End If
    
    ' figure out current bar color
    rat = 1 / (1 + UBound(pTimerColors) - LBound(pTimerColors))
    relapse = ratioElapsed
    For n = LBound(pTimerColors) To UBound(pTimerColors)
        If relapse > rat * (n - LBound(pTimerColors)) Then
            pTimer.Fill = pTimerColors(n)
        End If
    Next n
    
    ' do %age if needed
    If pShowPercentage Then
        pTimer.value = Format(ratioElapsed, "#%")
    End If
    eventsFlush
    
End Sub
Public Sub eventsFlush()
    ' when not idle, the appilcation on time event is not serviced
    ' if there is an outstanding scheduled event this will generate a doevents
    ' using this minimizes the use of doEvents to only when they are essential
    If pNextUpdate <> 0 Then
        If pNextUpdate < Now Then
            DoEvents
        End If
    End If
End Sub
Public Property Get isOutOfTime() As Boolean
    ' returns whethere we are out of time
    isOutOfTime = (ratioElapsed >= 1)
End Property
Public Property Get timeEstimate() As Double
    ' how long is estimated for the entire task being reported on
    timeEstimate = pTimeEstimate
End Property

Public Property Let ratioElapsed(ratioTaskComplete As Double)
    ' need to reset the timeallowe dmid flight
    ' note this actually updates the TimeEstimate property
    If ratioTaskComplete < 1 And ratioTaskComplete > 0 Then
        pTimeEstimate = timeElapsed / ratioTaskComplete
        eventsFlush
    End If
    
End Property
Public Property Get ratioElapsed() As Double
    'return % ratioElapsed
    Dim x As Double
    x = timeElapsed / pTimeEstimate
    If x > 1 Then
        ratioElapsed = 1
    Else
        ratioElapsed = x
    End If
    
    
End Property
Public Property Let timeEstimate(p As Double)
    ' how long is estimated for the entire task being reported on
    ' can be reset mid progres, but usually this would be donw with the ratioElapsed property
    pTimeEstimate = p
    eventsFlush
End Property
Public Property Get timeElapsed() As Double
    timeElapsed = Elapsed + pCum
End Property
'--------------private properties and procedures follow----------

Private Property Get Elapsed() As Double
    ' return time elapsed
    Elapsed = cMicroTimer() - pStart
End Property

Private Property Get Remaining() As Double
    Remaining = pTimeEstimate - timeElapsed
End Property

Private Property Get cPause() As Control
    ' cast pause toggle button as control object
    Set cPause = pbutPause
End Property
Private Property Get isPaused() As Boolean
    ' return whether progress bar is in paused state
    If Not pbutPause Is Nothing Then
        isPaused = pbutPause.value
    Else
        isPaused = False
    End If
End Property
Private Sub showValues(cBack As Long)
    ' allow showing of estimated time remaining
    If Not pCountDown Is Nothing Then
        pCountDown.Fill = cBack
        pCountDown.visible = True
    End If
    
    ' allow showing of elapsed time
    If Not pElapsed Is Nothing Then
        pElapsed.Fill = cBack
        pElapsed.visible = True
    End If
End Sub

Private Sub cancelScheduledUpdate()
    'cancel any scheduled updates
    If pNextUpdate <> 0 Then

        pxlApp.Application.OnTime pNextUpdate, pActiveScheduled, , False
        pNextUpdate = 0

    End If

End Sub
Private Sub scheduleUpdate()
    
     ' in case there are any outstanding - we only need one
    cancelScheduledUpdate
     
    If isOutOfTime Then
        If pActiveScheduled = pWhenOutofTime Then
            MsgBox ("Programming Error - Out of time call to " & pActiveScheduled & " was already scheduled but not executed")
            pActiveScheduled = ""
        Else
            pActiveScheduled = pWhenOutofTime
        End If
    Else
        pActiveScheduled = pScheduledUpdateProcess
    End If
    
    If pActiveScheduled <> "" Then
        pNextUpdate = Now + TimeSerial(0, 0, pUpdateInterval)
        pxlApp.Application.OnTime pNextUpdate, pActiveScheduled

    End If
    
End Sub

Public Function cMicroTimer() As Double
' Returns seconds.
    Dim cyTicks1 As Currency
    Static cyFrequency As Currency
    cMicroTimer = 0
' Get frequency.
    If cyFrequency = 0 Then getFrequency cyFrequency
' Get ticks.
    getTickCount cyTicks1
' Seconds
    If cyFrequency Then cMicroTimer = cyTicks1 / cyFrequency
End Function
