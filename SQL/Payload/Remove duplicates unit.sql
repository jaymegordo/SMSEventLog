-- delete duplicates within unit

with t as (
    select unit, datetime, payload, cycletime, ROW_NUMBER() OVER (Partition By unit, datetime, payload Order By unit, datetime, payload) as RN
    From temphaul
)
Delete From t where RN>1