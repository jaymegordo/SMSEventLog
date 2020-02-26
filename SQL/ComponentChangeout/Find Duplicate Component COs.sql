select Unit, DateAdded, Floc, count(*)
  from EventLog
  Where Floc Is Not Null And Unit Is Not Null
  group by Unit, DateAdded, Floc
  having count(*) > 1