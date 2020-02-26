select TSIAuthor, count(TSIAuthor) c From EventLog
Group By TSIAuthor
Order By C Desc