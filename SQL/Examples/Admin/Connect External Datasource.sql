
-- *create login creds and external table definition once

-- CREATE MASTER KEY ENCRYPTION BY PASSWORD = 'Z%^7wdpf%Nai=^ZFy-U.';

-- CREATE DATABASE SCOPED CREDENTIAL SqlUser
-- WITH IDENTITY = 'jgordon',
-- SECRET = 'Z%^7wdpf%Nai=^ZFy-U.';

-- CREATE EXTERNAL DATA SOURCE RemoteReferenceData
-- WITH (
--     TYPE=RDBMS,
--     LOCATION='jgazure1.database.windows.net',
--     DATABASE_NAME='db1_2020-04-29T18-04Z',
--     CREDENTIAL= SqlUser);

-- CREATE EXTERNAL TABLE [dbo].[FCSummaryMineSite2] (
--     FCNumber NVARCHAR(255) not null,
--     MineSite NVARCHAR(255) not null,
--     Comments VARCHAR(8000))
-- WITH (
--     DATA_SOURCE = [RemoteReferenceData],
--     SCHEMA_NAME = 'dbo',
--     OBJECT_NAME = 'FCSummaryMineSite'
--     );

UPDATE a
Set a.Comments=b.Comments

From FCSummaryMineSite a INNER JOIN  FCSummaryMineSite2 b on a.FCNumber=b.FCNumber and a.MineSite=b.MineSite

WHERE a.MineSite='FortHills'


