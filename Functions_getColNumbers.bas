Attribute VB_Name = "Functions_getColNumbers"

Function Field(iws, sHdr As String) As String
    Dim f As String
    Select Case iws
        Case 1
            Select Case sHdr
                Case "Passover"
                    f = "PassoverSort"
                Case "Status"
                    f = "StatusEvent"
                Case "Date Added"
                    f = "DateAdded"
                Case "Date Complete"
                    f = "DateCompleted"
                Case "Issue Category"
                    f = "IssueCategory"
                Case "Sub Category"
                    f = "SubCategory"
                Case "Added By"
                    f = "CreatedBy"
                Case "Time Called to Event"
                    f = "TimeCalled"
            End Select
        
        Case 2
            Select Case sHdr
                Case "Status"
                    f = "StatusWO"
                Case "Wrnty"
                    f = "WarrantyYN"
                Case "Work Order"
                    f = "WorkOrder"
                Case "Customer WO"
                    f = "SuncorWO"
                Case "Customer PO"
                    f = "SuncorPO"
                Case "Part Number"
                    f = "PartNumber"
                Case "Date Opened"
                    f = "DateAdded"
                Case "Date Closed"
                    f = "DateCompleted"
                Case "Added By"
                    f = "CreatedBy"
                Case "Comments"
                    f = "WOComments"
                Case "Comp CO"
                    f = "ComponentCO"
            End Select
        
        Case 7 'FC Details
            Select Case sHdr
                Case "Date Complete SMS"
                    f = "DateCompleteSMS"
            End Select
        
        Case 8 'FC Summary
            Select Case sHdr
                Case "Action Reqd"
                    f = "Resp"
                Case "Part Number"
                    f = "PartNumber"
                Case "Parts Avail."
                    f = "PartAvailability"
                Case "Release Date"
                    f = "ReleaseDate"
                Case "Expiry Date"
                    f = "ExpiryDate"
            End Select
        
        Case 10 'TSI
            Select Case sHdr
                Case "Status"
                    f = "StatusTSI"
                Case "Failure Date"
                    f = "DateAdded"
                Case "Info/Repair Date"
                    f = "DateInfo"
                Case "Submission Date"
                    f = "DateTSISubmission"
                Case "TSI No."
                    f = "TSINumber"
                Case "WO"
                    f = "WorkOrder"
                Case "Unit SMR"
                    f = "SMR"
                Case "Part SMR"
                    f = "ComponentSMR"
                Case "Part Name"
                    f = "TSIPartName"
                Case "Part Number"
                    f = "PartNumber"
                Case "Serial No"
                    f = "SNRemoved"
                Case "Details"
                    f = "TSIDetails"
                Case "Author"
                    f = "TSIAuthor"
            End Select
        
        Case 15 'Component CO
            Select Case sHdr
                Case "Group CO"
                    f = "GroupCO"
                Case "CO Date"
                    f = "DateAdded"
                Case "Unit SMR"
                    f = "SMR"
                Case "Comp SMR"
                    f = "ComponentSMR"
                Case "SN Removed"
                    f = "SNRemoved"
                Case "SN Installed"
                    f = "SNInstalled"
                Case "Wtny"
                    f = "WarrantyYN"
                Case "SMS WO"
                    f = "WorkOrder"
                Case "Customer WO"
                    f = "SuncorWO"
                Case "Customer PO"
                    f = "SuncorPO"
                Case "Notes"
                    f = "RemovalReason"
            End Select
    End Select
    
    If f = "" Then
        Field = sHdr
        Else
        Field = f
    End If
    
End Function
Function getCol(iws, colType As String)
    'function accepts worksheet number and type of column.
    'Use this whenever the code references a certain column, as columns could move around in the future.
    
    Select Case colType
        Case "StatusWO"
            Select Case iws
                Case 2
                    getCol = 2
            End Select
            
        Case "Title"
            Select Case iws
                Case 1
                    getCol = 5
                Case 2
                    getCol = 10
                Case 10
                    getCol = 10
            End Select
            
        Case "Unit"
            Select Case iws
                Case 1
                    getCol = 4
                Case 2
                    getCol = 8
                Case 7
                    getCol = 1
                Case 10
                    getCol = 8
                Case 15
                    getCol = 1
            End Select
        
        Case "DateAdded"
            Select Case iws
                Case 1
                    getCol = 8
                Case 2
                    getCol = 13
                Case 10
                    getCol = 3
                Case 15
                    getCol = 5
            End Select
        
        Case "UnitSMR"
            Select Case iws
                Case 2
                    getCol = 12
                Case 10
                    getCol = 11
                Case 15
                    getCol = 6
            End Select
        
        Case "PartSMR"
            Select Case iws
                Case 10
                    getCol = 12
                Case 15
                    getCol = 7
            End Select
        
        Case "DateClosed"
            Select Case iws
                Case 1
                    getCol = 9
                Case 2
                    getCol = 14
            End Select
        
        Case "WorkOrder"
            Select Case iws
                Case 2
                    getCol = 4
                Case 10
                    getCol = 7
                Case 15
                    getCol = 12
            End Select
        
        Case "PartNo"
            Select Case iws
                Case 2
                    getCol = 11
                Case 10
                    getCol = 14
            End Select
        
        Case "ComponentCO"
            Select Case iws
                Case 2
                    getCol = 17
            End Select
        
        Case "Warranty"
            Select Case iws
                Case 2
                    getCol = 3
            End Select
        
        Case "FCNumber"
            Select Case iws
                Case 7
                    getCol = 2
                Case 8
                    getCol = 1
            End Select
        
    End Select
    
End Function





