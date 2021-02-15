-- delete duplicates within unit
WITH
    t
    AS
    (
        SELECT
            a.unit,
            a.DATETIME,
            a.payload,
            cycletime,
            ROW_NUMBER() OVER (
			PARTITION BY a.unit,
			a.DATETIME,
			a.payload ORDER BY unit,
				a.DATETIME,
				payload
			) AS RN
        FROM
            temphaul a
    )
DELETE
FROM t
WHERE RN > 1
