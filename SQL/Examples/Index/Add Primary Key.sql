Alter Table OilSamplesImport
-- ADD CONSTRAINT pk_labTrackingNo PRIMARY KEY CLUSTERED (labTrackingNo); 
ALTER COLUMN labTrackingNo VARCHAR(100) NOT NULL;
GO

Alter Table OilSamplesImport
ADD PRIMARY KEY (labTrackingNo);