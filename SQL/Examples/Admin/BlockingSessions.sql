SELECT

blocking_session_id AS BlockingSessionID,

session_id AS VictimSessionID,

(SELECT [text] FROM sys.sysprocesses

CROSS APPLY sys.dm_exec_sql_text([sql_handle])

WHERE spid = blocking_session_id) AS BlockingQuery,

[text] AS VictimQuery,

wait_time/1000 AS WaitDurationSecond,

wait_type AS WaitType,

percent_complete AS BlockingQueryCompletePercent

FROM sys.dm_exec_requests

CROSS APPLY sys.dm_exec_sql_text([sql_handle])

WHERE blocking_session_id > 0