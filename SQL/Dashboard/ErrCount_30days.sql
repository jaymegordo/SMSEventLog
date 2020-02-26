select top 20 UserName, Count(*) as ErrCount
from Errors
Where ErrTime > DATEADD(Month, -3, getdate())
group by UserName
order by count(*) desc