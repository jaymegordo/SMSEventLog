UPDATE a 
INNER JOIN tbl b ON 
    a.Unit=b.Unit And 
    a.StartDate=b.StartDate
SET a.SMS=b.SMS