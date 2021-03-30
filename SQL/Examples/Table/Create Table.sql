drop table OilSamples;

Create Table OilSamples (
    hist_no BIGINT NOT NULL,
    sample_date DATE NULL,
    process_date DATE NULL,
    unit VARCHAR(50) NOT NULL,
    component_id VARCHAR(50) NULL,
    component_type VARCHAR(50) NULL,
    modifier VARCHAR(30) NULL,
    unit_smr INT NULL,
    component_smr INT NULL,
    sample_rank FLOAT NULL,
    oil_changed BIT NULL,
    test_results VARCHAR(2000),
    test_flags VARCHAR(1000),
    results VARCHAR(MAX),
    recommendations VARCHAR(MAX),
    comments VARCHAR(MAX)

    CONSTRAINT PK_hist_no PRIMARY KEY (hist_no)
)



-- unit 7
-- component_id 26
-- component_type 26
-- modifier 15
-- sample_date 10
-- process_date 10
-- unit_smr 8
-- component_smr 8
-- oil_changed 5
-- sample_rank 4
-- results 815
-- recommendations 1646
-- comments 68
-- test_results 702
-- test_flags 193