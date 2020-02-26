select Sub, count(*) as ErrCount
from Errors
Where ErrTime > DATEADD(Month, -3, getdate())
group by Sub
order by count(*) desc