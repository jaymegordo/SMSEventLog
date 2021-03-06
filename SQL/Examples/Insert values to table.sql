-- Drop table  #temp;

CREATE TABLE #temp (Unit VARCHAR(9) NOT NULL, AHSStart DATE NOT NULL);
INSERT INTO #temp (Unit, AHSStart)
VALUES

('F301',	'2020-05-15'),
('F302',	'2020-04-27'),
('F303',	'2019-11-22'),
('F304',	'2020-06-03'),
('F305',	'2020-05-04'),
('F307',	'2019-12-05'),
('F308',	'2019-12-05'),
('F309',	'2020-04-28'),
('F310',	'2019-11-12'),
('F311',	'2020-07-15'),
('F312',	'2020-04-10'),
('F313',	'2020-04-10'),
('F314',	'2020-04-09'),
('F315',	'2020-04-18'),
('F316',	'2020-04-17'),
('F317',	'2020-07-05'),
('F318',	'2020-07-02'),
('F319',	'2020-06-20'),
('F320',	'2020-06-21'),
('F321',	'2020-07-10'),
('F331',	'2019-04-05'),
('F332',	'2019-04-06'),
('F333',	'2019-04-09'),
('F334',	'2019-06-17'),
('F335',	'2019-05-06'),
('F336',	'2019-07-10'),
('F337',	'2019-05-13'),
('F338',	'2020-04-17'),
('F339',	'2020-04-14'),
('F342',	'2019-11-12'),
('F343',	'2019-11-28'),
('F344',	'2020-07-15'),
('F346',	'2020-07-18'),
('F347',	'2020-05-26');

Update a
Set a.AHSStart=b.AHSStart
From UnitID a Left Join #temp b on a.Unit=b.Unit
Where
    a.MineSite='FortHIlls' and
    a.Model like '980%';

Drop table #temp;