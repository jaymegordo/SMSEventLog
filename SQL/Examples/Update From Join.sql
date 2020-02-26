Update a
Set a.UID=b.UID
From Sun_CO_Records a Left Join [Sun_CO_Records-Backup] b on a.ID=b.ID
Where b.UID Is not Null