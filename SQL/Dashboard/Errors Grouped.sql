select ErrNum, ErrDescrip, Sub, count(ErrNum) c From Errors
Group By ErrNum, ErrDescrip, sub
Order By c DESC