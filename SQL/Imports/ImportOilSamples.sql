SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE PROCEDURE [dbo].[ImportOilSamples]
AS
Insert Into OilSamples 
Select b.*
From OilSamplesImport b Left Join OilSamples a
    On a.labTrackingNo=b.labTrackingNo
Where a.unitId Is Null;

TRUNCATE TABLE OilSamplesImport;

GO
