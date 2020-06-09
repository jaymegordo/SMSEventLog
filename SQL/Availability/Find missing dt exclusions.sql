select Date, COUNT(Hours) as Hrs
FROM DowntimeExclusions
Where
    Date BETWEEN '2020-05-01' and '2020-05-31' and
    Unit in 
        ('F319',
        'F320',
        'F321',
        'F322',
        'F323',
        'F324',
        'F325',
        'F326',
        'F327',
        'F328',
        'F329',
        'F330') 
    
GROUP BY Date