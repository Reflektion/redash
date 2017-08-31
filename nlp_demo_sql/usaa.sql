
DROP DATABASE IF EXISTS usaa;
CREATE DATABASE IF NOT EXISTS usaa;
USE usaa;

SELECT 'CREATING DATABASE STRUCTURE' as 'INFO';

DROP TABLE IF EXISTS families,
                     finance_products,
                     transactions;

/*!50503 set default_storage_engine = InnoDB */;
/*!50503 select CONCAT('storage engine: ', @@default_storage_engine) as INFO */;

CREATE TABLE families (
    family_id   INT             NOT NULL,
    first_name  VARCHAR(16)     NOT NULL,
    last_name   VARCHAR(16)     NOT NULL,
    address     VARCHAR(100)    NOT NULL,
    city        VARCHAR(32)     NOT NULL,
    state       VARCHAR(32)     NOT NULL,
    zip         CHAR(5)         NOT NULL,
    dob         DATE            NOT NULL,
    PRIMARY KEY (family_id)
);

CREATE TABLE finance_products (
    prod_id     INT             NOT NULL,
    prod_name   VARCHAR(40)     NOT NULL,
    PRIMARY KEY (prod_id),
    UNIQUE  KEY (prod_name)
);

CREATE TABLE transactions (
   family_id    INT              NOT NULL,
   prod_id      INT              NOT NULL,
   act_date     DATE             NOT NULL,
   activity     ENUM('viewed','inquired','purchased','renewed','reactivated')   NOT NULL,
   marketing    ENUM('texting','email','search','social')   NOT NULL,
   FOREIGN KEY (family_id)  REFERENCES families (family_id)    ON DELETE CASCADE,
   FOREIGN KEY (prod_id) REFERENCES finance_products (prod_id) ON DELETE CASCADE,
   PRIMARY KEY (family_id,prod_id)
); 

CREATE TABLE lat_long (
    state       VARCHAR(32)     NOT NULL,
    lat         FLOAT           NOT NULL,
    longitude   FLOAT           NOT NULL,
    #FOREIGN KEY (state) REFERENCES families (state)  ON DELETE CASCADE,
    PRIMARY KEY (state)
);

flush /*!50503 binary */ logs;
SELECT 'LOADING families' as 'INFO';
source load_families.dump ;
SELECT 'LOADING finance_products' as 'INFO';
source load_finance_products.dump ;
SELECT 'LOADING transactions' as 'INFO';
source load_transactions.dump ;
SELECT 'LOADING lat_long' as 'INFO';
source load_lat_long.dump
