-- update all rows where unit smr = component smr and 'Reman' status is null > has to be a new component > Reman=False

-- SELECT *

-- FROM
UPDATE a

SET
    a.Reman=0

FROM
    EventLog a

WHERE
    a.Reman IS NULL and
    a.ComponentCO = 1 and
    a.SMR = a.ComponentSMR