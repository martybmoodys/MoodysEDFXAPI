import io
import os
import requests
import warnings
import urllib.parse
import time
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import moodys_keys as mk
import requests
import json
import asyncio
import aiohttp
from enum import Enum
from datetime import datetime
from loguru import logger
from EDFXPrime import EDFXEndpoints, OutputFormat, FinancialTemplate
from urllib.parse import urljoin,urlencode,quote_plus
from aiohttp import ClientTimeout,ClientSession, ClientError, ServerTimeoutError
from EDFXAuthentication import EDFXClient
from traceback import format_exc
import nest_asyncio
import loan_scorecard
nest_asyncio.apply()


# =============================================================================================================
# ATTENTION: Before you continue UNDERSTAND:
# Moodys Analytics DOES NOT support this code. This code is for assistance and demonstration purposes only.
# Licensed Clients should reference https://hub.moodysanalytics.com/products
# and the functional endpoint examples when formatting their exact questions to support.
# ==============================================================================================================


logger.add(sink='LGDloggingfile.log', level='DEBUG')

class LGD(EDFXEndpoints):

    """
    Loss Given Default Functionality and interoperatibility between legacy RiskCalc and EDFX Software

    Class inheritance of EDFXEnpoints via EDFXPrime thus allowing users to leverage methods of
    the endpoints class.

    Key Characteristics of this class:

        Case1: API Broken yet we need to yield a Legacy RiskCalc.csv Input File
               This implies that only the df, can be passed for case1 situations.

        Case2: API WORKS and we would like to create a Legacy RiskCalc.csv with the appropriate annualized term structure.
        Case3: We will abstract all use of Legacy RiskCalc and use EDFX API exclusively.

    ATTN USER: UPON INSTANTIATION YOU CANNOT INSTANTIATE BOTH A DF AND Entities OBJECTS. YOU MUST FEED ONLY ONE OR THE OTHER!!!!
    -----------------------------------------------------------------------------------------------------------------------------------------------------
    General Params Required in all Cases:

        api_publickey: Your public key

        api_privatekey: Your private key

        df: is the EDFX.csv turned into a pandas dataframe fed to this class.

        entities: Entity vector.  Please use the 'format_PDpayload' method in EDFXPrime.py to create an entities object
                  This can be fed at instantiation.  You can observe this within the LGD NoteBook.

        IndustryClassification:  as of 11/15/2023 options are 'NDY' or 'NAICS2017' are supported only for the df Input and if you were
                            to instantiate the class with entities then NDY, NACE, NAICS, and SIC are available.

        Case:  Acceptable case numbers are 1, 2, or 3.  This specifies the route of processing.

        BatchingSearchBatch: The size constraint of how you can pull the information.  I made the size constraint derivative of the EDFX APIs
                rate limits when Asyncio and AioHTTP libraries are used. This seemed most relevant for speed. Do not increase over 100.

        AsyncBatch: LGD and PD payloads have batch sizes limits for asyncio and aiohttp functionality.  With full term structures
                    The limit is two payloads.
    -------------------------------------------------------------------------------------------------------------------------------------------------------
    CASE 1 & CASE2 Specific Params:

         Given the Unique Nature of the Class and due to the Fact that this class primarily is designed to support the EDFX-API (Case 3)
         Use case long term, I elect to have Loan Specific Parameters specified within this LGD's RiskCalcLoanSpecification Method. See
         this Method for specifics and the repos JupyterNotebook example for clarity.

    --------------------------------------------------------------------------------------------------------------------------------------------------------
    LGDCASE3Parameters:

            | Field                           | Required | Description                                                                 | Example        |
            |---------------------------------|----------|-----------------------------------------------------------------------------|----------------|,

            |   loanId                        | Yes      | Loan Identifier.                                                            | Loan123        |
            |   loanName                      |          | Loan label or name.                                                         | Charle's Loan  |
            |   asOfDate                      | Yes      | This is the date used to calculate the  MACRO  environment for LGD values.  | "2021-01-01"   |
            |                                 |          | Format: YYYY-MM-DD.                                                         |                |
            |   Country                       | Yes      | Three digit ISO Code                                                        | "USA"          |
            |   instrumentType                | Yes      | The debt type and seniority class of the instrument.                        | “Term Loan”    |
            |   securedUnsecured              | Yes      | Indicates whether the instrument is secured or unsecured.                   | “Secured”      |
            |                                 |          | Only applicable for certain instruments.                                    |                |
            |   capitalStructure              | Yes      | Specifies the borrower's capital structure at the time of default.          | “Unknown”      |
            |   recoveryCalculationMode       | Yes      | Indicates which recovery model to use for the calculation.                  | “Ultimate Recovery” |
            |
            |   exposure                      | Yes      | Amount of exposure at the time of asOfDate.                                 | 1000000        |
            |   originationDate               |          | Date the loan was originated. Format: YYYY-MM-DD.                           | "2022-12-31"   |
            |   maturityDate                  |          | Date the loan matures. Format: YYYY-MM-DD.                                  | "2025-06-30"   |
            |   exposureCurrency              |          | The currency denomination of the exposure amount.                           | "USD"          |

        How would a temporal case look like when I need a Time Series?

            Example of Temporal 1:

                If the Loan is using TODAYS Macro Scenario with a loan starting 3 years ago from January 2024 you can pull the last three years LGD term 
                strucure payloads vis filling in the relevant loan paramaters, in particular, the following start, end, and history frequency dates
                will be necessary for this use case.
                Case3LGDPDStartDate = "2021-01-01", Case3LGDPDEndDate = "2024-01-01",  Case3LGDhistoryFrequency = "Annual"


            Example Temporal 2:

                If the Loan is using a Macro Scenario 3 years ago for a loan starting 3 years ago from January 1 2024, (meaning you want to see the credit 
                cycle applied 3 years ago ==> Jan 1 2021) you can pull the LGD content via
                filling in these relevant loan paramaters along wiht the rest of the loan specific informaiton. 

                EX: Say you just need one term structure, 3 years ago today.
                case3LGDOriginationDate = '2021-01-01' #date loan originated
                Case3LGDPDStartDate = "2021-01-01", Case3LGDPDEndDate = "2022-01-01", # here we take a term structure over the year 3 years ago.
                Case3LGDhistoryFrequency = "Annual", Case3LGDasOfDate = "2021-01-01" # asofDate is the date we apply the macro scenario over the analysis.


    """
    def __init__(self,df:pd.DataFrame = None,entities:list[dict[str,str]]=None, case:int=2,Case3LGDInstrumentType:str='Senior Bond',
                    IndustryClassification:str="NDY",BatchingSearchBatch:int=100,Case3LGDasOfDate:str = pd.Timestamp.now(),
                    Case3LGDSecuredUnsecured:str='Unsecured',Case3LGDExposure:int= 100000, Case3LGDExposureCurrency:str="USD",
                    Case3LGDCountry:str="USA",Case3LGDMaturityDate:str="2028-01-01",AsyncBatch:int = 2, api_publickey:str=None,
                    Case3LGDRecoveryCalculationMode:str="Ultimate Recovery",Case3LGDCapitalStructure:str="Unknown", TTCPD:bool=False,
                    Case3LGDPDStartDate:str=None, Case3LGDPDEndDate:str=pd.Timestamp.now().strftime('%Y-%m-%d'),case3LGDOriginationDate:str=None,
                    Case3LGDhistoryFrequency:str='annual',api_privatekey:str=None, *args, **kwargs):
        super().__init__(api_publickey=api_publickey, api_privatekey=api_privatekey, *args, **kwargs)

        self.df = df.copy() if df is not None else None
        self.entities = entities
        # we can't have both inputs. Users need to choose one or the other.
        if (self.df is None and self.entities is None) or (self.df is not None and self.entities is not None):
                    raise ValueError('You must include either an entities list OR a Pandas DataFrame, but not both and at least one.')

        if self.df is not None:
            # If a DataFrame is provided, only 'NDY' or 'NAICS2017' are valid
            if IndustryClassification not in ['NDY', 'NAICS2017']:
                raise ValueError("For DataFrame input, IndustryClassification must be either 'NDY' or 'NAICS2017' as of this code update.")
        if self.entities is not None:
            if IndustryClassification not in ['NDY', 'NACE', 'NAICS', 'SIC']:
                raise ValueError("For entities input 'NDY', 'NACE', 'NAICS', 'SIC' are the only parameters Mapping endpoint supports. If you get NA VALUES try NDY.")

        self.IndustryClassification = IndustryClassification
        self.case = case
        self.BatchingSearchBatch = BatchingSearchBatch
        self.AsyncBatch = AsyncBatch
        self.TTCPD = TTCPD

        assert self.case in (1, 2, 3), "Please put integer value 1,2, or 3."
        # specify where Case1 and Case 2 users input their loan information
        if self.case != 3:
            logger.info("ATTENTION: To provide your Loan Specific Inputs you MUST USE RiskCalcLoanSpecification method to output the values in the RiskCalc.csv file. ")
        if self.case == 3:
            # Case 3 Paramaters
            self.Case3LGDasOfDate = Case3LGDasOfDate
            self.Case3LGDExposure = Case3LGDExposure
            self.Case3LGDExposureCurrency = Case3LGDExposureCurrency
            self.Case3LGDCountry = Case3LGDCountry
            self.Case3LGDMaturityDate = Case3LGDMaturityDate
            self.Case3LGDSecuredUnsecured = Case3LGDSecuredUnsecured
            self.Case3LGDInstrumentType = Case3LGDInstrumentType
            self.Case3LGDRecoveryCalculationMode = Case3LGDRecoveryCalculationMode
            self.Case3LGDCapitalStructure = Case3LGDCapitalStructure
            self.Case3LGDPDStartDate = Case3LGDPDStartDate
            self.Case3LGDPDEndDate = Case3LGDPDEndDate
            self.Case3LGDhistoryFrequency = Case3LGDhistoryFrequency
            self.case3LGDOriginationDate = case3LGDOriginationDate


    def NDY_Mapper(self, industrySeries:pd.Series) -> pd.Series:


        """This takes any Pandas series with appropriaty NDY Industry Names and maps them to the appropriate NDY Mappings. """

        NDY_IndustryMapping = {
                            'NDY': ['N01', 'N02', 'N03', 'N04', 'N05', 'N06', 'N07', 'N08', 'N09', 'N10',
                                    'N11', 'N12', 'N13', 'N14', 'N15', 'N16', 'N17', 'N18', 'N19', 'N20',
                                    'N21', 'N22', 'N23', 'N24', 'N25', 'N26', 'N27', 'N28', 'N29', 'N30',
                                    'N31', 'N32', 'N33', 'N34', 'N35', 'N36', 'N37', 'N38', 'N39', 'N40',
                                    'N41', 'N42', 'N43', 'N44', 'N45', 'N46', 'N47', 'N48', 'N49', 'N50',
                                    'N51', 'N52', 'N53', 'N54', 'N55', 'N56', 'N57', 'N58', 'N59', 'N60',
                                    'N61', 'N62'],

                            'NDY Description': ['AEROSPACE & DEFENSE', 'AGRICULTURE', 'AIR TRANSPORTATION', 'APPAREL & SHOES', 'AUTOMOTIVE',
                                                'BANKS AND S&LS', 'BROADCAST MEDIA', 'BUSINESS PRODUCTS WHSL', 'BUSINESS SERVICES', 'CHEMICALS',
                                                'COMPUTER HARDWARE', 'COMPUTER SOFTWARE', 'CONSTRUCTION', 'CONSTRUCTION MATERIALS', 'CONSUMER DURABLES',
                                                'CONSUMER DURABLES RETL/WHSL', 'CONSUMER PRODUCTS', 'CONSUMER PRODUCTS RETL/WHSL', 'CONSUMER SERVICES', 'ELECTRICAL EQUIPMENT',
                                                'ELECTRONIC EQUIPMENT', 'ENTERTAINMENT & LEISURE', 'FINANCE COMPANIES', 'FINANCE NEC', 'FOOD & BEVERAGE',
                                                'FOOD & BEVERAGE RETL/WHSL', 'FURNITURE & APPLIANCES', 'HOTELS & RESTAURANTS', 'INSURANCE - LIFE', 'INSURANCE - PROP/CAS/HEALTH',
                                                'INVESTMENT MANAGEMENT', 'LESSORS', 'LUMBER & FORESTRY', 'MACHINERY & EQUIPMENT', 'MEASURE & TEST EQUIPMENT',
                                                'MEDICAL EQUIPMENT', 'MEDICAL SERVICES', 'MINING', 'OIL REFINING', 'OIL, GAS & COAL EXPL/PROD',
                                                'PAPER', 'PHARMACEUTICALS', 'PLASTIC & RUBBER', 'PRINTING', 'PUBLISHING',
                                                'REAL ESTATE', 'REAL ESTATE INVESTMENT TRUSTS', 'SECURITY BROKERS & DEALERS', 'SEMICONDUCTORS',
                                                'STEEL & METAL PRODUCTS', 'TELEPHONE', 'TEXTILES', 'TOBACCO', 'TRANSPORTATION EQUIPMENT',
                                                'TRANSPORTATION', 'TRUCKING', 'UNASSIGNED', 'UTILITIES NEC', 'UTILITIES, ELECTRIC',
                                                'UTILITIES, GAS', 'CABLE TV', 'IT SERVICES']
                        }

        NDY_df = pd.DataFrame(NDY_IndustryMapping)
        ndymap = NDY_df.set_index('NDY Description').to_dict()['NDY']
        industrySeries = industrySeries.map(ndymap)
        return industrySeries

    def NAICS2017_Mapper(self, industrySeries: pd.Series) -> pd.Series:

        """
        This function takes a Pandas series with appropriate NAICS 2017 Industry Descriptions
        and maps them to the corresponding NAICS 2017 sector codes.
        """

        NAICS2017_IndustryMapping = {
            'NAICS2017': ['11', '21', '22', '23', '31-33', '42', '44-45', '48-49', '51', '52', '53',
                            '54', '55', '56', '61', '62', '71', '72', '81', '92'],

            'NAICS2017 Description': ['Agriculture, Forestry, Fishing and Hunting',
                                        'Mining, Quarrying, and Oil and Gas Extraction',
                                        'Utilities',
                                        'Construction',
                                        'Manufacturing',
                                        'Wholesale Trade',
                                        'Retail Trade',
                                        'Transportation and Warehousing',
                                        'Information',
                                        'Finance and Insurance',
                                        'Real Estate and Rental and Leasing',
                                        'Professional, Scientific, and Technical Services',
                                        'Management of Companies and Enterprises',
                                        'Administrative and Support and Waste Management and Remediation Services',
                                        'Educational Services',
                                        'Health Care and Social Assistance',
                                        'Arts, Entertainment, and Recreation',
                                        'Accommodation and Food Services',
                                        'Other Services (except Public Administration)',
                                        'Public Administration']
        }

        NAICS2017_df = pd.DataFrame(NAICS2017_IndustryMapping)
        naics_map = NAICS2017_df.set_index('NAICS2017 Description').to_dict()['NAICS2017']
        industrySeries = industrySeries.map(naics_map)
        return industrySeries

    def NACE2_Mapper(self, industrySeries:pd.Series) ->pd.Series:

        """
        NACE2 European Industry Classification Standards.
            WIll Ask Chris on this

        """
        print("We are sorry but NACE2 Mapping is not completed as a function.  Please email chris.roldan@moodys.com for help.")
        return None

    def map_description_vectorized(self, series:pd.Series):

        """
        Vectorized mapping of descriptions to 'Private' or 'Public'

        Parameters:
        - series (pd.Series): thie is applied to EDFX.CSV output column 'Confidence Description'

        """
        # set conditions: When you're using the result of str.contains() as a condition for np.select, it's crucial to have a boolean
        # array where all entries are either True or False. If NaN values are present, np.select won't work as expected,
        # because NaN is not a valid condition. By setting na=False, you ensure that all values in the array are boolean,
        # and NaN values will not interfere with the selection process.
        conditions = [series.str.contains('Private firm', na=False), series.str.contains('Public firm', na=False)]
        choices = ['Private', 'Public']
        vectorized = np.select(conditions, choices, default='EDFX does not have relevant data for this entity. Please contact support.')
        return vectorized

    def LGDCase3PDParse(self, CleanedDF:pd.DataFrame, pd_df:pd.DataFrame):


        """
        Helper Function to Clean and blend the information of the PD Term Structure.
        Cleaning witll be derivative of either case 2 or case 3. This function is for case 3.

        Information is coming from the EDFX PD's endpoint, and the loan dataframe generated from the LGDDFLoan Specific method.
        """
        pdcolumns = ['entityId'] + ['asOfDate'] + [col for col in pd_df.columns if col.startswith('cumulative_cumulative') and 1 <= int(col.split('cumulative_cumulative')[1][:-1]) <= 10]

        # Lets just the Grab the Information we need from the Pds's endpoint and then lets format it and throw it into the LGDTarget Df
        # pdcolumns = ['entityId'] +  [col for col in pd_df.columns if col.startswith('cumulative_cumulative') and 1 <= int(col[-2]) <= 11]
        pdtermdf = pd_df[pdcolumns].reset_index(drop=True)
        column_mapping = {
                'entityId': 'Reference ID',
                'asOfDate': 'originationDate',
                'cumulative_cumulative1y': 'cumulativePd1y',
                'cumulative_cumulative2y': 'cumulativePd2y',
                'cumulative_cumulative3y': 'cumulativePd3y',
                'cumulative_cumulative4y': 'cumulativePd4y',
                'cumulative_cumulative5y': 'cumulativePd5y',
                'cumulative_cumulative6y': 'cumulativePd6y',
                'cumulative_cumulative7y': 'cumulativePd7y',
                'cumulative_cumulative8y': 'cumulativePd8y',
                'cumulative_cumulative9y': 'cumulativePd9y',
                'cumulative_cumulative10y': 'cumulativePd10y'
                }
        pdtermdf_renamed = pdtermdf.rename(columns=column_mapping)
        pdtermdf_renamed = pdtermdf_renamed.set_index('Reference ID')

        # Clean of RiskCalc.csv Columns
        NonEDFXcolumns = ['User PD 1', 'User PD 2', 'User PD 3', 'User PD 4', 'User PD 5', 'PID', 'Assets', 'Liabilities']
        # this won't parse uncessarily
        try:
            CleanedDF = CleanedDF.drop(columns=NonEDFXcolumns)
        except:
            pass
        # The next four lines takes a merge with columns with the same col name and extracts the columns with nan and replaces those with the columns with the values
        merged_df = CleanedDF.merge(pdtermdf_renamed, left_index=True, right_index=True, how='left', suffixes=("", '_y'))
        cols_to_replace = [col for col in pdtermdf_renamed.columns if col + '_y' in merged_df.columns]
        merged_df[cols_to_replace] = merged_df[[col + '_y' for col in cols_to_replace]]

        columns_to_drop = [col + '_y' for col in cols_to_replace]
        if 'asOfDate' in merged_df:
            columns_to_drop.append('asOfDate')
        merged_df.drop(columns=columns_to_drop, inplace=True)

        return merged_df[merged_df.index.isin(pdtermdf_renamed.index)]

    def LGDCase2PDParse(self, CleanedDF:pd.DataFrame, pd_df:pd.DataFrame):

        """
        Helper Function to Clean and blend the information of the PD Term Structure.
        Cleaning witll be derivative of either case 2 or case 3. This function is for case 3.

        Information is coming from the EDFX PD's endpoint, and the loan dataframe generated from the LGDDFLoan Specific method.
        """
        pd_df = pd_df.reset_index(drop = True)
        pdcolumns = ['entityId'] + ['asOfDate'] + [col for col in pd_df.columns if col.startswith('annualized') and 1 <= int(col.split('d')[-1].replace('y', '')) <= 5]
        pdtermdf = pd_df[pdcolumns]

        column_mapping = {
            'entityId': 'Reference ID',
            'asOfDate': 'InputMonthYear',
            'annualized_annualized1y': 'User PD 1',
            'annualized_annualized2y': 'User PD 2',
            'annualized_annualized3y': 'User PD 3',
            'annualized_annualized4y': 'User PD 4',
            'annualized_annualized5y': 'User PD 5'
        }
        pdtermdf_renamed = pdtermdf.rename(columns=column_mapping)
        pdtermdf_renamed['InputMonthYear'] = pd.to_datetime(pdtermdf_renamed['InputMonthYear'])
        pdtermdf_renamed['Input Date Month'] = pdtermdf_renamed['InputMonthYear'].dt.month
        pdtermdf_renamed['Input Date Year'] = pdtermdf_renamed['InputMonthYear'].dt.year
        del pdtermdf_renamed['InputMonthYear']
        pdtermdf_renamed = pdtermdf_renamed.set_index('Reference ID')

        # The next four lines takes a merge with columns with the same name and extracts the columss with nan and replaces those with the columns with the values
        merged_df = CleanedDF.merge(pdtermdf_renamed, left_index=True, right_index=True, how='left', suffixes=("", '_y'))
        cols_to_replace = [col for col in pdtermdf_renamed.columns if col + '_y' in merged_df.columns]
        merged_df[cols_to_replace] = merged_df[[col + '_y' for col in cols_to_replace]]
        merged_df.drop(columns=[col + '_y' for col in cols_to_replace], inplace=True)

        merged_df['User PD 1'] = pd.to_numeric(merged_df['User PD 1'], errors='coerce')
        merged_df['User PD 2'] = pd.to_numeric(merged_df['User PD 2'], errors='coerce')
        merged_df['User PD 3'] = pd.to_numeric(merged_df['User PD 3'], errors='coerce')
        merged_df['User PD 4'] = pd.to_numeric(merged_df['User PD 4'], errors='coerce')
        merged_df['User PD 5'] = pd.to_numeric(merged_df['User PD 5'], errors='coerce')

        # These values MUST be in percentage for the .csv upload
        merged_df['User PD 1'] =   np.round(merged_df['User PD 1']*100,4)
        merged_df['User PD 2'] =   np.round(merged_df['User PD 2']*100,4)
        merged_df['User PD 3'] =   np.round(merged_df['User PD 3']*100,4)
        merged_df['User PD 4'] =   np.round(merged_df['User PD 4']*100,4)
        merged_df['User PD 5'] =   np.round(merged_df['User PD 5']*100,4)

        # this implicitly handles mismatches of the two indices
        return merged_df[merged_df.index.isin(pdtermdf_renamed.index)]

    def PDTermStructureCheck(self, df: pd.DataFrame):
        """This will help us know which Identifiers are
           not returning payloads for."""
        case = self.case

        # DataFrame to store BVD IDs with NaN values
        nan_reference_ids = pd.DataFrame()

        if case == 1:
            pd_columns = ['User PD 1']
        elif case == 2:
            pd_columns = ['User PD 2', 'User PD 3', 'User PD 4', 'User PD 5']
        elif case == 3:
            pd_columns = ['cumulativePd1y', 'cumulativePd2y', 'cumulativePd3y', 'cumulativePd4y', 'cumulativePd5y', 'cumulativePd6y', 'cumulativePd7y', 'cumulativePd8y', 'cumulativePd9y', 'cumulativePd10y']

        df = df.reset_index()
        nan_rows = df[pd_columns].isna().any(axis=1)

        if nan_rows.any():
            nan_indices = df[nan_rows].index.tolist()
            # Store BVD IDs with NaN values
            nan_reference_ids = df.loc[nan_indices, ['Reference ID']]
             # Rename column for the nans dataframe
            nan_reference_ids = nan_reference_ids.rename(columns={'Reference ID': 'BVDIDs Erroring'})

            for index in nan_indices:
                reference_id = df.at[index, 'Reference ID']
                logger.error(f"Alert: NaN value found at index {index} with Reference ID {reference_id}. Removing this row.")
            df = df.drop(nan_indices).reset_index(drop=True)
            # drop columns index counter as it's uncessary
            df = df.loc[:, df.columns != '']
        else:
            logger.info("No NaN values found in the specified columns.")

        dictionaryclean = {'cleaned_df': df, 'BVDIDErrors': nan_reference_ids}

        return dictionaryclean

    def EDFXCSVClean(self):

        """
        Funtional Code to clean .csv output from EDFX Software portfolio .csv Output

        Construction of unconditional LGD's take Three Cases of 'Processes' to output an unconditional LGD:

            Case1: API Broken and we have user information within EDFX so we will reconstruct the Legacy RiskCalc.csv file (NO EDFX API)
                    This implies that only the df, can be passed for case1 situations.

            Case2: EDFX API WORKS and we may or may not have the client portfolio in EDFX but we at least have their entities we need RiskCalc.csv
            Case3: We will abstract all use of Legacy RiskCalc and use EDFX API exclusively.



        FUNCTIONAL CODE ONLY: Moving Cases to constructor class in LGD
                            The industry code classification. Options: NDY, NACE, NAICS, NAICS2017, SIC ==>Constructor

        """
        BatchSize = self.BatchingSearchBatch
        case = self.case
        IndustryClassification = self.IndustryClassification
        # IF case1 == True I must have a dataframe
        if case == 1:
            if self.df is not None and isinstance(self.df, pd.DataFrame) and not self.df.empty:
                df = self.df.copy()
                #Pre-process EDFdf Industry Column to the appropriate NDY Code
                if IndustryClassification == 'NDY':
                    df['Industry'] = self.NDY_Mapper(df['Industry'])

                elif IndustryClassification == 'NAICS2017':
                    df['Industry'] = self.NAICS2017_Mapper(df['Industry'])

                else:
                    print("NACE2 Mapping is not complete yet. Please re-read the docstring for how to pass this method. ")

                # Pre-process EDFXdf Confidence Description column to hit LGD.CSV output requirements
                df['Confidence Description'] = self.map_description_vectorized(df['Confidence Description'])

                # Define mapping
                EDFXMapper = {
                    "Entity Id": "Reference ID",
                    "Company Name": "Company Name",
                    "Country": "Location Code",
                    "Industry": "Industry Code",
                    "Confidence Description": "Private/Public",
                    "1 YRC CCA PD": "User PD 1"
                }
                EDFXdfrenamed = df.rename(columns=EDFXMapper)
                pd.to_numeric(EDFXdfrenamed['User PD 1'], errors='coerce')
                # must be in % terms
                EDFXdfrenamed['User PD 1'] = np.round(EDFXdfrenamed['User PD 1'] * 100,4)
                            # Select only the renamed columns
                EDFXValues_selected = EDFXdfrenamed[list(EDFXMapper.values())]

                if EDFXValues_selected['Industry Code'].isna().all():

                    print("You Ran this function more than once and need to re-readIn the EDFX.csv Portfolio output from EDFX Gui")
                    return None

                else:
                    # we need to figure something out for case one in accessing this dictionary
                    EDFXValues_selected = self.PDTermStructureCheck(EDFXValues_selected)
                    return EDFXValues_selected
            else:
                if self.entities:
                    print("You must use the Dataframe from the .csv portfolio download from the EDFX Software.  Entities payload is not meant for case 1.")

        # Cases Not 2 and 3 where they have the EDFX.Csv download in pandas and want the EDFX API termstructure (less compute)
        elif case != 1 and self.df is not None and isinstance(self.df, pd.DataFrame) and not self.df.empty:

            df = self.df.copy()
            #Pre-process EDFdf Industry Column to the appropriate NDY Code
            if IndustryClassification == 'NDY':
                df['Industry'] = self.NDY_Mapper(df['Industry'])

            elif IndustryClassification == 'NAICS2017':
                df['Industry'] = self.NAICS2017_Mapper(df['Industry'])

            else:
                print("NACE2 and SIC Mapping is not complete yet. you will have to use NDY or NAICS if you do not want to provide entities")

            # Pre-process EDFXdf Confidence Description column to hit LGD.CSV output requirements
            df['Confidence Description'] = self.map_description_vectorized(df['Confidence Description'])

            EDFXMapper = {
                "Entity Id": "Reference ID",
                "Company Name": "Company Name",
                "Country": "Location Code",
                "Industry": "Industry Code",
                "Confidence Description": "Private/Public",
            }
            # Rename EDFXdf columns
            EDFXdfrenamed = df.rename(columns=EDFXMapper)
            EDFXValues_selected = EDFXdfrenamed[list(EDFXMapper.values())]

            if EDFXValues_selected['Industry Code'].isna().all():

                print("You Ran this function more than once and need to re-readIn the EDFX.csv Portfolio output from EDFX Gui")
                return None

            else:
                return EDFXValues_selected
        else:
            # Payload Error Handling
            if self.entities:

                entities = self.entities
                if isinstance(entities, dict):
                    for key, value in entities.items():
                        if not isinstance(key,str) or not isinstance(value,str):
                            print("Error: you need to either feed a dictionary of 'EntityID' as key and an EDFX Qualified ID as the value." )
                            return None
                    entities = [entities]

                # Check if entities is a list of dictionaries with the key "entityId"
                if not isinstance(entities, list) or not all(isinstance(e, dict) and "entityId" in e for e in entities):
                    print("Error: entities parameter must be a list of dictionaries values.")
                    return None

                industry_column_mapping = {
                    'NDY': "primaryIndustryNDY",
                    'NACE': "primaryIndustryNACE",
                    'NAICS': "primaryIndustryNAICS",
                    'SIC': "primaryIndustrySIC"
                }
                indcol = industry_column_mapping.get(IndustryClassification)
                if not indcol:
                    print(f"Error: Invalid IndustryClassification '{IndustryClassification}'. Expected values are {list(industry_column_mapping.keys())}.")
                    return None
                columns = ['entityId', 'isPublic' , 'internationalName', 'contactCountryCode', indcol]

                batchdf = None
                if len(entities) > BatchSize:
                    logger.info('Co-routines to be employed at mapping endpoint')
                    # fix this when this is complete.
                    batchdf = asyncio.run(self.BatchingBatchSearch_async(EntityPayload=entities, BatchSize=BatchSize))
                else:
                    batchdictionary = self.EDFXBatchEntitySearch(queries=entities)
                    batchdf = self.EDFXBatchParse(batchdictionary)

                if batchdf is not None:

                    EDFXDFSearchEndpoint = batchdf[columns]
                    EDFXDFSearchEndpoint["Private/Public"] = EDFXDFSearchEndpoint['isPublic'].apply(lambda x: 'Public' if x else 'Private')
                    del EDFXDFSearchEndpoint['isPublic']

                    EDFXMapper = {
                        "entityId": "Reference ID",
                        "internationalName": "Company Name",
                        "contactCountryCode": "Location Code",
                        indcol : "Industry Code",
                    }
                    # Rename EDFXdf columns
                    EDFXDFSearchEndpoint = EDFXDFSearchEndpoint.rename(columns=EDFXMapper)

                    if EDFXDFSearchEndpoint['Industry Code'].isna().all():
                        print("recheck your inputs.")
                        return None

                    return EDFXDFSearchEndpoint
                else:
                    logger.error(f"Something happened {batchdf}.")

    def RiskCalcLoanSpecification(self, RiskDeterminantType:str='PD',DebtSeniority:str='SeniorSecuredBond',CapitalStructure:str='MostSeniorDebt',
                          RecoveryForecastType:str = 'UltimateRecovery', LocationType:str = 'ISO',Case1InputDateMonth = pd.Timestamp.now().month,
                          Case1InputDateYear:int = pd.Timestamp.now().year,Assets:float=None,Liabilities:float=None, PID:str = None,
                          Bankruptcy:str = None, Bailout:str = None)->pd.DataFrame:
        """
            This Function Takes in many of the the LGD inputfile paramaters. We specify them below.

            Params
                df: This is the Dataframe fed from EDFXClean function.

            If you have loan parameters, here is where you can input the loan data
            Understand it would be wise for you to build a sort with similar bonds to batch them all together.

            IMPORTANT: Within RiskCalcLoanSpecification method DO NOT ENTER InputDateYear or InputDateMonth here for
            case 2 and case 3. THESE ARE SPECIFICED WITHIN the PD Term Structure that is called.  These set
            the inputdatemonth and inputdateyear within Case 2 and they set the OriginationDate of the loan within
            case 3 for the EDFXLGD Payload that is called.

            PARAMS:

                CapitalStructure:
                    Options: Unknown, MostSeniorDebt, HasDebtAbove

                RecoveryForecastType:
                    Options: UltimateRecovery, PostDefaultPrice

                RiskDeterminantType: Defines the risk input of the obligor. Options: PD, Leverage, Company.

                IndustryClassification: This needs to be abstracted away into the first function within the clas.

                Industry Code:  We fed these in the EDFX Output file and we assume NDY Mappings.

                DebtSeniority: The debt type and seniority class of the instrument.

                    Options Debt Seniority: SubordinateBond, JuniorSubordinateBond, SeniorSubordinateBond, SeniorSecuredBond, EquipmentTrust
                                            SeniorUnsecuredBond, IndustrialRevenueBond,SecuredTermLoan, UnsecuredTermLoan

                PID: The Moody’s Analytics Permanent Identifier (PID). If you use a PID, leave the Industry and Country fields empty.
                    Options: Any valid PID. For Example, N06966

                Bankruptcy:  An indicator that specifies whether a bankruptcy is expected: Options: 'Yes', 'No', 'Unknown'

                Bailout: An indicator that specifies whether a bailout is expected. Options: 'Yes', 'No', 'Unknown'

            FOR LEGACY RISKCalc.csv file, you can start your Loan dates through InputDateMonth and InputDateYear

        """

        case = self.case
        IndustryClassification = self.IndustryClassification

        if case == 1:
            # here i call the df, but what could i do if they wanted the bvdids that didnt catch?

            case1dictionary = self.EDFXCSVClean()
            df = case1dictionary['cleaned_df']
            bvdidsError = case1dictionary['BVDIDErrors']

            df['Input Date Month'] = Case1InputDateMonth
            df['Input Date Year'] = Case1InputDateYear
            df['Risk Determinant Type'] = RiskDeterminantType
            df['PID'] = PID
            df['Debt / Seniority'] = DebtSeniority
            df['Capital Structure'] = CapitalStructure
            df['Bankruptcy'] = Bankruptcy
            df['Bailout'] = Bailout
            df['Recovery Forecast Type'] = RecoveryForecastType
            df['Location Type'] = LocationType
            df['Assets'] = Assets
            df['Liabilities'] = Liabilities
            #this needs to go away in this function and put in the next function
            df['Industry Classification'] = IndustryClassification

            # Legacy RiskCalc Specifics.  For columns we merge to later we can force empty columns as nan values
            LGDColumns = ['Reference ID', 'Company Name', 'Private/Public',
                        'Risk Determinant Type', 'PID', 'User PD 1', 'User PD 2', 'User PD 3',
                        'User PD 4', 'User PD 5', 'Assets', 'Liabilities', 'Input Date Month',
                        'Input Date Year', 'Location Type', 'Location Code',
                        'Industry Classification', 'Industry Code', 'Debt / Seniority',
                        'Capital Structure', 'Bankruptcy', 'Bailout', 'Recovery Forecast Type']

            # Create the Target Dataframe that's empty so We can concatonate it to it row wise
            LGDTarget = pd.DataFrame(columns=LGDColumns)
            # Set indexes for merging. We alwasy merge on same index.  Since this is an empty dictionary we must concatonate.
            # preserve the index as we will merge for later data mapping.
            LGDTarget = LGDTarget.set_index('Reference ID')
            EDFXValues = df.set_index('Reference ID')
            #Concatenate the dataframe rowwise since it's empty in LGD TARGET now.
            LGDTarget = pd.concat([LGDTarget, EDFXValues])
            return {'cleaned_df': LGDTarget, 'BVDIDErrors':bvdidsError }


        else:
            df = self.EDFXCSVClean()
            #EDFXAPI Term Structure will set these values based off the AsOfDate of the term structure being pulled.
            # Term structures pulled should map to the dates loans were initiated
            df['Input Date Month'] = np.nan
            df['Input Date Year'] = np.nan

        if case == 2:

            # Filling the columns with the specified values
            df['Risk Determinant Type'] = RiskDeterminantType
            df['PID'] = PID
            df['Debt / Seniority'] = DebtSeniority
            df['Capital Structure'] = CapitalStructure
            df['Bankruptcy'] = Bankruptcy
            df['Bailout'] = Bailout
            df['Recovery Forecast Type'] = RecoveryForecastType
            df['Location Type'] = LocationType
            df['Assets'] = Assets
            df['Liabilities'] = Liabilities
            #this needs to go away in this function and put in the next function
            df['Industry Classification'] = IndustryClassification

            # Legacy RiskCalc Specifics.  For columns we merge to later we can force empty columns as nan values
            LGDColumns = ['Reference ID', 'Company Name', 'Private/Public',
                        'Risk Determinant Type', 'PID', 'User PD 1', 'User PD 2', 'User PD 3',
                        'User PD 4', 'User PD 5', 'Assets', 'Liabilities', 'Input Date Month',
                        'Input Date Year', 'Location Type', 'Location Code',
                        'Industry Classification', 'Industry Code', 'Debt / Seniority',
                        'Capital Structure', 'Bankruptcy', 'Bailout', 'Recovery Forecast Type']

            # Create the Target Dataframe that's empty so We can concatonate it to it row wise
            LGDTarget = pd.DataFrame(columns=LGDColumns)
            # Set indexes for merging. We alwasy merge on same index.  Since this is an empty dictionary we must concatonate.
            # preserve the index as we will merge for later data mapping.
            LGDTarget = LGDTarget.set_index('Reference ID')
            EDFXValues = df.set_index('Reference ID')
            #Concatenate the dataframe rowwise since it's empty in LGD TARGET now.
            LGDTarget = pd.concat([LGDTarget, EDFXValues])

        elif self.case == 3:

            exposure = self.Case3LGDExposure
            exposureCurrency = self.Case3LGDExposureCurrency
            country = self.Case3LGDCountry
            maturityDate = self.Case3LGDMaturityDate
            IndustryClassification = self.IndustryClassification
            securedUnsecured = self.Case3LGDSecuredUnsecured
            instrumentType = self.Case3LGDInstrumentType
            recoveryCalculationMode = self.Case3LGDRecoveryCalculationMode
            capitalStructure = self.Case3LGDCapitalStructure
            asOfDate = self.Case3LGDasOfDate

            # Filling the columns with the specified values
            df['Risk Determinant Type'] = RiskDeterminantType
            df['exposure'] = exposure
            df['ExposureCurrency'] = exposureCurrency
            df['country'] = country
            df['maturityDate'] = maturityDate
            df['Capital Structure'] = capitalStructure
            df['Bankruptcy'] = Bankruptcy
            df['Bailout'] = Bailout
            df['Recovery Forecast Type'] = RecoveryForecastType
            df['securedUnsecured'] = securedUnsecured
            df['instrumentType']= instrumentType
            df['recoveryCalculationMode'] = recoveryCalculationMode
            df['Location Type'] = LocationType
            # consider taking these out from Case 3 if they do not provide us the requisite information
            df['Assets'] = Assets
            df['Liabilities'] = Liabilities
            #this needs to go away in this function and put in the next function
            df['Industry Classification'] = IndustryClassification
            df['asOfDate'] = asOfDate

            EDFXColumns = ['Reference ID', 'Company Name', 'country', 'maturityDate','securedUnsecured',
                            'Risk Determinant Type', 'PID', 'instrumentType', 'asOfDate',
                            'Input Date Month','Location Type'
                            'Input Date Year', 'Location Type', 'Location Code',
                            'Industry Classification', 'Industry Code',
                            'Capital Structure', 'Recovery Forecast Type']


            # Create the Target Dataframe that's empty so We can concatonate it to it row wise
            LGDTarget = pd.DataFrame(columns=EDFXColumns)
            # Set indexes for merging. We alwasy merge on same index.  Since this is an empty dictionary we must concatonate.
            # preserve the index as we will merge for later data mapping.
            LGDTarget = LGDTarget.set_index('Reference ID')
            EDFXValues = df.set_index('Reference ID')
            #Concatenate the dataframe rowwise since it's empty in LGD TARGET now.
            LGDTarget = pd.concat([LGDTarget, EDFXValues])

        if df is None or df.empty:
            message = "None" if df is None else "empty"
            logger.error(f"EDFXCSVClean returned an {message} DataFrame. Unable to proceed.")
            return None

        if LGDTarget['Industry Code'].isna().all():

            print("You Ran this function more than once and need to re-readIn the .Xlsx and EDFX.csv files and run them through these funtions again.")
            # return None
            return LGDTarget

        else:

            return LGDTarget

    def LGDClientSideEDFXPDTermStructures(self,CleanedDF:pd.DataFrame,asReported:bool=False,timeout:int=900,PDcompute:int=100,
                                          RiskCalcStartDate=None, RiskCalcEndDate = pd.Timestamp.now().strftime('%Y-%m-%d'),
                                          RiskCalchistoryFrequency='monthly', asyncretries1:int=2, asyncretries2:int=15, semaphore:int=500):

        """
            Params:

                PDcompute:  This is a size parameter that allows for sychronous requests from EDFX API without using the asyncio library.

                asyncResponse = Is this a large or small file endpoint request?
                    If asyncResponse=True you will receive a processId.

                    The processId returned is to applied to the edfx/v1/processes/{processId}/files endpoint
                    not the modelInputs endpoint.

                Please reference pd endpoints on EDFXPrime.py's EDFXPD_Endpoint method.  These parameters are specific for LGD requirements
                only and not exhaustive of the entire PD's enpoint class.  You will need to refactor this class with the requisiste params if
                you want to use utilize parameters within the PD's endpoint not found here.

                AsyncBatchSize is referencing self.AsyncBatch batchsize for pulls using the asyncio library (faster synchronous pulls)

                historyFrequency: This endpoint defines the frequency of the PD value history.
                                  Permitted values: "daily"; "monthly"; "quarterly"; or "annual". Default = 'monthly'

                case 2 vs Case 3 is the question within this method.
                    The spirit of the method elicits whether the user wants to pull LGD outputs entirely through the EDFXAPI OR
                    wishes to recreate the legacy RiskCalc.csv input file for Batch LGD Pulls from the Legacy RiskCalc software.
                    Set default as two

        """
        TTCPD = self.TTCPD
        case = self.case
        BatchSize = self.AsyncBatch
        # case 3 params
        if case == 3:
            historyFrequency = self.Case3LGDhistoryFrequency
            startDate = self.Case3LGDPDStartDate
            endDate = self.Case3LGDPDEndDate
        else:
            historyFrequency = RiskCalchistoryFrequency
            startDate = RiskCalcStartDate
            endDate = RiskCalcEndDate

        modelParameters = TTCPD if TTCPD else False

        if 'Reference ID' not in CleanedDF.columns:
            # I'm just resetting the index and grabbing the BvdIds
            payload = CleanedDF.reset_index()['Reference ID']
            EntityIDPayload = self.format_PDpayload(payload)

        else:
            payload = CleanedDF['Reference ID']
            EntityIDPayload = self.format_PDpayload(payload)

        if len(EntityIDPayload) > PDcompute:
            logger.info("Co-routines to be employed at PDs endpoint.")
            # we elect to ALWAYS asyncio library
            pd_df = asyncio.run(self.SynchronousBatchMVP_async(EntityPayload=EntityIDPayload, BatchSize=BatchSize,historyFrequency= historyFrequency,
                                                               startDate=startDate, endDate=endDate, asReported=asReported,
                                                               modelParameters = modelParameters,asyncretries1=asyncretries1,
                                                               asyncretries2=asyncretries2, semaphore=semaphore))

        else:
            pd_dict = self.EDFXPD_Endpoint(entities=EntityIDPayload, startDate = startDate, endDate=endDate,
                                            historyFrequency=historyFrequency, timeout=timeout, modelParameters=modelParameters)
            pd_df = self.EDFXPDParse(pd_dict)


        if pd_df is None or pd_df.empty:
            logger.error(f"No valid data frames were created. {type(pd_df)}")

        #Case 3
        if case == 3:
            # This gets us the dataframe we need to convert to payload
            dftoconverttoLGDPayload = self.LGDCase3PDParse(CleanedDF= CleanedDF, pd_df=pd_df)
            dftoconverttoLGDPayload = self.PDTermStructureCheck(dftoconverttoLGDPayload)
            # this will be a dictionary you need to access the dataframe that is cleaned
            return dftoconverttoLGDPayload
        # CASE 2
        else:
            LargedftoconverttoRiskCalcCSVinputfile = self.LGDCase2PDParse(CleanedDF=CleanedDF, pd_df = pd_df)
            LargedftoconverttoRiskCalcCSVinputfile = self.PDTermStructureCheck(LargedftoconverttoRiskCalcCSVinputfile)
            # this will be a dictionary you need to access the dataframe that is cleaned
            return LargedftoconverttoRiskCalcCSVinputfile

    def LGDServerSidePDAsynchronousEDFXAPIData(self, processID:str=None,LocationType:str = 'ISO',asyncResponse:bool=False,
                                                asReported:bool=False,timeout:int=900,RiskDeterminantType:str = 'PD',DebtSeniority:str='SeniorSecuredBond',
                                                CapitalStructure:str='MostSeniorDebt',RiskCalcEndDate=pd.Timestamp.now().strftime('%Y-%m-%d'),
                                                RecoveryForecastType:str ='UltimateRecovery', Assets:float=None, Liabilities:float=None, PID:str=None,
                                                RiskCalcStartDate=None, Bankruptcy:str = None, Bailout:str = None, RiskCalchistoryFrequency='annual'):


        """
        Server Side Asynchronous Processes.

        This will output one of three outputs.
            i)  Process/Parse a large data request PD Term structure plus LargedftoconverttoLGDPayload dataframe to convert to LGD Payload (case=3)
            ii) Process/Parse a large data request PD Term structure plus LargedftoconverttoRiskCalcCSVinputfile dataframe to convert to LGD Payload (case=2)
            iii)asycnResponse = True ==> processID ==> send this to status endpoint ==> wait till complete ==> come back and send to this method the completed
                processId

                Understand the processID you receive NEEDS to be sent to the status endpoint.

                The process id used can come from 1. endpoints where asyncResponse parameter is available, in this case, the PDS endpoint.

        """
        case = self.case
        # if processID and CleanedDF:
        #     raise ValueError('Both processId and Dataframe provided for this function you should only provide one or the other')
        if processID:

            # we need to look at ServerSide Batch and see if 1000 termstructures will run through status/processing/'complete'/ BLAH BLAH.
            # Thisy may be as low as 500 term structures so if this gets stuck in processing may try and look at 500
            try:
                # This is server side, from AWS Lambda
                downloaded_file = self.EDFXModelInputsGetFiles(processID=processID)
                pd_df = self.EDFXPDParse(downloaded_file)
                # this isn't right, it should parse like in EDFX Case 3
                if case == 3:

                    # All params specified in constructor will flow to RiskCalcLoanSpecification
                    CleanedDF = self.RiskCalcLoanSpecification()

                    LargedftoconverttoLGDPayload = self.LGDCase3PDParse(CleanedDF=CleanedDF, pd_df=pd_df)
                    LargedftoconverttoLGDPayload = self.PDTermStructureCheck(LargedftoconverttoLGDPayload)
                    # do we put the LGD Parse Method here too? why not?
                    # This is a dictionary
                    return LargedftoconverttoLGDPayload

                elif case == 2:

                    CleanedDF = self.RiskCalcLoanSpecification( RiskDeterminantType=RiskDeterminantType, DebtSeniority=DebtSeniority ,
                                                        CapitalStructure= CapitalStructure,
                                                        RecoveryForecastType = RecoveryForecastType,LocationType = LocationType,
                                                        Assets = Assets, Liabilities= Liabilities, PID = PID,
                                                        Bankruptcy= Bankruptcy, Bailout=Bailout)
                    LargedftoconverttoRiskCalcCSVinputfile = self.LGDCase2PDParse(CleanedDF=CleanedDF, pd_df = pd_df)
                    # this is a dictionary
                    LargedftoconverttoRiskCalcCSVinputfile = self.PDTermStructureCheck(LargedftoconverttoRiskCalcCSVinputfile)
                    return LargedftoconverttoRiskCalcCSVinputfile

            except Exception as e:
                logger.error(f"An unexpected error occured. {e}")

        if asyncResponse:

            TTCPD = self.TTCPD
            entities = self.entities
            modelParameters = TTCPD if TTCPD else False

            if case == 3:
                startDate = self.Case3LGDPDStartDate
                endDate = self.Case3LGDPDEndDate
                historyFrequency = self.Case3LGDhistoryFrequency
            else:
                historyFrequency = RiskCalchistoryFrequency
                startDate = RiskCalcStartDate
                endDate = RiskCalcEndDate
            try:
            # now lets leverage EDFXPrime.pyClass # if y
                response = self.EDFXPD_Endpoint(entities,
                                                    asyncResponse=asyncResponse,
                                                    startDate=startDate,
                                                    endDate = endDate,
                                                    historyFrequency=historyFrequency,
                                                    timeout=timeout,
                                                    modelParameters=modelParameters,
                                                    asReported=asReported)
                processId = response['processId']
                return processId

            except ConnectionError as e:
                #Log error
                logger.error("A connection error occurred:", str(e))
                return None

            except Exception as e:
                logger.error("An unexpected error occurred. Please try again or try Batch Synchronous Directly", str(e))
                return None

    def LGDProcessing(self, processID:str):
        """Checks Process"""
        status = self.EDFXModelInputsGetStatus(processID)
        # this is a boolean!
        return status['status'] in ("Processing", "Requested")

    def create_base_loan_scorecard(self, loanScorecardId:str="2b77f0d7-b0e4-4dbc-844d-aabb4376a688") -> loan_scorecard.LoanScorecard:
        """
        Creates base loan scorecard filled with placeholder data.

        According to the EDFXAPI Docs loanScorecardId = "2b77f0d7-b0e4-4dbc-844d-aabb4376a688"
        """
        scorecard = loan_scorecard.LoanScorecard(
            loanScorecardId=loanScorecardId,
            blanketLien=loan_scorecard.LoanScorecardParameterValues.NO,
            collateral=[
                loan_scorecard.Collateral(
                    customCollateralId="123",
                    loanId="123",
                    collateralType=loan_scorecard.CollateralTypes.ACCOUNTS_RECEIVABLE,
                    amount=10000,
                    questionAnswers=[
                        loan_scorecard.CollateralQuestionAnswer(name=loan_scorecard.CollateralQuestions.STANDARD_PAYMENT_TERMS,
                                                value=loan_scorecard.CollateralAnswers.NOT_AVAILABLE),
                        loan_scorecard.CollateralQuestionAnswer(name=loan_scorecard.CollateralQuestions.CUSTOMER_CONCENTRATION,
                                                value=loan_scorecard.CollateralAnswers.HIGH),
                        loan_scorecard.CollateralQuestionAnswer(name=loan_scorecard.CollateralQuestions.CUSTOMER_CREDIT_QUALITY,
                                                value=loan_scorecard.CollateralAnswers.EXCELLENT),
                    ]
                )
            ],
        )
        return scorecard

    def EDFXlgd_function(self, df: pd.DataFrame, cumulative:bool=True, use_loan_scorecard:bool=False, user_defined_loan_scorecard:loan_scorecard.LoanScorecard=None):
        """
        We are turning the Case 4 DataFrame we cbuilt in case3datadictionary and transforming it to the EDFX-API LGD payload,

        We are using the loan inputs from instantiation and any scorecard information the user would like to put into the payload. 

            CASE 3 PARAMS:
            Calculating LGD
            Use this endpoint to calculate LGD in EDF-X API, the calculations are on-demand and use Loss Given Default 4.0 (LGD 4.0) model.

            Suggest Edits
            The main metrics currently accessible are:

            LGD (Loss Give Default)
            EL (Expected Loss)
            EL IR (Expected Loss Implied Rating)

            LGDCASE3Parameters:
                | Field                           | Required | Description                                                                 | Example        |
                |---------------------------------|----------|-----------------------------------------------------------------------------|----------------|


                |   loanId                        | Yes      | Loan Identifier.                                                            | Loan123        |
                |   loanName                      |          | Loan label or name.                                                         |                |
                |   asOfDate                      | Yes      | This is the date used to calculate the LGD values./Macro                    | "2021-01-01"   |
                |                                 |          | Format: YYYY-MM-DD.                                                         |                |
                |   instrumentType                | Yes      | The debt type and seniority class of the instrument.                        | “Term Loan”    |
                |   securedUnsecured              | Yes      | Indicates whether the instrument is secured or unsecured.                   | “Secured”      |
                |                                 |          | Only applicable for certain instruments.                                    |                |
                |   capitalStructure              | Yes      | Specifies the borrower's capital structure at the time of default.          | “Unknown”      |
                |   recoveryCalculationMode       | Yes      | Indicates which recovery model to use for the calculation.                  | “Ultimate Recovery” |
                |
                |   exposure                      | Yes      | Amount of exposure at the time of asOfDate.                                 | 1000000        |
                |   originationDate               |          | Date the loan was originated. Format: YYYY-MM-DD.                           | "2022-12-31"   |
                |   maturityDate                  |          | Date the loan matures. Format: YYYY-MM-DD.                                  | "2025-06-30"   |
                |   exposureCurrency              |          | The currency denomination of the exposure amount.                           | "USD"          |


        """
        # Case 3 paramaters
        def convert_to_payload(row, idx):
            loan_id = str(row.get('Loan ID')) if pd.notna(row.get('Loan ID')) else f"loan{str(idx)+str(1)}"
            loan_name = str(row.get('Loan Name')) if pd.notna(row.get('Loan Name')) else f"loan{str(idx)+str(1)}"

            loan_parameters = {
                "loanId": str(loan_id),
                "loanName": loan_name,
                "asOfDate": row.get('asOfDate') or self.Case3LGDasOfDate,
                "exposure": row.get('exposure') or self.Case3LGDExposure,
                "originationDate": row.get('originationDate') or self.case3LGDOriginationDate,
                "maturityDate": row.get('maturityDate') or self.Case3LGDMaturityDate,
                "exposureCurrency": row.get('exposureCurrency') or self.Case3LGDExposureCurrency,
                "instrumentType": row.get('instrumentType') or self.Case3LGDInstrumentType,
                "securedUnsecured": row.get('securedUnsecured') or self.Case3LGDSecuredUnsecured,
                "recoveryCalculationMode": row.get('recoveryCalculationMode') or self.Case3LGDRecoveryCalculationMode,
                "capitalStructure": row.get('capitalStructure') or self.Case3LGDCapitalStructure or "Unknown",
            }

            # Add additional parameters if they are not None. Class ==>self.create_params_dict
            loan_parameters = self.create_params_dict(loan_parameters)

            # Add the scorecard
            if use_loan_scorecard:
                if user_defined_loan_scorecard:
                    loan_parameters['loanScorecard'] = user_defined_loan_scorecard.to_dict()
                else:
                    loan_parameters['loanScorecard'] = self.create_base_loan_scorecard().to_dict()

            # Get term structures from df
            term_structure_cumulative_pd = {k: v for k, v in row.items() if k.startswith("cumulativePd")}

            return {
                "entityId": str(row.get('Company Name', 'Unknown Company')),
                "country": self.Case3LGDCountry,
                "primaryIndustry": str(row.get("Industry Code", "Unknown Industry")),
                "primaryIndustryClassification": self.IndustryClassification,
                "loans": [
                    {
                        "loanParameters": loan_parameters,
                        "termStructureCumulativePd": term_structure_cumulative_pd
                    }
                ]
            }

        payload = [convert_to_payload(row, idx) for idx, row in df.iterrows()]
        return payload

    async def EDFXLGD_Async(self, semaphore:asyncio.Semaphore, entities:list, LGDasyncretries1:int=3 ,LGDasyncretries2:int = 15):


        """
        Speeds up Large LGD Requests. For regular LGD call you can find it within EDFXPrime.py

        """
        headers = self.EDFXHeaders()['JSONGet']['headers']
        endpoint = "/edfx/v1/entities/loans"
        url = urljoin(self.base_url, endpoint)
        params = {
                "entities": entities
            }
        failedLGD=[]
        # This inner function is responsible for making the actual POST request.
        # It's defined as async, meaning it's a coroutine and will be run in the event loop.
        async def _post_async(LGDasyncretries1:int=LGDasyncretries1):
            # First portion of Retry Logic
            for attempt in range(LGDasyncretries1):
                
                async with semaphore:
                    try:                        
                        # The 'async with' statement is used to manage the context of the aiohttp session's POST request.
                        # This is where the actual POST request is made.
                        async with session.post(url, headers=headers, json=params) as response:
                            payload = await response.json()

                            if 'entities' not in payload:
                                logger.error(f"Server-side Response: {payload} \n Params for failedLGD request are {params}.")
                                failedLGD.append(params)

                            else:
                                return payload
                    
                    except ServerTimeoutError as e:
                        logger.error(f"ServerTimeoutError encountered: {str(e)} | Attempt {attempt+1} of {LGDasyncretries1}")
                            
                    except ClientError as e:  
                        logger.error(f"ClientError encountered: {str(e)} | Attempt {attempt+1} of {LGDasyncretries1}")
                    
                    except Exception as e:    
                        logger.error(f"Unexpected error encountered: {type(e).__name__}: {str(e)}")

                await asyncio.sleep(2)

        # ClientSession is used to make HTTP requests. The 'async with' statement here ensures that
        # the session is created and terminated properly.
        # The timeout parameter specifies how long the client will wait for the server's response.

        async with ClientSession(timeout=ClientTimeout(total=10000)) as session:
            # The for loop implements the retry logic.
            for ii in range(LGDasyncretries2, 0, -1):
                try:
                # Attempting the POST request. If successful, the function will return the response.
                    return await _post_async()
                except Exception as e:
                       # Logging any exceptions that occur during the request.
                    logger.exception(f"This batch has an exception {e}. There are {ii} retries left.")
                    if ii > 1:
                        await asyncio.sleep(1)  # Delay between retries, adjust as needed
        if failedLGD:
            # send LGD Params that couldn't get through to a vector of uniqe bvdis to get sent again.
            FailedLGD = {"FailedLGDParams": failedLGD}
            FailedLGD = pd.DataFrame(FailedLGD).drop_duplicates()
            FailedLGD.to_csv(f"{datetime.now()}_FailedLGDParams.csv")

    async def LGDSynchronousBatchMVP_async(self,EntityPayload:list[dict[str,str]], BatchSize:int, FormatType='Wide',
                                           LGDasyncretries1:int=2, LGDasyncretries2:int=15, sempcount:int = 600):

        """
        This is a Batch co-routine for users who would like to batch requests within a co-routine. 
        """
        semaphore = asyncio.Semaphore(sempcount)
        BatchSize = self.AsyncBatch
        dfs = []
        # Generate list of batches.
        batches = list(self.split_list(EntityPayload, BatchSize=BatchSize))

        # Gather the results of calling EDFXPD_Endpoint_async for each batch in the batches list.
        # This is async method so the API calls made by EDFXPD_Endpoint_async will be made in parallel.
        responses = await asyncio.gather(
            *(self.EDFXLGD_Async
              ( semaphore=semaphore,
                entities=b,
                LGDasyncretries1=LGDasyncretries1,
                LGDasyncretries2=LGDasyncretries2) for b in batches
            ), return_exceptions=False
        )

        for pd_dict in responses:
            # go to next loop so you dont append a None objct to the list
            if pd_dict is None:
                continue
            try:
                # parse the dictionary object to a pandas dataframe
                pd_df = self.EDFXLGDParse(pd_dict, FormatType=FormatType)
                if pd_df is None:
                    continue
                # append them to a list, 30 row object elements per appending
                dfs.append(pd_df)
            except:
                logger.error(f'Parsing batch response failed: {format_exc(1, False)}')

        if dfs:
            return pd.concat(dfs)
        else:
            logger.info("No data frames were created.")
            return None


    def LGDCase3datadictionary(self, Serverside:bool=False, processID:str=None,asyncResponse:bool=False,asReported:bool=False,
                               timeout:int=900,PDcompute:int=100,asyncretries1:int=3, asyncretries2:int=15):

        """
        This is a helper funciton for EDFX API CASE 3 only

        Given a loan or prtfolio of loans is specified, we can build out a dataframe that will be converted into EDFX-API's 
        LGD Payload.

        The finanl DataFrame here will be pased to our EDFXLGDFinal method that applies a nested EDFXlgd_function and EDFXLGD_Async
        methods.

        For context lets think about this process as follows for CASE3:

        We need information from:

            i) Batch/mapping endpoint
            ii) pds endpoint
            iii) LGD endpoint

            Thus, this dataframe is pulling information for i) and ii) and since the pds endpoint allows for serverside
            asynchronous batching we allow for a processID and asyncResponse flexibility to this method.

        UNDERSTAND: WE will have a Superior Solution by end of 2024 where we will abstract the processID approach.

        """

        if Serverside:
            # Go through the serverside paths
            if processID:
                Case3datadictionary = self.LGDServerSidePDAsynchronousEDFXAPIData(processID=processID)
                return Case3datadictionary
            else:
                processID = self.LGDServerSidePDAsynchronousEDFXAPIData(asyncResponse=asyncResponse, PDcompute=PDcompute, timeout=timeout,
                                                                        asReported=asReported)
                return processID
        else:

            Cleandf = self.RiskCalcLoanSpecification()
            case3dictionary = self.LGDClientSideEDFXPDTermStructures(CleanedDF=Cleandf,asReported=asReported,timeout=timeout,PDcompute=PDcompute,
                                                                     asyncretries1=asyncretries1, asyncretries2=asyncretries2)

            #Error Happening here with LGD Case 3 parse
            # if case3dictionary['cleaned_df'] is None:
            #     logger.error(f"error occuring at {case3dictionary['cleaned_df']} is NoneType but we care skipping.")
                # continue
            return case3dictionary

    def EDFXLGDFinal(self, df:pd.DataFrame, FormatType='Wide', AsyncBatch:int=2, LGDCompute:int=100, use_loan_scorecard: bool = False,
                      LGDasyncretries1:int=2, LGDasyncretries2:int=15, sempcount:int = 600,
                      user_defined_loan_scorecard: loan_scorecard.LoanScorecard = None):

        """
        This is the LGD call for CASE 3.

        Here we are getting the LGD parameters, parsing the parameters, and renaming the columns to
        make the dataframe columns more readable.

        params:
            df: CaseDataframe Parsed
            FormatType: LGD Parsing 'FormatType'.  once we get the LGD Payload back we parse it into a 'row' we place into the final dataframe
            AsyncBatch: Batch Size for co-routine batch sizes for the LGD async method
            LGDCompute = amount of payloads to run syncronously before using the co-routines
            use_loan_scorecard: = Boolean for whether the user would like to apply the scorecard or not. 
            user_defined_loan_scorecard: So we made a dataclass that explicitly allows a user to build a class object they can place here
                                        for the given scorecard parameter which we parse and add to the LGD Payload.

        The output is a pandas dataframe where users can see the relvant LGD outputs from the EDFX-API LGD Payload
        The last part of the code in this method is us cleaning up the parsed dataframe to be a bit more readable.

        """

        payload = self.EDFXlgd_function(df, use_loan_scorecard=use_loan_scorecard, user_defined_loan_scorecard=user_defined_loan_scorecard)
      
        if len(df) > LGDCompute:

            step_3_df = asyncio.run(self.LGDSynchronousBatchMVP_async(EntityPayload=payload, BatchSize=AsyncBatch, FormatType=FormatType,
                                                                    LGDasyncretries1=LGDasyncretries1, LGDasyncretries2=LGDasyncretries2,
                                                                    sempcount=sempcount))
        else:

            step_3_response = self.EDFXCalculatingLGD(payload)
            step_3_df = self.EDFXLGDParse(step_3_response, FormatType=FormatType)
            
        # This works for Wide or Long. We are just making the dataframe easier to read
        original_columns = step_3_df.columns.tolist()
        # Creating the renaming dictionary
        renamed_columns = {col: col.split('_')[-1] for col in original_columns if col != 'entityId'}
        # Renaming the columns in the DataFrame
        step_3_df.rename(columns=renamed_columns, inplace=True)
        # Define the order of the first few columns explicitly
        first_columns = ['entityId', 'longRunLgd', 'longRunRecovery', 'tenor', 'pd', 'expectedLossAmount', 'expectedLossPercent', 'expectedLossRating']
        # Add the rest of the columns in their original order, but renamed
        ordered_columns = first_columns + [col for col in step_3_df.columns if col not in first_columns]
        # Reordering the DataFrame columns
        df = step_3_df[ordered_columns]

        return df

    def Testcase1(self):

        """
        Proof of Concept Function Case 1 Users that would value a flexible Case 1 option with their loan/loas should apply the RiskCalcLoanSpecification method
        with the appropriate loan parameters and ensure that they instantiate the the class properly for the best tailored case1 approach.

        YOU CANNOT USE Entities payload with Case 1. It assumes one uploaded their portfolio within EDFXAPI and has downloaded the .csv file and
        converted it to a pandas dataframe 'df'.  This df is the argument fed at the LGD class instantiation.
        """
        entities = self.entities
        df = self.df

        if df is not None and isinstance(df, pd.DataFrame) and not df.empty:
            # case 1 and data fed at instantiation
            case1df = self.RiskCalcLoanSpecification()['cleaned_df']
            return case1df

        elif entities:
            print("Case1 does not handle entitiy Payloads. ")
            return None

    def TestcaseClientSide2(self,startDate = datetime.now().strftime('%Y-%m-%d'), endDate=datetime.now().strftime('%Y-%m-%d'),
                   historyFrequency='annual'):

        """Proof of Concept Function Case 2"""

        entities = self.entities
        df = self.df

        if df is not None and isinstance(df, pd.DataFrame) and not df.empty:
            start_time = datetime.now()
            Cleandf = self.RiskCalcLoanSpecification()
            # this is now a dictionary
            case2df = self.LGDClientSideEDFXPDTermStructures(CleanedDF=Cleandf, RiskCalcStartDate= startDate,
                                                             RiskCalcEndDate=endDate,RiskCalchistoryFrequency= historyFrequency)['cleaned_df']
            end_time = datetime.now()
            print('Duration:', end_time - start_time)
            return case2df

        elif entities:
            start_time = datetime.now()
            Cleandf = self.RiskCalcLoanSpecification()
            case2df = self.LGDClientSideEDFXPDTermStructures(CleanedDF=Cleandf, startDate=startDate, endDate=endDate,
                                                              historyFrequency=historyFrequency)['cleaned_df']
            end_time = datetime.now()
            print('Duration:', end_time - start_time)
            return case2df


if __name__ == "__main__":

    print("LGDClass to support Moody's Predictive Analytics EDFX Offering")

