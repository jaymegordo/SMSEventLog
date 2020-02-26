Create Table PLM (
    Unit varchar(50) Not Null,
    [DateTime] DateTime2(0) Not Null,
    Payload Float Not Null,
    Swingloads bigint,
    StatusFlag varchar(50),
    Carryback float,
    CycleTime float,
    L_HaulDistance float,
    L_MaxSpeed float,
    E_MaxSpeed float,
    MaxSprung float,
    TruckType varchar(50),
    SprungWeight float,
    Payload_Est float,
    Payload_Quick float,
    Payload_Gross float
    CONSTRAINT PK_Unit_DateTime PRIMARY KEY (Unit, [DateTime])
)