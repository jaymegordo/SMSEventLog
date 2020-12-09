# coding: utf-8
from sqlalchemy import (BigInteger, Column, DECIMAL, Date, DateTime, Float, ForeignKey, Index, Integer, SmallInteger, String, Table, Time, Unicode, text)
from sqlalchemy.dialects.mssql import (BIT, DATETIME2, MONEY, SMALLDATETIME, TIMESTAMP)
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()
metadata = Base.metadata


t_Comp_Latest_CO = Table(
    'Comp Latest CO', metadata,
    Column('Unit', Unicode(255)),
    Column('Floc', Unicode(255)),
    Column('MaxUnitSMR', Integer),
    Column('MaxDateAdded', DATETIME2)
)


t_Component_CO_to_check_SMR = Table(
    'Component CO to check SMR', metadata,
    Column('Unit', Unicode(255)),
    Column('Title', Unicode(255)),
    Column('DateAdded', DATETIME2),
    Column('Floc', Unicode(255)),
    Column('SMR', Integer),
    Column('ComponentSMR', Integer)
)


class ComponentLookAhead(Base):
    __tablename__ = 'ComponentLookAhead'

    Week = Column(Integer, nullable=False, index=True)
    Status = Column(Unicode(255))
    StartDate = Column(DATETIME2)
    SuncorWO = Column(Integer, primary_key=True)
    SMSWO = Column(Unicode(255))
    MainWC = Column(Unicode(255))
    Description = Column(Unicode(255))
    FLOC = Column(Unicode(255))
    DueDate = Column(DATETIME2)
    WOType = Column(Unicode(255))
    DueWeek = Column(Integer)
    Category = Column(Unicode(255))
    Old = Column(BIT, server_default=text("((0))"))
    SSMA_TimeStamp = Column(TIMESTAMP, nullable=False)


class ComponentType(Base):
    __tablename__ = 'ComponentType'
    __table_args__ = (
        Index('ComponentType$ComponentModifier', 'Component', 'Modifier'),
    )

    Component = Column(Unicode(255), index=True)
    Modifier = Column(Unicode(255))
    Floc = Column(Unicode(255), primary_key=True, nullable=False)
    Model = Column(Unicode(255))
    BenchSMR = Column(Integer, server_default=text("((0))"))
    PartNo = Column(Unicode(255))
    Major = Column(BIT, server_default=text("((0))"))
    EquipClass = Column(String(50, 'SQL_Latin1_General_CP1_CI_AS'), primary_key=True, nullable=False)


class Downtime(Base):
    __tablename__ = 'Downtime'

    Unit = Column(Unicode(255), primary_key=True, nullable=False)
    StartDate = Column(DATETIME2, primary_key=True, nullable=False)
    EndDate = Column(DATETIME2, primary_key=True, nullable=False)
    CategoryAssigned = Column(Unicode(255))
    DownReason = Column(Unicode(255))
    Comment = Column(String(8000, 'SQL_Latin1_General_CP1_CI_AS'))
    Duration = Column(DECIMAL(10, 2))
    Responsible = Column(Unicode(255))
    SMS = Column(DECIMAL(10, 2))
    Suncor = Column(DECIMAL(10, 2))
    ShiftDate = Column(Date)
    Origin = Column(String(50, 'SQL_Latin1_General_CP1_CI_AS'))


t_DowntimeExport = Table(
    'DowntimeExport', metadata,
    Column('Unit', SmallInteger),
    Column('Start Date', DATETIME2),
    Column('End Date', DATETIME2),
    Column('Category Assigned', Unicode(255)),
    Column('Down Reason', Unicode(255)),
    Column('Comment', Unicode(255)),
    Column('Duration', Float(53)),
    Column('SMS', Float(53)),
    Column('Suncor', Float(53)),
    Column('Responsible', Unicode(255)),
    Column('Shift Date', Date)
)


t_DowntimeImport = Table(
    'DowntimeImport', metadata,
    Column('Unit', Unicode(255), nullable=False),
    Column('StartDate', DATETIME2, nullable=False),
    Column('EndDate', DATETIME2),
    Column('CategoryAssigned', Unicode(255)),
    Column('DownReason', Unicode(255)),
    Column('Comment', String(collation='SQL_Latin1_General_CP1_CI_AS')),
    Column('Duration', DECIMAL(10, 2)),
    Column('Responsible', Unicode(255)),
    Column('SMS', DECIMAL(10, 2)),
    Column('Suncor', DECIMAL(10, 2)),
    Column('ShiftDate', Date),
    Column('Origin', String(50, 'SQL_Latin1_General_CP1_CI_AS'))
)


class EmailList(Base):
    __tablename__ = 'EmailList'

    Email = Column(Unicode(255), primary_key=True, nullable=False)
    MineSite = Column(Unicode(255), primary_key=True, nullable=False)
    UserGroup = Column(Unicode(50), primary_key=True, nullable=False)
    Passover = Column(Unicode(255))
    WORequest = Column(Unicode(255))
    FCCancelled = Column(Unicode(255))
    PicsDLS = Column(Unicode(255))
    PRP = Column(Unicode(255))
    FCSummary = Column(Unicode(255))
    TSI = Column(Unicode(255))
    RAMP = Column(Unicode(255))
    Service = Column(Unicode(255))
    Parts = Column(Unicode(255))
    AvailDaily = Column(Unicode(255))
    AvailReports = Column(Unicode(255))


class EquipType(Base):
    __tablename__ = 'EquipType'

    Model = Column(String(255, 'SQL_Latin1_General_CP1_CI_AS'), primary_key=True)
    EquipClass = Column(String(255, 'SQL_Latin1_General_CP1_CI_AS'))
    ModelBase = Column(String(50, 'SQL_Latin1_General_CP1_CI_AS'))
    TargetPayload = Column(Float(53))


t_Errors = Table(
    'Errors', metadata,
    Column('UserName', String(255, 'SQL_Latin1_General_CP1_CI_AS')),
    Column('ErrTime', DATETIME2),
    Column('ErrNum', Integer),
    Column('ErrDescrip', String(collation='SQL_Latin1_General_CP1_CI_AS')),
    Column('Sub', String(collation='SQL_Latin1_General_CP1_CI_AS')),
    Column('Version', Float(53)),
    Column('WorkSheet', Integer)
)


class EventLog(Base):
    __tablename__ = 'EventLog'
    __table_args__ = (
        Index('EventLog$SuncorWOFloc', 'SuncorWO', 'Floc'),
        Index('EventLog$MineSite-StatusEvent', 'MineSite', 'PassoverSort', 'StatusEvent'),
        Index('EventLog$MineSite-StatusWO', 'MineSite', 'WarrantyYN', 'StatusWO')
    )

    UID = Column(Float(53), primary_key=True, server_default=text("((0))"), autoincrement=False)
    MineSite = Column(Unicode(255))
    PassoverSort = Column(Unicode(255))
    StatusEvent = Column(Unicode(255))
    StatusWO = Column(Unicode(255))
    CreatedBy = Column(Unicode(255))
    ClosedBy = Column(Unicode(255))
    Unit = Column(Unicode(255), index=True)
    Title = Column(Unicode(255))
    Description = Column(String(8000, 'SQL_Latin1_General_CP1_CI_AS'))
    Required = Column(String(8000, 'SQL_Latin1_General_CP1_CI_AS'))
    FailureCause = Column(String(8000, 'SQL_Latin1_General_CP1_CI_AS'))
    SMR = Column(Integer)
    DateAdded = Column(Date)
    DateCompleted = Column(Date)
    TimeCalled = Column(Date)
    IssueCategory = Column(Unicode(255))
    SubCategory = Column(Unicode(255))
    Cause = Column(Unicode(255))
    WarrantyYN = Column(Unicode(255))
    WorkOrder = Column(Unicode(255), index=True)
    Seg = Column(Unicode(255))
    PartNumber = Column(Unicode(255))
    SuncorWO = Column(Unicode(255))
    SuncorPO = Column(Unicode(255))
    Downloads = Column(BIT, server_default=text("((0))"))
    Pictures = Column(SmallInteger, server_default=text("((0))"))
    CCOS = Column(Unicode(255))
    WOComments = Column(String(8000, 'SQL_Latin1_General_CP1_CI_AS'))
    StatusTSI = Column(Unicode(255), index=True)
    DateInfo = Column(Date)
    DateTSISubmission = Column(Date)
    TSINumber = Column(Unicode(255))
    TSIPartName = Column(Unicode(255))
    TSIDetails = Column(String(8000, 'SQL_Latin1_General_CP1_CI_AS'))
    TSIPartNo = Column(Unicode(255))
    TSIAuthor = Column(Unicode(255))
    FilePath = Column(String(8000, 'SQL_Latin1_General_CP1_CI_AS'))
    ComponentCO = Column(BIT, server_default=text("((0))"))
    Floc = Column(Unicode(255))
    GroupCO = Column(BIT, server_default=text("((0))"))
    ComponentSMR = Column(Integer)
    SNRemoved = Column(Unicode(255))
    SNInstalled = Column(Unicode(255))
    CapUSD = Column(MONEY)
    RemovalReason = Column(Unicode(255))
    COConfirmed = Column(BIT, server_default=text("((0))"))
    DateReturned = Column(Date)
    SunCOReason = Column(String(255, 'SQL_Latin1_General_CP1_CI_AS'))
    Reman = Column(BIT)


class FCSummary(Base):
    __tablename__ = 'FCSummary'

    FCNumber = Column(Unicode(255), primary_key=True)
    Subject = Column(Unicode(255))
    SubjectShort = Column(Unicode(255))
    Classification = Column(Unicode(255))
    NotCustomerFriendly = Column(BIT, server_default=text("((0))"))
    Hours = Column(Float(53))
    DowntimeEst = Column(Float(53), server_default=text("((0))"))
    PartNumber = Column(Unicode(255))
    CustomSort = Column(Integer)
    ReleaseDate = Column(Date)
    ExpiryDate = Column(Date)
    TempCol = Column(String(255, 'SQL_Latin1_General_CP1_CI_AS'))


class FCSummaryMineSite(Base):
    __tablename__ = 'FCSummaryMineSite'

    FCNumber = Column(Unicode(255), primary_key=True, nullable=False, index=True)
    MineSite = Column(Unicode(255), primary_key=True, nullable=False)
    Resp = Column(Unicode(255))
    Comments = Column(String(8000, 'SQL_Latin1_General_CP1_CI_AS'))
    ManualClosed = Column(BIT, server_default=text("((0))"))
    PartAvailability = Column(Unicode(255))


t_FactoryCampaignImport = Table(
    'FactoryCampaignImport', metadata,
    Column('FCNumber', String(collation='SQL_Latin1_General_CP1_CI_AS')),
    Column('Model', String(collation='SQL_Latin1_General_CP1_CI_AS')),
    Column('Serial', String(collation='SQL_Latin1_General_CP1_CI_AS')),
    Column('Unit', String(collation='SQL_Latin1_General_CP1_CI_AS')),
    Column('StartDate', Date),
    Column('EndDate', Date),
    Column('DateCompleteKA', Date),
    Column('Subject', String(collation='SQL_Latin1_General_CP1_CI_AS')),
    Column('Classification', String(collation='SQL_Latin1_General_CP1_CI_AS')),
    Column('Hours', String(collation='SQL_Latin1_General_CP1_CI_AS')),
    Column('Distributor', String(collation='SQL_Latin1_General_CP1_CI_AS')),
    Column('Branch', String(collation='SQL_Latin1_General_CP1_CI_AS')),
    Column('Safety', String(collation='SQL_Latin1_General_CP1_CI_AS')),
    Column('Status', String(collation='SQL_Latin1_General_CP1_CI_AS'))
)


class FaultCode(Base):
    __tablename__ = 'FaultCodes'

    Type = Column(Unicode(255))
    Description = Column(Unicode(255), primary_key=True, nullable=False)
    Code = Column(Unicode(255), primary_key=True, nullable=False)


t_FaultImport = Table(
    'FaultImport', metadata,
    Column('unit', String(collation='SQL_Latin1_General_CP1_CI_AS')),
    Column('code', String(collation='SQL_Latin1_General_CP1_CI_AS')),
    Column('time_from', DATETIME2),
    Column('time_to', DATETIME2),
    Column('faultcount', BigInteger),
    Column('message', String(collation='SQL_Latin1_General_CP1_CI_AS'))
)


class Fault(Base):
    __tablename__ = 'Faults'
    __table_args__ = (
        Index('IX_Code_Timefrom', 'Code', 'Time_From'),
    )

    Unit = Column(String(50, 'SQL_Latin1_General_CP1_CI_AS'), primary_key=True, nullable=False)
    Code = Column(String(50, 'SQL_Latin1_General_CP1_CI_AS'), primary_key=True, nullable=False)
    Time_From = Column(DATETIME2, primary_key=True, nullable=False, index=True)
    Time_To = Column(DATETIME2)
    FaultCount = Column(Integer)
    Message = Column(String(collation='SQL_Latin1_General_CP1_CI_AS'))


t_Find_duplicates_for_EventLog = Table(
    'Find duplicates for EventLog', metadata,
    Column('Unit', Unicode(255)),
    Column('DateAdded', DATETIME2),
    Column('Floc', Unicode(255)),
    Column('UID', Float(53), nullable=False),
    Column('MineSite', Unicode(255)),
    Column('Title', Unicode(255)),
    Column('DateCompleted', DATETIME2),
    Column('SuncorWO', Unicode(255)),
    Column('SuncorPO', Unicode(255)),
    Column('ComponentCO', BIT),
    Column('SNRemoved', Unicode(255)),
    Column('SNInstalled', Unicode(255)),
    Column('RemovalReason', Unicode(255))
)


t_MAGuarantee = Table(
    'MAGuarantee', metadata,
    Column('MaxAge', Integer),
    Column('MA', DECIMAL(4, 3)),
    Column('MAExisting', DECIMAL(4, 3))
)


class PLM(Base):
    __tablename__ = 'PLM'

    Unit = Column(String(50, 'SQL_Latin1_General_CP1_CI_AS'), primary_key=True, nullable=False)
    DateTime = Column(DATETIME2, primary_key=True, nullable=False)
    Payload = Column(Float(53), nullable=False)
    Swingloads = Column(BigInteger)
    StatusFlag = Column(String(50, 'SQL_Latin1_General_CP1_CI_AS'))
    Carryback = Column(Float(53))
    CycleTime = Column(Float(53))
    L_HaulDistance = Column(Float(53))
    L_MaxSpeed = Column(Float(53))
    E_MaxSpeed = Column(Float(53))
    MaxSprung = Column(Float(53))
    TruckType = Column(String(50, 'SQL_Latin1_General_CP1_CI_AS'))
    SprungWeight = Column(Float(53))
    Payload_Est = Column(Float(53))
    Payload_Quick = Column(Float(53))
    Payload_Gross = Column(Float(53))


t_PLMImport = Table(
    'PLMImport', metadata,
    Column('index', BigInteger, index=True),
    Column('unit', String(50, 'SQL_Latin1_General_CP1_CI_AS'), nullable=False, index=True),
    Column('datetime', DateTime),
    Column('payload', Float(53)),
    Column('swingloads', Float(53)),
    Column('statusflag', String(collation='SQL_Latin1_General_CP1_CI_AS')),
    Column('carryback', Float(53)),
    Column('cycletime', BigInteger),
    Column('l_hauldistance', Float(53)),
    Column('l_maxspeed', Float(53)),
    Column('e_maxspeed', Float(53)),
    Column('maxsprung', Float(53)),
    Column('trucktype', String(collation='SQL_Latin1_General_CP1_CI_AS')),
    Column('sprungweight', Float(53)),
    Column('payload_est', Float(53)),
    Column('payload_quick', Float(53)),
    Column('payload_gross', Float(53))
)


t_PSNList = Table(
    'PSNList', metadata,
    Column('Reference Number', Unicode(255)),
    Column('Comp Code', Unicode(255), index=True),
    Column('Subject', Unicode(255)),
    Column('Model(s)', Unicode(255)),
    Column('Product Line', Unicode(255)),
    Column('Issue Date', DATETIME2),
    Column('Customer friendly?', Unicode(255))
)


class Part(Base):
    __tablename__ = 'Parts'

    PartNo = Column(Unicode(255), primary_key=True, nullable=False, index=True)
    PartName = Column(Unicode(255), index=True)
    Model = Column(Unicode(255), primary_key=True, nullable=False, index=True)


class PicsDL(Base):
    __tablename__ = 'PicsDLS'

    Unit = Column(Unicode(255), index=True)
    FolderName = Column(Unicode(255), primary_key=True, nullable=False)
    Type = Column(Unicode(255), primary_key=True, nullable=False)
    DateAdded = Column(DATETIME2)
    SortDate = Column(DATETIME2)
    FaultLinesAdded = Column(Integer)
    PLMLinesAdded = Column(Integer)
    FilePath = Column(Unicode(255))


t_RemanImport = Table(
    'RemanImport', metadata,
    Column('ID', BigInteger),
    Column('RepDate', String(collation='SQL_Latin1_General_CP1_CI_AS')),
    Column('SMSWO', String(collation='SQL_Latin1_General_CP1_CI_AS')),
    Column('RecDate', String(collation='SQL_Latin1_General_CP1_CI_AS')),
    Column('Branch', String(collation='SQL_Latin1_General_CP1_CI_AS')),
    Column('BranchWO', String(collation='SQL_Latin1_General_CP1_CI_AS')),
    Column('Customer', String(collation='SQL_Latin1_General_CP1_CI_AS')),
    Column('CustPO', String(collation='SQL_Latin1_General_CP1_CI_AS')),
    Column('UnitNum', String(collation='SQL_Latin1_General_CP1_CI_AS')),
    Column('Make', String(collation='SQL_Latin1_General_CP1_CI_AS')),
    Column('Model', String(collation='SQL_Latin1_General_CP1_CI_AS')),
    Column('MachineSer', String(collation='SQL_Latin1_General_CP1_CI_AS')),
    Column('Component', String(collation='SQL_Latin1_General_CP1_CI_AS')),
    Column('CompMod', String(collation='SQL_Latin1_General_CP1_CI_AS')),
    Column('CompSerial', String(collation='SQL_Latin1_General_CP1_CI_AS')),
    Column('CompLoc', String(collation='SQL_Latin1_General_CP1_CI_AS')),
    Column('InstallDate', String(collation='SQL_Latin1_General_CP1_CI_AS')),
    Column('RemoveDate', String(collation='SQL_Latin1_General_CP1_CI_AS')),
    Column('Commisioned', String(collation='SQL_Latin1_General_CP1_CI_AS')),
    Column('CompHrs', String(collation='SQL_Latin1_General_CP1_CI_AS'))
)


t_SunBench = Table(
    'SunBench', metadata,
    Column('ID', Integer, nullable=False),
    Column('Unit', Unicode(255)),
    Column('MineSite', Unicode(255)),
    Column('Component', Unicode(255)),
    Column('Modifier', Unicode(255)),
    Column('WorkOrder', Unicode(255)),
    Column('SuncorWO', Unicode(255)),
    Column('SMR', Integer),
    Column('ComponentSMR', Integer),
    Column('Part_Num', Unicode(255)),
    Column('SNRemoved', Unicode(255)),
    Column('DateAdded', Date),
    Column('CO_Mode', Unicode(255)),
    Column('Reason', Unicode(255)),
    Column('PO', Unicode(20)),
    Column('Notes', Unicode(255)),
    Column('Convert_Indicator', Integer),
    Column('CapUSD', MONEY),
    Column('PercentBench', Float(53)),
    Column('Warranty', Unicode(255)),
    Column('SUN_CO_Reason', Unicode(255)),
    Column('Group_CO', BIT),
    Column('TSI', Unicode(25)),
    Column('Warranty_Hours', Integer),
    Column('UID', Float(53)),
    Column('Transaction_Hour', Integer),
    Column('Floc', Unicode(255))
)


class TSIValue(Base):
    __tablename__ = 'TSIValues'

    Element = Column(Unicode(255), primary_key=True)
    Type = Column(Unicode(255))
    Active = Column(Unicode(255))
    DefaultVal = Column(Unicode(255))


class TechLogAction(Base):
    __tablename__ = 'TechLogActions'

    UID = Column(Float(53), primary_key=True)
    UIDParent = Column(Float(53), nullable=False)
    Issue_Title = Column(Unicode(50))
    Action = Column(Unicode)
    Added_By = Column(Unicode(50), nullable=False)
    Responsible = Column(Unicode(50))
    Date_Added = Column(Date)
    Date_Complete = Column(Date)
    Status = Column(Unicode(50))


class TechLogSummary(Base):
    __tablename__ = 'TechLogSummary'

    UID = Column(Float(53), primary_key=True)
    Status = Column(Unicode(50))
    Title = Column(Unicode(1000))
    Risk_Rank = Column(Unicode(50))
    Model = Column(Unicode(50))
    Owner = Column(Unicode(50))
    Description = Column(Unicode(1000))
    Date_Added = Column(Date)
    Date_Complete = Column(Date)
    Resolution = Column(Unicode(1000))
    Receptor = Column(Unicode(50))
    EquipType = Column(String(255, 'SQL_Latin1_General_CP1_CI_AS'))


class TechLogUser(Base):
    __tablename__ = 'TechLogUsers'

    UserName = Column(Unicode(50), primary_key=True)
    Email = Column(Unicode(50))
    Company = Column(Unicode(50))


class UnitID(Base):
    __tablename__ = 'UnitID'
    __table_args__ = (
        Index('UnitID$ModelSerial', 'Model', 'Serial'),
    )

    MineSite = Column(Unicode(255), index=True)
    Model = Column(Unicode(50), nullable=False)
    Serial = Column(Unicode(50), nullable=False, index=True)
    EngineSerial = Column(Unicode(50))
    Unit = Column(Unicode(255), primary_key=True)
    DeliveryDate = Column(Date)
    VerPLM = Column(SmallInteger)
    SubSite = Column(String(255, 'SQL_Latin1_General_CP1_CI_AS'))
    Active = Column(BIT)
    ExcludeMA = Column(BIT)
    OffContract = Column(BIT)
    DateOffContract = Column(Date)
    AHSActive2 = Column(BIT, server_default=text("((0))"))
    AHSActive = Column(BIT, server_default=text("((0))"))
    Customer = Column(String(50, 'SQL_Latin1_General_CP1_CI_AS'))


class UnitSMR(Base):
    __tablename__ = 'UnitSMR'

    Unit = Column(Unicode(255), primary_key=True, nullable=False, index=True)
    DateSMR = Column(Date, primary_key=True, nullable=False)
    SMR = Column(Integer)


t_UnitSMRImport = Table(
    'UnitSMRImport', metadata,
    Column('Unit', Unicode(255), nullable=False, index=True),
    Column('DateSMR', Date, nullable=False),
    Column('SMR', Integer)
)


class UserSettings(Base):
    __tablename__ = 'UserSettings'

    UserName = Column(Unicode(255), primary_key=True)
    Version = Column(Float(53), server_default=text("((0))"))
    Ver = Column(String(10, 'SQL_Latin1_General_CP1_CI_AS'))
    LastLogin = Column(DATETIME2)
    Hours = Column(DECIMAL(10, 3))
    NumOpens = Column(Integer, index=True, server_default=text("((0))"))
    FilePath = Column(Unicode(255))
    Email = Column(String(255, 'SQL_Latin1_General_CP1_CI_AS'))
    Domain = Column(String(255, 'SQL_Latin1_General_CP1_CI_AS'))
    UserGroup = Column(String(50, 'SQL_Latin1_General_CP1_CI_AS'))
    MineSite = Column(String(100, 'SQL_Latin1_General_CP1_CI_AS'))


class User(Base):
    __tablename__ = 'Users'

    UserName = Column(Unicode(255), primary_key=True)
    Title = Column(Unicode(255))
    Manager = Column(Unicode(255))


t_viewComponentCO = Table(
    'viewComponentCO', metadata,
    Column('MineSite', Unicode(255)),
    Column('Unit', Unicode(255)),
    Column('ModelBase', String(50, 'SQL_Latin1_General_CP1_CI_AS')),
    Column('Component', Unicode(255)),
    Column('DateAdded', SMALLDATETIME),
    Column('Reman', String(5, 'SQL_Latin1_General_CP1_CI_AS'), nullable=False),
    Column('SunCOReason', String(255, 'SQL_Latin1_General_CP1_CI_AS')),
    Column('ComponentSMR', Integer),
    Column('PercentBench', Float(53))
)


t_viewPLM = Table(
    'viewPLM', metadata,
    Column('Unit', String(50, 'SQL_Latin1_General_CP1_CI_AS'), nullable=False),
    Column('DateTime', DATETIME2, nullable=False),
    Column('Payload', Float(53), nullable=False),
    Column('StatusFlag', String(50, 'SQL_Latin1_General_CP1_CI_AS')),
    Column('L_HaulDistance', Float(53)),
    Column('GrossPayload_pct', Float(53)),
    Column('QuickPayload_pct', Float(53)),
    Column('QuickShovelEst_pct', Float(53)),
    Column('ExcludeFlags', Integer, nullable=False)
)


t_viewPredictedCO = Table(
    'viewPredictedCO', metadata,
    Column('MineSite', Unicode(255)),
    Column('Model', Unicode(50), nullable=False),
    Column('Unit', Unicode(255), nullable=False),
    Column('Component', Unicode(255)),
    Column('Modifier', Unicode(255)),
    Column('BenchSMR', Integer),
    Column('CurrentUnitSMR', Integer),
    Column('LastCO', Integer),
    Column('PredictedCODate', DateTime)
)


class FactoryCampaign(Base):
    __tablename__ = 'FactoryCampaign'

    UID = Column(ForeignKey('EventLog.UID'), index=True)
    Unit = Column(Unicode(255), primary_key=True, nullable=False)
    FCNumber = Column(Unicode(255), primary_key=True, nullable=False, index=True)
    Serial = Column(Unicode(255), index=True)
    Status = Column(Unicode(243))
    Classification = Column(Unicode(255))
    Subject = Column(Unicode(255))
    Model = Column(Unicode(255))
    Distributor = Column(Float(53))
    Branch = Column(Float(53))
    CompletionDate = Column(Date)
    DateCompleteSMS = Column(Date)
    DateCompleteKA = Column(Date)
    Safety = Column(Unicode(255))
    StartDate = Column(Date)
    EndDate = Column(Date)
    ClaimNumber = Column(Unicode(255))
    Technician = Column(Unicode(255))
    Hours = Column(Float(53))
    ServiceLetterDate = Column(Date)
    Notes = Column(Unicode(255))
    CustomSort = Column(Integer)
    Ignore = Column(BIT, server_default=text("((0))"))

    EventLog = relationship('EventLog')
