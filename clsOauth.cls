VERSION 1.0 CLASS
BEGIN
  MultiUse = -1  'True
END
Attribute VB_Name = "clsOauth"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = False
Attribute VB_PredeclaredId = False
Attribute VB_Exposed = False
'================================================================================== '
'
' OAuth 2.0 Google Authenticator
' Developed by Kyle Beachill
' licence: MIT (http://www.opensource.org/licenses/mit-license.php)
'
' Inspired loosely by Tim Halls authentication classes in his Excel-Rest library:
' https://github.com/timhall/Excel-REST
'
'
' Features:
'     Simple class to handle Google OAuth 2.0 Authentication
'     Follows the Installed Application Flow
'     Returns Simply the value for the Authorization header in API requests
'
' Gotchas:
'     Tokens are held in plain text in the registry
'
' Required References:
'   - Microsoft Internet Controls
'   - Microsoft XML
'
' ================================================================================== '


Option Explicit

'// Simple enum for current authentication status
Private Enum AuthenticationStatus
    NotAuthenticated = 1
    TokenExpired = 2
    Authenticated = 3
End Enum


'// Application Client ID and Application Secret
Private strClientId As String
Private strClientSecret As String

'// Authentication codes, tokens and expiry date
Private strTokenKey As String
Private strToken As String
Private strRefreshToken As String
Private dtExpiresWhen As Date
Private strAuthCode As String

'// Url End points for the authentication
Private strAuthUrl As String
Private strTokenUrl As String
Private strRedirectUri As String

'// Internet Explorer variables for initial authentication request
Private WithEvents oIExplorer As InternetExplorer
Attribute oIExplorer.VB_VarHelpID = -1
Private blnIeComplete As Boolean

Private strResponseText As String
Private oResponse As Object

'// Save the request object to prevent being created for each token expiry
Private objXMLRequest As MSXML2.ServerXMLHTTP



'// Since we are persisting the credentials to the registry, we need to read these in each time the class
'// is initialized, if they aren't found - these will be default values, "" for strings and 1900/01/01 for te date
Private Sub class_initialize()
    
    Dim sDate As String
    
    strToken = GetSetting("GoogleAuth", "Tokens", "Token")
    strRefreshToken = GetSetting("GoogleAuth", "Tokens", "RefreshKey")
    sDate = GetSetting("GoogleAuth", "Tokens", "TokenExpiry")
    
    Debug.Print "strToken", strToken
    Debug.Print "strRefreshToken", strRefreshToken
    Debug.Print "sDate", sDate
    
    If Len(sDate) > 0 Then
         dtExpiresWhen = CDate(sDate)
    Else
         dtExpiresWhen = #1/1/1900#
    End If
    
End Sub

'// Allows the overriding of the default google EndPoints - these are unlikely to change
Public Sub InitEndPoints( _
    Optional ByVal AuthUrl As String = "https://accounts.google.com/o/oauth2/auth", _
    Optional ByVal TokenUrl As String = "https://accounts.google.com/o/oauth2/token", _
    Optional ByVal RedirectUri As String = "urn:ietf:wg:oauth:2.0:oob" _
)
    
    strAuthUrl = AuthUrl
    strTokenUrl = TokenUrl
    strRedirectUri = RedirectUri
    
End Sub

'// Application ID and Secret will always need passing, since they are required for refresh calls
'// Though these *could* be persisted in the registry also
Public Sub InitClientCredentials(ByVal ClientId As String, ByVal ClientSecret As String)

    strClientId = ClientId
    strClientSecret = ClientSecret

End Sub

'// Simple function to return the authentication status of the currently held credentials
Private Function getAuthenticationStatus() As AuthenticationStatus

    '// If the Refresh Token Length is 0 then the initial authentication hasn't occurred
    If Len(strRefreshToken) = 0 Then
        getAuthenticationStatus = NotAuthenticated
        Exit Function
    End If
    
    '// If the refresh date is less than now (with a 10 second buffer) then the token has expired
    If dtExpiresWhen < DateAdd("s", 10, Now()) Then
        getAuthenticationStatus = TokenExpired
        Exit Function
    End If
    
    '// Otherwise the token is valid
    getAuthenticationStatus = Authenticated
End Function
Private Sub GetNewToken()
    
    Set oIExplorer = New InternetExplorer
    
    With oIExplorer
        .navigate CreateAuthRequest()
        .AddressBar = False
        .MenuBar = False
        .resizable = False
        .visible = True
    End With
    
    '// Wait for userInteraction
    Do: DoEvents: Loop Until blnIeComplete
    
    '// Do we have an Authentication Code?
    If Len(strAuthCode) = 0 Then
        Err.Raise vbObjectError + 2, _
            Description:="User cancelled Authentication"
    End If
    
    '// Now Get a new Token
    If objXMLRequest Is Nothing Then Set objXMLRequest = New MSXML2.ServerXMLHTTP
    
    With objXMLRequest
        .Open "POST", strTokenUrl, False
        .setRequestHeader "Content-Type", "application/x-www-form-urlencoded"
        .send CreateTokenRequest()

        If .Status <> 200 Then
            '// Error getting OAuth2 token
            Err.Raise vbObjectError + .Status, _
                Description:="Failed to retrieve OAuth2 Token - " & .Status & ": " & .responseText
        End If
        
        '// Get the credentials from the response
        strToken = GetProp("access_token", .responseText)
        strRefreshToken = GetProp("refresh_token")
        dtExpiresWhen = DateAdd("s", CLng(GetProp("expires_in")), Now())
    
    End With
    
    '// Persist the Refresh key and expiry - the above should only ever need running once per application
    SaveSetting "GoogleAuth", "Tokens", "RefreshKey", strRefreshToken
    SaveSetting "GoogleAuth", "Tokens", "Token", strToken
    SaveSetting "GoogleAuth", "Tokens", "TokenExpiry", CStr(dtExpiresWhen)

End Sub

Private Sub RefreshToken()

    If objXMLRequest Is Nothing Then Set objXMLRequest = New MSXML2.ServerXMLHTTP
    
    With objXMLRequest
        .Open "POST", strTokenUrl, False
        .setRequestHeader "Content-Type", "application/x-www-form-urlencoded"
        .send CreateRefreshRequest()
        If .Status <> 200 Then
            '// Error getting OAuth2 token
            Err.Raise vbObjectError + .Status, _
                Description:="Failed to retrieve OAuth2 Token - " & .Status & ": " & .responseText
        End If
        
        '// Get the credentials from the response
        strToken = GetProp("access_token", .responseText)
        dtExpiresWhen = DateAdd("s", CLng(GetProp("expires_in")), Now())
    End With
    
    '// Persist new token in registry
    SaveSetting "GoogleAuth", "Tokens", "Token", strToken
    SaveSetting "GoogleAuth", "Tokens", "TokenExpiry", CStr(dtExpiresWhen)
        
        
End Sub
'// Simple function that gets a propery from a single depth JSON formatted string
'// Requires the property name
'// Requires te JSON string on the first pass
Private Function GetProp(strPropName As String, Optional strJSObject As String = "") As String
    
    Static oScriptControl As Object
    
    If oScriptControl Is Nothing Then Set oScriptControl = CreateObject("ScriptControl")
    
    With oScriptControl
        .language = "JScript"
        .AddCode "function getProp(json, prop) { return json[prop]; }"
        
        If Len(strJSObject) > 0 Then
            strResponseText = strJSObject
            Set oResponse = .Eval("(" & strJSObject & ")")
        End If
        GetProp = .Run("getProp", oResponse, strPropName)
    End With

End Function
'// Public property to return the Authorisation value header for a request
Public Property Get AuthHeader() As String
    
    Dim eAuthStatus As AuthenticationStatus
    
    eAuthStatus = getAuthenticationStatus
    
    If eAuthStatus = NotAuthenticated Then
        GetNewToken
    ElseIf eAuthStatus = TokenExpired Then
        RefreshToken
    End If
    
    AuthHeader = "Bearer " & strToken
    
    
End Property

'//===========================================================================================================
'// String building functions for the requests

'// Step 1: The initial url for authentication - Note the scope attribute, this sets what the application can access
Private Function CreateAuthRequest() As String
    ' Generate initial Authentication Request
    ' Using installed application flow: https://developers.google.com/accounts/docs/OAuth2InstalledApp
    CreateAuthRequest = strAuthUrl
    If InStr(1, CreateAuthRequest, "?") < 1 Then: CreateAuthRequest = CreateAuthRequest & "?"
    CreateAuthRequest = CreateAuthRequest & "response_type=code"
    CreateAuthRequest = CreateAuthRequest & "&client_id=" & strClientId
    CreateAuthRequest = CreateAuthRequest & "&redirect_uri=" & strRedirectUri
    CreateAuthRequest = CreateAuthRequest & "&scope=https%3A%2F%2Fwww.googleapis.com%2Fauth%2Fanalytics.readonly"
End Function

'// Step 2: The initial POST body to get the initial Token and refresh token
Private Function CreateTokenRequest() As String

    CreateTokenRequest = "code=" & strAuthCode
    CreateTokenRequest = CreateTokenRequest & "&client_id=" & strClientId
    CreateTokenRequest = CreateTokenRequest & "&client_secret=" & strClientSecret
    CreateTokenRequest = CreateTokenRequest & "&redirect_uri=" & strRedirectUri
    CreateTokenRequest = CreateTokenRequest & "&grant_type=authorization_code"

End Function

'// Step 3: The POST body to refresh a token after it has expired
Private Function CreateRefreshRequest() As String

    CreateRefreshRequest = "client_id=" & strClientId
    CreateRefreshRequest = CreateRefreshRequest & "&client_secret=" & strClientSecret
    CreateRefreshRequest = CreateRefreshRequest & "&refresh_token=" & strRefreshToken
    CreateRefreshRequest = CreateRefreshRequest & "&grant_type=refresh_token"
    
End Function

'//===========================================================================================================
'// Event handling for Internet Explorer Object
'// OAuth 2.0 Process flow requires a user to provide access through the browser for initial Authentication

'//Break Loop on user Quit of IE
Private Sub oIExplorer_OnQuit()
    blnIeComplete = True
End Sub

'//Check the title Window, if Success or Denied Found End the IE interaction
Private Sub oIExplorer_TitleChange(ByVal Text As String)

    If InStr(1, Text, "Success") > 0 Then
        'strAuthCode = oIExplorer.Document.getElementById("code").Value
        strAuthCode = "4/rAARJbmNxU5HRO-XAPS1kOaqPhRhaF9cHii6_Mmgd1jPOoYl8MN4_70"
        oIExplorer.Quit
    ElseIf InStr(1, Text, "Denied") > 0 Then
        oIExplorer.Quit
    End If

End Sub

