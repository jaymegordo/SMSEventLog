Select Errors.*, Email From Errors Right Join UserSettings On UserSettings.UserName=Errors.UserName
Order By ErrTime Desc