import io
import requests
import warnings
import io
import urllib.parse
import datetime
import time
import logging
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import moodys_keys as mk
import requests
import json
import os
from enum import Enum
from urllib.parse import urljoin,urlencode,quote_plus
from EDFXAuthentication import EDFXClient


# Helper function to flatten dictionaries.
# It is not a static method because it is using recursion and will require hard coding the class name, better to keep it external
def flatten_dict(input_dict:dict, separator:str='_',  parent_name:str='')->dict:

    """
    Recursively flattens a dictionary.
    Each key in the flattened dictionary is a concatenation of the parent key and the current key.
    If a key has multiple levels of dicts/lists, the keys are concatenated using underscores as ParentNames.
    Values are converted to strings.
    Args:
        input_dict: The dictionary to be flattened.
        separator: The separator used to concatenate keys.
        parent_name: The parent name that will be added as prefix key
    Return:
        dict: flattened_dict

    """
    flattened_dict = {}
    for key, value in input_dict.items():
        if isinstance(value, dict):
            flattened_dict.update(flatten_dict(value, separator, key))
        elif isinstance(value, list):
            for index, item in enumerate(value):
                item_key = f"{key}{separator}{index}"
                if isinstance(item, dict):
                    flattened_dict.update(flatten_dict(item, separator, item_key))
                else:
                    flattened_dict[item_key] = item
        else:
            if parent_name:
                flattened_dict[f'{parent_name}{separator}{key}'] = value
            else:
                flattened_dict[key] = value
    return flattened_dict

def filter_out_list_and_dict(dictionary: dict, prefix: str = ''):
    '''
    Returns a version of dictionary that has only keys that are not dict or list type.
    If prefix is provided it will be added to keys.
    '''
    return {
        f'{prefix}_{key}' if prefix else key: value for key, value in dictionary.items()
        if not isinstance(value, (list, dict))}

def PDDrivers_extract_ratios(entity: dict) -> list:
    """
    HelperFunction to Parse Pd History Json
    """
    ratios = []
    if not isinstance(entity, dict):
        raise TypeError(f'Expected entity to be a dict, but got {type(entity)}: {entity}')

    # Handle inputData section
    input_data = entity.get('inputData', [])
    for item in input_data:
        if isinstance(item, dict) and "message" in item:
            ratio_data = {
                "entityId": entity['entityId'],
                "asOfDate": None,
                "Type": "Error",
                "ErrorMessage": item["message"]
            }
            ratios.append(ratio_data)
    #handle results section
    result_data = entity.get('resultData', {})
    for key, items in result_data.items():
        # Check if the item is not a list of dictionaries, then convert it to one
        if not isinstance(items, list):
            items = [items]

        for item in items:
            # Check if the item is a dictionary
            if not isinstance(item, dict):
                continue

            if key == 'relativeContribution':  # Check for current data
                ratio_data = {"entityId": entity['entityId'], "asOfDate": item['asOfDate'], 'Type': 'Current'}
            else:
                ratio_data = {"entityId": entity['entityId'], "asOfDate": item['asOfDate'], 'Type': key}

            for k, value in item.items():
                ratio_data[k] = value
            ratios.append(ratio_data)

    return ratios

class FinancialTemplate(Enum):

    """
    Use of Enums:

    Purpose: Enums can represent a set of named values, ensuring that only those values can be used.

    Benefit: Prevents arbitrary string values from being passed to the function. This leads to more
    predictable behavior and reduces potential bugs.

    """

    UNIVERSAL = 'Universal'
    BANK = 'Bank'

class OutputFormat(Enum):
    PANDAS = 'Pandas'
    EXCEL = 'Excel'
    CSV = 'Csv'

class EDFXEndpoints(EDFXClient):

    """
    EDFXEndpoints Class provides all EDF-X Endopints.

    Class attributes will be constructed with the unique
    headers and payloads for EDF-X

    """
    EDFXProxies = {}

    def __init__(self, api_publickey:str = None, api_privatekey:str=None, proxies={}, *args, **kwargs):
        super().__init__(api_publickey, api_privatekey, proxies, *args, **kwargs)
        # this token is in bytes that needs to be in str type

    def EDFXHeaders(self, process_id=None):

        """
        This method calls get_bearer_token() to get the current bearer token and returns the headers.
        NOTE: get_bearer_token() checks if the token needs to be renewed on each call.

        If you're using the ModelInputsUploadProcess be sure to feed the process_id
        Some of these parameters appear obnoxious but that's due to the fact the EDF-X API
        Requires them to be passed as such (see boundry in ModelInputsProcess)

        """
        bearer_token = self.get_bearer_token()
        bearer = bearer_token.decode('utf-8') if bearer_token else None

        if bearer is not None:
            return  {
                    "JSONBasic": {
                        "headers" : {
                                "accept": "application/json",
                                "content-type": "application/json",
                                "authorization": "Bearer " + bearer
                                }
                            },
                    "JSONMultipart":{
                        "headers" : {
                                "accept": "application/json",
                                "content-type": "multipart/form-data",
                                "authorization": "Bearer " + bearer
                                }
                            },
                    "JSONGet": {
                        "headers": {
                                "accept": "application/json",
                                "authorization": "Bearer " + bearer
                                    }
                            },
                    "ModelInputsProcess": {
                        "headers": {
                                    "accept": "application/json",
                                    "content-type": "multipart/form-data; boundary=---011000010111000001101001",
                                    "authorization": "Bearer " + bearer
                                    }
                        },
                    "ModelInputsUploadProcess":{
                        "headers": {
                                        'x-amz-tagging': 'edfx_process_id=' + process_id if process_id else 'process_id_not_used.',
                                        'content-type': 'text/csv'
                                    }
                        }
                    }
        else:
            raise ValueError('bearer is None')

    def create_params_dict(self, params):
        """
        Helper Function to select params

        """
        params = {key:value for key, value in params.items() if value is not None and value is not False}
        return params

    def EDFXCurl_process(self):
        pass

    def EDFXEntitySearchEndpoint(self,query:str, limit:int=None, offset:int=None):

        """
        Entity Search Endpoint:

            query:required Param

            limit: 	Specify the maximum number of results returned in single call.

            offset: 	Specify the index from which to start returning results.
                        Use with the limit parameter to get result batches to process.
                        For example, limit= 10, offset = 20, returns the results indexed
                        from 20-29.
        """
        search = "/entity/v1/search"
        base = self.base_url
        Searchurl = urljoin(base,search)
        #general post headers for RESTFUL API's
        headers = self.EDFXHeaders()['JSONBasic']['headers']

        payload = {
                    'query': query,
                    'limit': limit,
                    'offset':offset
                }

        response = requests.post(Searchurl, headers=headers, json=payload)
        payload = response.json()

        return payload

    def EDFXBatchEntitySearch(self,queries:list[dict]):

        """
        Batch Entity Explanation,

        An object containing the companies identifiers. The currently supported identifiers
        are listed in "Appendix: Supported Identifiers";
        the keys accepted by the json for the main ones are:

        - entityidentifierbvd- Identifier from Orbis
        - entityidentifierorbis - Identifier from Orbis
        - entityIdentifierTaxNumber
        - entityIdentifierEin - Employer Reference Number
        - isin - International Securities Identification Number
        - cusip - Committee on Uniform Securities Identification Procedures
        - lei - Legal Entity Identifier
        - pid - CreditEdge Identifier
        - ticker - Stock symbol

        Provide the keys and the related values. ==> Example of a request of eac,

            EX of query to feed:
            [{ "entityIdentifierPartitaIva": 1959680388 }, { "lei": "549300CRVT18MXX0AG93" }, { "cusip": 594918 }, { "isin": "US3453708600" }, { "pid": "34537A" }]

        """
        base = self.base_url
        batch = "/entity/v1/mapping"
        batchurl = urljoin(base,batch)
        #general post headers for RESTFUL API's
        headers = self.EDFXHeaders()['JSONBasic']['headers']
        # Simple error handling: It's just saying if they don't feed a list of dictionary elements return that message
        if not isinstance(queries, list) or not all(isinstance(q, dict) for q in queries):
            print("You need to feed a list of dictionary elements. For example: queries = [{'pid': '34537A'}, {'cusip': 594918}]")
            return
        else:
            payload = { "queries" : queries}
            response = requests.post(batchurl, headers=headers, json=payload)
            batch_response = response.json()

            return batch_response

    def EDFXPD_Endpoint(self, entities:list[dict[str,str]]=None, startDate:str=None, endDate:str=None, historyFrequency:str='monthly',
                        asyncResponse:bool=False, asReported:bool=False, modelParameters:bool=False, includeDetailResult:bool=False,
                        includdeDetailInput:bool = False, includeDetailModel:bool=False, includeTermStructure: bool=True, processId:str=None,
                        CreditEdge:bool=False, RiskCalc:bool=False, TradePayment:bool=False ):

        """
        Params: These are the values of the paramater dictionary you are feeding the method.

            Entities: The object is a list of dictionary elements: value = [{'entityId': 'identifier'}]
                        multiple entities exmampe:
                        [{ "entityId": "DELEI421244" }, { "entityId": "US800890963" }, { "entityId": "FR813755949" }]

            startDate: If provided, generates a history of PD values in the format YYYY-MM-DD.

            endDate: The date of the PD you are retrieving in the format YYYY-MM-DD.

            historyFrequency: reference APIHUB FOR FULL details:
                            This endpoint defines the frequency of the PD value history.
                            Allowed values are: "daily"; "monthly"; "quarterly"; or "annual". Default = 'monthly'

            modelParameters: This is referring to Financial Statement Only.  Set to TRUE if you need FSO EDF
            processID: This parameter is alternative to providing the list of entities.
                        The values accepted are process IDs received when uploading a csv file through the /modelInput endpoint.

            includeDetail: options:
                                i) 'resultDetail'
                                ii) 'inputDetai'
                                iii) 'modelDetail'

            CreditEdge: = True if you would like the CE Structural EDF. Only listed companies appear since the
                          model relies on equity market prices.

            RiskCalc: = True if you would like the RiskCalc EDF returned mapped to the model internally allocated

            TradePayment: = True if you would like the TradePayment EDF returned (given it exists)
                            Payment PDs are only calculated for US companies with netSales < 500mln USD
                            for which payment information is available.

        ---------------FOR YOUR REFERENCE----------------------------------------------------------
        When no startDate and endDate is provided, the API serves the latest PD available considered.
        For private firms this is the latest available month, while for active public firms this is
        the latest available day within the last 10 days. Dates beyond these can be accessed in the
        history by specifying startDate and endDate.

        """
        if entities:
            if isinstance(entities, dict):
                for key, value in entities.items():
                    if not isinstance(key,str) or not isinstance(value,str):
                        print("Error: you need to either feed a dictionary of 'EntityID' as key and an EDFX Qualified ID as the value." )
                        return None
                entities = [entities]

                # Check if entities is a list of dictionaries with the key "entityId"
            if not isinstance(entities, list) or not all(isinstance(e, dict) and "entityId" in e for e in entities):
                print("Error: entities parameter must be a list of dictionaries with an 'entityId' key")
                return None

        headers = self.EDFXHeaders()['JSONBasic']['headers']

        # Define initial parameters
        params = {
            'startDate': startDate,
            'endDate': endDate,
            'historyFrequency': historyFrequency,
            'asyncResponse': asyncResponse,
            'asReported': asReported,
            'modelParameters':
                                {'fso': modelParameters} if modelParameters is not None else None,
            'includeDetail': {
                "resultDetail":includeDetailResult,
                "inputDetail": includdeDetailInput,
                "modelDetail": includeDetailModel,
                "includeTermStructure": includeTermStructure
            }
        }
        if entities:
            params['entities'] = entities
        if processId:
            params['processId'] = processId

        base = self.base_url

        EDFXPDEnpoints = {
            'CreditEdge':   '/edfx/v1/entities/pds/creditedge',
            'RiskCalc':     '/edfx/v1/entities/pds/riskcalc',
            'TradePayment': '/edfx/v1/entities/pds/payment',
            'default':      '/edfx/v1/entities/pds'
        }

        if CreditEdge:
            endpoint = EDFXPDEnpoints['CreditEdge']
        elif RiskCalc:
            endpoint = EDFXPDEnpoints['RiskCalc']
        elif TradePayment:
            endpoint = EDFXPDEnpoints['TradePayment']
        else:
            endpoint = EDFXPDEnpoints['default']

        url = urljoin(base, endpoint)
        response = requests.post(url, headers=headers, json=params)

        payload = response.json()
        return payload


    def EDFXPD_Drivers(self, entities:list[dict[str,str]], historyFrequency:str="monthly" ,startDate:str=None, endDate:str=None,
                        asyncResponse:bool=False, asReported:bool=False, modelParameters:bool=False,includeDetailResult:bool=True,
                        includdeDetailInput:bool = False, includeDetailModel:bool=False, processId:str=None):

        """
        I need to determine the above method to know the following structure for the below.

        We MUST set the boolean values otherwise the parameter function will not return appropriately

        Required arguments are: entities, startDate

        """

        if processId and entities:
            raise ValueError('Both processId and entities provided')

        if processId:
            entities = [{"entityId": processId}]

        # Check if entities is a list of dictionaries with the key "entityId"
        if not isinstance(entities, list) or not all(isinstance(e, dict) and "entityId" in e for e in entities):
            raise ValueError("entities parameter must be a list of dictionaries with an 'entityId' key")

        headers = self.EDFXHeaders()['JSONBasic']['headers']
        params = {
                "entities": entities,
                "startDate": startDate,
                "endDate": endDate,
                "historyFrequency": historyFrequency,
                "asyncResponse": asyncResponse,
                "asReported": asReported,
                "modelParameters":
                                    {'fso': modelParameters} if modelParameters is not None else None,
                "includeDetail": {
                    "resultDetail": includeDetailResult,
                    "inputDetail": includdeDetailInput,
                    "modelDetail": includeDetailModel
                }
            }
        # Remove None values from params
        # params = {k: v for k, v in params.items() if v is not None}
        base = self.base_url
        endpoint = '/edfx/v1/entities/pds/detailHistory'
        url = urljoin(base, endpoint)

        response = requests.post(url, headers=headers, json=params)

        if response.status_code == 200:
            payload = response.json()
            return payload
        else:
            print(f"Request failed with status code {response.status_code} {response.text}")
            return None

    def EDFXClimatePD(self,scenarioCategory:str,transition:bool,physical:bool,combined:bool,entityName:str,entityId:str,
                        primaryCountry:str,primaryCountryWeight:str,primaryIndustryClassification:str,primaryIndustry:str,
                        industryWeight:str,pd:float,impliedRating:str,financialStatementDate:str=None,
                        carbonEmissionDate:str=None,asOfDate:str=None,totalAssets:float=None,netSales:float=None,
                        scope1Emission:float=None,scope2Emission:float=None,carbonFootPrint:float=None,
                        physicalRiskScoreOverwrite:int=None,resultDetailMain:bool=False,resultDetailTransition:bool=False):

        """
        Important Params:
        scenarioCategory: Valid values: "NGFS", "NGFS2", "NGFS3","NGFS3_REMIND","MAS", See Appendix: Climate Scenarios
                        for more information about the supported scenarios.
        TYPES OF RISK: Desired risk type. At least one of these parameter has to be set to true.
        transition: Type of Risk
        physical: TYpe of Risk
        combined: Type of Risk
        carbonEmissionDate: Represents the snapshot date relative to the carbon foot print provided.
        scope1Emission:These are direct emissions from sources that are owned or controlled by the company.
                        For example, emissions from a company's own vehicles, boilers, or manufacturing processes.

        scope2Emission: These are indirect emissions that come from the consumption of purchased electricity, heat, or steam.
                        For example, emissions from the power plants that generate the electricity used by the company.

        Use the /climate/v2/entities/pds endpoint to access the climate-adjusted PDs. These are credit risk metrics adjusted
        to incorporate the climate risk impact. The climate-adjusted PDs are the result of a stress testing exercise following
        some pre-defined scenarios sets, typically released by regulators or relevant institutions (ex. NGFS III).
        The output are separate for physical risk, transition risk, and combined risk.

        We do maintain a set of pre-calculated and ready available results: currently, this universe corresponds to actively
        traded public firms. For any other firm, i.e. private firms, the API request triggers an on-demand calculator
        that outputs climate adjusted metrics starting from the set of user-provided inputs. Hence, more input parameters are
        required for private firms

        For comprehensive param understanding see:
        https://docs.moodysanalytics.com/moodys-edfx-climate/docs/retrieving-climate-adjusted-pds
        within EDF-X API Hub

        """

        params = {"entities": [
                    {
                        "entityId": entityId,
                        "entityName": entityName,
                        "financialStatementDate": financialStatementDate,
                        "pd": pd,
                        "impliedRating": impliedRating,
                        "asOfDate": asOfDate,
                        "carbonEmissionDate": carbonEmissionDate,
                        "qualitativeInputs": {
                            "industriesDetails": [
                                {
                                    "industryWeight": industryWeight,
                                    "primaryIndustry": primaryIndustry,
                                    "primaryIndustryClassification": primaryIndustryClassification
                                }
                            ],
                            "regionDetails": [
                                {
                                    "primaryCountry": primaryCountry,
                                    "primaryCountryWeight": primaryCountryWeight
                                }
                            ]
                        },
                        "quantitativeInputs": {
                            "carbonFootPrint": carbonFootPrint,
                            "netSales": netSales,
                            "scope1Emission": scope1Emission,
                            "scope2Emission": scope2Emission,
                            "totalAssets": totalAssets,
                        },
                        "physicalRiskScore": { "physicalRiskScoreOverwrite": physicalRiskScoreOverwrite }
                    }
                ],
                "scenarios": { "scenarioCategory": scenarioCategory },
                "riskTypes": {
                    "combined": combined,
                    "physical": physical,
                    "transition": transition
                },
                "includeDetail": {
                    "resultDetailMain": resultDetailMain,
                    "resultDetailTransition": resultDetailTransition
                }}

        headers = self.EDFXHeaders()['JSONBasic']['headers']
        endpoint = "/climate/v2/entities/pds"
        url = urljoin(self.base_url, endpoint)
        response = requests.post(url, json=params, headers=headers)
        return response.json()

    def EDFXClimateIndustryTransitionRiskDrivers(self, industry:str, scenarioCategory:str,scenario:str=None):

        """
        The drivers for transition risk at region/country and
        industry granularity level are pre-calculated and can be accessed using the following endpoints.

        Required Params:

            - industry  ex: 'N40'  ex: See Appendix Climate Sectors for the list of valid values.
            - scenarioCategory  ex: 'NGFS' ; Valid values: "NGFS",”MAS”,”NGFS2”,"NGFS3","NGFS2_REMIND".
            - senario ex: Valid for NGFS: “orderlyScenario”, “disorderlyScenario”, “hothouseScenario”, “hotHouseTailScenario”.
        """
        # Construct the endpoint
        scenario_param = f"&scenario={scenario}" if scenario else ""
        endpoint = f"/climate/v2/industry/industryTransitionPaths?scenarioCategory={scenarioCategory}&industry={industry}{scenario_param}"
        headers = self.EDFXHeaders()["JSONGet"]['headers']
        url = urljoin(self.base_url, endpoint)

        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()  # Raise an error for bad responses
            return response.json()

        except requests.RequestException as e:
            # Handle the exception as you see fit
            print(f"Error fetching data: {e}")
            return None

    def EDFXClimateRegionTransitionPaths(self,scenarioCategory:str,regionIndustry:tuple[str,str], industry: str, scenario:str=None):

        """
        The drivers for transition risk at region/country and industry
        granularity level are pre-calculated and can be accessed using the following endpoints.

        see appendix for full details here:
        https://docs.moodysanalytics.com/moodys-edfx-climate/docs/retrieving-transition-risk-drivers-for-sector-and-region

        params:
            scenarioCategory: example => "NGFS"
            regionIndustry: example => ("USA","N30") # no space
            scenario: example => "noAdditionalPolicyScenario"
            industry: example => "N13"
        """

        # Format the tuple
        regionIndustry_str = f"({regionIndustry[0]},{regionIndustry[1]})"
        # URL encode the tuple string
        regionIndustry_encoded = quote_plus(regionIndustry_str)
        endpoint = "/climate/v2/industry/industryTransitionPaths"
        params = {
            'scenarioCategory': scenarioCategory,
            'regionIndustry': regionIndustry_encoded,
            'industry': industry
        }
        if scenario:
            params['scenario'] = scenario
        headers = self.EDFXHeaders()["JSONGet"]['headers']
        url = urljoin(self.base_url, endpoint)
        # error handling
        try:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()  # Raise an error for bad responses
            return response.json()

        except requests.RequestException as e:
            # Handle the exception as you see fit
            print(f"Error fetching data: {e}")
            return None

    def EDFXClimateReportPublic(self,reportType:str,reportFormat:str,scenarioCategory:list[str],entities:list[dict[str:str]]):

        """
        The Reports endpoint allows access to PDF and CSV files that explains the analytics
        and data available via other endpoints. These reports are pre-defined. As a user you can
        request the download of the file but you cannot define the content yet.

        Params:
                ALL PARAMS REQUIRED:

                reportType: example => 'climate'
                scenarioCategory: example => 'NGFS3'
                reportFormat: example => 'pdf'
                entities: example => [{"entityId": "CN46262PC"]

            Sample Json Request:

                    {
                        "reportType": "climate",
                        "reportFormat": "pdf",
                        "scenarioCategory": ["NGFS3"],
                        "entities": [
                            {
                                "entityId": "CN46262PC"
                            }
                        ]
                    }
        """
        #error handle entities variable
        if isinstance(entities, dict):
            for key, value in entities.items():
                if not isinstance(key,str) or not isinstance(value,str):
                    print("Error: you need to either feed a dictionary of 'EntityID' as key and an EDFX Qualified ID as the value." )
                    return None
            entities = [entities]

            # Check if entities is a list of dictionaries with the key "entityId"
        if not isinstance(entities, list) or not all(isinstance(e, dict) and "entityId" in e for e in entities):
            print("Error: entities parameter must be a list of dictionaries with an 'entityId' key")
            return None

        endpoint = "/edfx/v1/reports"
        url= urljoin(self.base_url, endpoint)
        params = {
            "reportType": reportType,
            "reportFormat": reportFormat,
            "scenarioCategory": scenarioCategory,
            "entities": entities
        }
        headers = self.EDFXHeaders()['JSONBasic']['headers']
        response = requests.post(url, json=params, headers=headers)
        return response.json()

    def EDFXTemplateDownload(self, financialtemplate = 'Universal', output_format = 'Pandas'):


        """
        Specify what template you'd like to retrieve and the output format you'd like to use.

        Proper FinancialTemplate options: FinancialTemplate.UNIVERSAL, FinancialTemplate.BANK
        Proper OutputFormat: OutputFormat.PANDAS, OutputFormat.EXCEL, OutputFormat.CSV

        """
        financialtemplate = financialtemplate.title()
        output_format = output_format.title()

        if financialtemplate == FinancialTemplate.UNIVERSAL.value:
            endpoint = '/edfx/v1/entities/financials/template/universal'
        elif financialtemplate == FinancialTemplate.BANK.value:
            endpoint = '/edfx/v1/entities/financials/template/bank'
        else:
            raise ValueError(f"Invalid financial template: {financialtemplate}")

        base = self.base_url
        url = urllib.parse.urljoin(base, endpoint)
        headers = self.EDFXHeaders()['JSONGet']['headers']
        response = requests.get(url, headers=headers)
        text = response.text
        try:
            # Convert text to a dataframe
            data = io.StringIO(text)
            df = pd.read_csv(data, sep=",")

        except Exception as e:
            print(f"Error: Unable to convert the response to a DataFrame/CSV. {e}")
            return None

        # Check OutputFormat
        if output_format == OutputFormat.PANDAS.value:
            return df
        elif output_format == OutputFormat.EXCEL.value:
            # You can change the file name as needed or even pass it as a parameter
            df.to_excel("SearchOutput.xlsx", index=False)
            print("Data saved to SearchOutput.xlsx")
            return None
        elif output_format == OutputFormat.CSV.value:
            df.to_csv('SearchOutput.csv',index=False)
            print('Data Saved to SearchOutput.csv')
            return None
        else:
            raise ValueError(f"Unsupported OutputFormat: {OutputFormat}")

    def EDFXModelInputs(self, uploadFilename: str, localFilename: str, largeFile:bool = False ) -> dict:

        """
        Allows the user to upload financials for either an existing BVDID or a company that is unknown to Orbis.

        The API responds with a processId, which can be used in the following ways to check the process status and retrieve the value.

        With the /processes/{processId}/status endpoint to access the status of the upload, when they are ready
        the processId can be used as per point 2 and 3 below

        In the /pds, /pds/riskcalc, /pds/creditedge endpoints as value for the parameter processId  Using it to access the PD, implied ratings, etc.
        for all the companies in the uploaded file.

        By combining the entityIdentifier provided as input with the processid
        as follows: {entityIdentifiier}-{processId}. Using it as the identifier for the PD, trade credit limits, etc.,
        endpoints to access the metrics calculated using the information uploaded for a subset of the companies in the
        uploaded file (See Retrieving PD values page for more information).

        If a process is started the method will return a dict containing processId and uploadLink

        """
        ## call model input profile
        endpoint = "/edfx/v1/entities/modelInputs"
        url = urljoin(self.base_url, endpoint)
        payload = "-----011000010111000001101001\r\nContent-Disposition: form-data; name=\"uploadFilename\"\r\n\r\n" + uploadFilename + "\r\n-----011000010111000001101001\r\nContent-Disposition: form-data; name=\"largeFile\"\r\n\r\ntrue\r\n-----011000010111000001101001--\r\n\r\n"
        headers = self.EDFXHeaders()['ModelInputsProcess']['headers']
        response = requests.post(url, data=payload, headers=headers)

        if response.status_code == 200:
            payload = response.json()
            process_id = payload['processId']
            upload_link = payload['uploadLink']

            # print('upload_link: ', upload_link)
            # print('process_id: ', process_id)

            upload_headers = self.EDFXHeaders(process_id=process_id)['ModelInputsUploadProcess']['headers']

            #Upload local large file using the process id and upload link retrieved from last step.
            with open(localFilename, 'rb') as file:
                response = requests.put(upload_link, headers=upload_headers, data=file)
                if response.status_code == 200:
                    print(response.status_code)
                    return payload
                else:
                    print(response.text)

    def EDFXModelInputsGetStatus(self, processID: str) -> dict:
        """
        Gets the status of a process that was started with the EDFXModelInputs() method
        If the process is still running the method will return {'status': 'Processing'}
        """
        endpoint = f"/edfx/v1/processes/{processID}/status"
        url = urljoin(self.base_url, endpoint)
        headers = self.EDFXHeaders()['JSONGet']['headers']
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            status = response.json()
            print(status)
            return status
        else:
            print(response.status_code)
            print(response.text)

    def EDFXModelInputsGetFiles(self, processID: str) -> dict:
        """
        Gets the output/files of a process that was started with the EDFXModelInputs() method

        Response

        The JSON format response will contain a download link URL. A GET request with this URL will
        return the results for the asynchronous request in JSON format. The response from the
        download link will have the same structure as the equivalent synchronous data request.

        """
        endpoint = f"/edfx/v1/processes/{processID}/files"
        url = urljoin(self.base_url, endpoint)
        headers = self.EDFXHeaders()['JSONGet']['headers']
        response = requests.get(url, headers=headers)
        download_link = response.json()['downloadLink']
        file = requests.get(download_link)
        return json.loads(file.content)

    def EDFXRetrievinglimtsfortradecredit(self, entities:list[dict], startDate:str=None, endDate:str=None)->dict:

        """
        Required Params:
        entities.

        Use the /tools/creditLimit endpoint to access estimated limits for trade credit.
        For each company except for financial institutions, we provide trade credit limits based on conservative,
        balanced, and aggressive risk appetites. Limits provide corporate users with guidance on how much trade
        credit to extend to a firm, and when to consider being paid upfront.

        Limits are only implemented for entities that we have information on, either from Orbis or uploaded as custom
        financials. It is not possible to calculate limits based on custom PD inputs.
        """

        if isinstance(entities, dict):
            for key, value in entities.items():
                if not isinstance(key,str) or not isinstance(value,str):
                    print("Error: you need to either feed a dictionary of 'EntityID' as key and an EDFX Qualified ID as the value." )
                    return None
            entities = [entities]

            # Check if entities is a list of dictionaries with the key "entityId"
        if not isinstance(entities, list) or not all(isinstance(e, dict) and "entityId" in e for e in entities):
            print("Error: entities parameter must be a list of dictionaries with an 'entityId' key")
            return None

        params = {
                    "startDate": startDate,
                    "endDate": endDate,
                    "entities": entities
                    }
        endpoint = "/edfx/v1/tools/tradeCreditLimit"
        url = urljoin(self.base_url, endpoint)
        headers = self.EDFXHeaders()["JSONBasic"]['headers']
        response = requests.post(url, json=params, headers=headers)
        return response.json()

    def EDFXRetrievingpeergroups_IDS(self,peerRegion:str, ownershipType:str, industryClassification:str=None, industryCode:str=None,
                                     country:str=None) -> dict:

        """
        See Peer Groups - country to region mapping for more information:

        Params: peerRegion: required
                ownershipType: required
                industryClassification: required
                industryCode: required
                country, Not required.

            Sample JSON request:

                                {
                                "peerRegion":"WESTEUR",
                                "industryClassification":"NDY",
                                "industryCode":"N55",
                                "ownershipType":"UNLISTED"
                                }

        """

        params = {"peerRegion":peerRegion,
                  "ownershipType":ownershipType,
                  "industryClassification":industryClassification,
                  "industryCode":industryCode,
                  "country":country
                  }

        endpoint = "/edfx/v1/entities/peers/id"
        url = urljoin(self.base_url, endpoint)
        headers = self.EDFXHeaders()["JSONBasic"]['headers']
        response = requests.post(url, json=params, headers=headers)
        return response.json()

    def EDFXRetrievingpeergroups_Metrics(self, peerId:str, metrics:list[str], variables:list[str]=None,startDate:str=None,
                                         endDate:str=None) -> dict:


        """
            Use this endpoint to retrieve metrics about variables (e.g. PD) within the peer group.

            Method: POST

            Params peerId: Required
                   metrics: Required
                   variables:Required
                   startDate: Required
                   endDate: Required

            Sample Payload:
                            payload = {
                                "peerId": "832ec933-28e0-47c9-85a2-a8b5c2ca02b5",
                                "variables": ["annualizedcumulativepd1y"],
                                "metrics": ["P025", "P050"],
                                "startDate": "2022-11-01",
                                "endDate": "2023-01-01"
                            }


        """
        params = {
                    "peerId": peerId,
                    "variables": variables,
                    "metrics": metrics,
                    "startDate": startDate,
                    "endDate": endDate
                }

        headers = self.EDFXHeaders()["JSONBasic"]["headers"]
        endpoint = "/edfx/v1/entities/peers/metrics"
        url = urljoin(self.base_url, endpoint)
        response = requests.post(url, json=params, headers=headers)
        return response.json()

    def EDFXRetrievingpeergroups_Percentile(self,peerId:str,variableName:list[str], value:list[float]) -> dict:


        """
            For a specific variable, use this endpoint to retrieve the percentile of a given value.

            Use this endpoint to retrieve metrics about variables (e.g. PD) within the peer group.

            Params: peerId, variableName, value all required

            sample payload:

            payload = {
                "peerId": "832ec933-28e0-47c9-85a2-a8b5c2ca02b5",
                "request": {
                    "variableName": ["annualizedcumulativepd1y"],
                    "value": [0.023]
                }
            }

        """
        params = {
                "peerId": peerId,
                "request":
                        {
                        "variableName": variableName,
                        "value": value
                        }
                    }
        headers = self.EDFXHeaders()["JSONBasic"]["headers"]
        endpoint = "/edfx/v1/entities/peers/percentile"
        url = urljoin(self.base_url, endpoint)
        response = requests.post(url, json=params, headers=headers)
        return response.json()

    def EDFXRetrievingpeergroups_Metadata(self, peerId:str) -> dict:

        """
        Use this endpoint to retrieve information about a peer group.

        Sample JSON Request


                {
                    "peerId":"6cef0ad5-5f1b-40bc-85a9-0a071143fd3b"
                }
        """


        params =    {
                    "peerId":peerId
                    }
        headers = self.EDFXHeaders()["JSONBasic"]['headers']
        endpoint = "/edfx/v1/entities/peers/metadata"
        url = urljoin(self.base_url, endpoint)
        response = requests.post(url, json=params, headers=headers)
        return response.json()

    def EDFXRetrievingpeergroups_Recommended(self,industryClassification:str,industryCode:str, ownershipType:str, country:str)->dict:

        """
        Params Required:

            industryClassification
            industryCode
            ownershipType
            country

            Sample JSON request

                    {
                    "industryClassification":"NDY",
                    "industryCode":"N17",
                    "ownershipType":"UNLISTED",
                    "country":"USA"
                    }

        Response Important Note:

        Access the peer group ID that Moody's Analytics recommends as most appropriate according to both the criteria in the
        request and some pre-set criteria. The pre-set criteria currently in place is:

            - the recommended peer groups always include 10 or more constituents.

        Given the Country, Industry and Ownership type in the request, this endpoint only returns the Country level peer group
        that fits the criteria above; else the Region level peer group is looked up, and if that is not fitting the criteria
        either then the Global-wide peer group is returned as the recommended one. In many cases, this response is the
        same as /entity/peer/id.

        """
        params =    {
                    "industryClassification":industryClassification,
                    "industryCode":industryCode,
                    "ownershipType":ownershipType,
                    "country":country
                    }

        headers = self.EDFXHeaders()["JSONBasic"]['headers']
        endpoint = "/edfx/v1/entities/peers/id/recommended"
        url = urljoin(self.base_url, endpoint)
        response = requests.post(url, json=params, headers=headers)
        return response.json()

    def EDFXRetrievingpeergroups_Constituents(self, peerId:str)->dict:

        """
        Required Param:

                peerId

            The ID of the peer group for which you want to get information such as
            - the number of companies in the peer group
            - the country, in ISO code standard
            - the industry, in NDY classification
            - whether the peer groups concerns listed or not listed companies

            The response is a pre-signed URL to the S3 bucket where the file with the constituents list is.

        """
        headers = self.EDFXHeaders()['JSONGet']['headers']
        endpoint = f"/edfx/v1/entities/peers/{peerId}/constituents"
        url = urljoin(self.base_url, endpoint)
        response = requests.get(url, headers=headers)
        return response.text

    def EDFXEarlyWarningScore(self, entities:list[dict[str,str]],asOfDate:str=None,prevAsOfDate:str=None,
                               targetPercentile:float=None)->list:
        """
        The riskCategory endpoint allows you to access an early warning category for a given company.
        This category is chosen based on changes in a company's risk, as indicated by its implied rating, and how it compares to its peers.
        We use a target PD percentile of the peer group to define a trigger level and determine if a company's PD is above this level.
        The trigger methodology uses a Bayesian-adjustment to leverage information from more broadly defined peer groups to control for situations
        when a granular peer group has insufficient data. Additionally, it includes a procyclical adjustment that takes into account the position of
        the industry in the credit cycle.

        Possible risk categories are:
            Severe: PD above triggerStable or worsening
            High: PD above triggerImproving
            Medium: PD at or below triggerWorsening
            Low: PD at or below triggerStable or improving

        Required Params:
            entities: A list of either:
                      - entityId. We support BvD IDs and CreditEdge PIDs and the API automatically determines which one is being used.
                      − A dictionary of:
                          1.entityId: A unique string used by requester to identify the entity.
                          2.pd: A PD value for the as of date. PDs should be a number between 0 and 1.
                          3.pdPrev: A PD value for a previous date (optional). PDs should be a number between 0 and 1.
                          4.peerId: A valid peer group identifier. This can be generated using the /edfx/v1/entities/peers/id endpoint
        Optional Params:
            asOfDate: Date of PD value in the format YYYY-MM-DD. If this is not provided, this will default to the 1st day of the current month.
            prevAsOfDate: Date of previous PD value in the format YYYY-MM-DD. This is used to calculate the change in implied rating
            targetPercentile: Target percentile used for trigger level. Percentiles are represented as numbers i.e. the 63rd percentile is represented as 0.63.
                              Values should be between 0.60 and 0.95 and given to two decimal place precision. This depends on the peer group chosen:
                                  1.Private company peer group 0.80
                                  2.Public financial company peer group 0.85
                                  3.Public nonfinancial company peer group 0.75


        """
        headers = self.EDFXHeaders()['JSONGet']['headers']
        endpoint = "/edfx/v1/tools/riskCategory"
        url = urljoin(self.base_url, endpoint)
        params = {
            "entities": entities
        }
        if asOfDate:
            params['asOfDate'] = asOfDate
        if prevAsOfDate:
            params['prevAsOfDate'] = prevAsOfDate
        if targetPercentile:
            params['targetPercentile'] = targetPercentile
        response = requests.post(url, headers=headers, json=params)
        return response.json()

    def EDFXEarlyWarningTriggers(self,peerId:str,endDate:str = None, startDate:str=None,targetPercentile:float=None)->dict:
        """
        The purpose of this endpoint to is provide a timeseries of triggers for a given peer group.

        Sample Json:

        {
            "peerId":"89a28088-7952-4b15-8ff3-f963e36d7cfd",
            "startDate":"2020-11-01",
            "endDate":"2021-01-01",
            "targetPercentile":0.80
        }

        """
        headers = self.EDFXHeaders()['JSONGet']['headers']
        endpoint = "/edfx/v1/tools/triggers"
        url = urljoin(self.base_url, endpoint)
        payload = {
                    "peerId": peerId,
                    "startDate": startDate,
                    "endDate": endDate,
                    "targetPercentile": targetPercentile
                    }
        response = requests.post(url, json=payload, headers=headers)
        return response.json()


    def EDFXRetrievingStatements(self, entities: list, asOfDate: str = None, endData: str = None) -> list:
        """
        Access a summary of the financial statement for entities we have data on.

        Required Params:
            entities: A list of either:
                      - entityId. We support BvD IDs and CreditEdge PIDs and the API automatically determines which one is being used.
                      - A dictionary of:
                          1.entityId: A unique string used by requester to identify the entity.
                          2.pd: A PD value for the as of date. PDs should be a number between 0 and 1.
                          3.pdPrev: A PD value for a previous date (optional). PDs should be a number between 0 and 1.
                          4.peerId: A valid peer group identifier. This can be generated using the /edfx/v1/entities/peers/id endpoint
        Optional Params:
            asOfDate: If provided, generates a history of limit values to be generated in the format YYYY-MM-DD.
            endData: The date of the limit you are retrieving in the format YYYY-MM-DD.


        """
        headers = self.EDFXHeaders()['JSONGet']['headers']
        endpoint = "/edfx/v1/entities/financials/statements"
        url = urljoin(self.base_url, endpoint)
        params = {
            "entities": entities
        }
        if asOfDate:
            params['asOfDate'] = asOfDate
        if endData:
            params['endData'] = endData
        response = requests.post(url, headers=headers, json=params)
        return response.json()

    def EDFXRetrievingRatios(self, entities: list, asOfDate: str = None, endData: str = None) -> list:
        """
        Access key financial ratios for entities we have data on.

        Required Params:
            entities: A list of either:
                      - entityId. We support BvD IDs and CreditEdge PIDs and the API automatically determines which one is being used.
                      - A dictionary of:
                          1.entityId: A unique string used by requester to identify the entity.
                          2.pd: A PD value for the as of date. PDs should be a number between 0 and 1.
                          3.pdPrev: A PD value for a previous date (optional). PDs should be a number between 0 and 1.
                          4.peerId: A valid peer group identifier. This can be generated using the /edfx/v1/entities/peers/id endpoint
        Optional Params:
            asOfDate: If provided, generates a history of limit values to be generated in the format YYYY-MM-DD.
            endData: The date of the limit you are retrieving in the format YYYY-MM-DD.


        """
        headers = self.EDFXHeaders()['JSONGet']['headers']
        endpoint = "/edfx/v1/entities/financials/ratios"
        url = urljoin(self.base_url, endpoint)
        params = {
            "entities": entities
        }
        if asOfDate:
            params['asOfDate'] = asOfDate
        if endData:
            params['endData'] = endData
        response = requests.post(url, headers=headers, json=params)
        return response.json()

    def EDFXRetrievingRatioCalculations(self, statements: list) -> dict:
        """
        Calculate key ratios using your own financial statement inputs

        Required Params:
            statements: A list of statements. Each statement is a list of financial statement items
            - financialStatementDate
            - ebitda
            - financeCosts
            - grossIncome
            - netIncome
            - netSales
            - netWorth
            - profitBeforeTaxesAndExtraordinaryExpenses
            - shortTermDebt
            - totalAssets
            - totalAssetsPreviousYear
            - totalCostOfGoodsSold
            - totalCurrentAssets
            - totalCurrentLiabilities
            - totalInventory
            - totalInventoryPreviousYear
            - totalLiabilities
            - totalLongTermDebt
            All items are optional. Missing values should not be sent and resulting ratios will be calculated as NA


        """
        headers = self.EDFXHeaders()['JSONGet']['headers']
        endpoint = "/edfx/v1/entities/financials/ratios/calculate"
        url = urljoin(self.base_url, endpoint)
        params = {
            "statements": statements
        }
        response = requests.post(url, headers=headers, json=params)
        return response.json()

    def EDFXRetrievingSmartProjection(self, entities: list, projectionYears: int, assumptions: dict,
                                      resultDetail: bool = False, inputDetail: bool = False, includeRatios: bool = False) -> dict:
        """
        Calculate key ratios using your own financial statement inputs

        Required Params:
            entities: A list of either:
                      - entityId. We support BvD IDs and CreditEdge PIDs and the API automatically determines which one is being used.
                      - A dictionary of:
                          1.entityId: A unique string used by requester to identify the entity.
                          2.pd: A PD value for the as of date. PDs should be a number between 0 and 1.
                          3.pdPrev: A PD value for a previous date (optional). PDs should be a number between 0 and 1.
                          4.peerId: A valid peer group identifier. This can be generated using the /edfx/v1/entities/peers/id endpoint
            projectionYears: The number of years the projection is requested to cover. This must be whole years.
            assumptions: Dict of assumtions, for example:
                         {
                            "sales": {
                                "valuesType": "variable",
                                "frequency": "annual",
                                "value": [0.9, 1]
                            },
                            "newDebt": {
                                "useProportion": {
                                    "cash": 0.5,
                                    "inventory": 0.25,
                                    "fixedAssets": 0.25
                                },
                                "percentage": 0.03,
                                "maturity": 60,
                                "debtStart": 3,
                                "interestRate": 0.03
                            },
                            "dividendPayoutRatio": {
                                "valuesType": "fixed",
                                "absChange": False,
                                "value": 0.11
                            }
                        }
            resultDetail: Should result detais be included in output
            inputDetail: Should input details be included in output
            includeRatios: Should ratios be included in output


        """
        headers = self.EDFXHeaders()['JSONGet']['headers']
        endpoint = "/edfx/v1/entities/financials/smartProjection"
        url = urljoin(self.base_url, endpoint)
        params = {
            "entities": entities,
            "projectionYears": projectionYears,
            "assumptions": assumptions,
            "includeDetail": {
                "resultDetail": resultDetail,
                "inputDetail": inputDetail,
                "includeRatios": includeRatios
            }
        }
        response = requests.post(url, headers=headers, json=params)
        return response.json()

    def EDFXRetrievingScenarioConditionPDs(self, includeScenario: dict, entityId: str, projectionYears: int = None, asOfDate: str = None, pd_at_time_t: float = None, pdLag: float = None,
                                                 primaryCountry: str = None, primaryIndustryClassification: str = None, primaryIndustry: str = None) -> list:

        """
        The endpoint provides the capability to observe PD stress evaluations aligned with Moody's economics scenarios.
        You have the option to view the applied stress conditions for three distinct cases:
        1- Orbis Entities: This refers to predefined entities available within the system.
        2- Custom Entities from /modelInputs: users can apply stress conditions to custom entities they have previously established using the /modelInputs feature.
        3- On-Demand Stress Testing Calculation: you have the flexibility to directly provide the necessary inputs for Stress PD calculations through the API;
        you can provide your own credit risk metric, which will be stressed according to Moody’s Analytics Standard Global Scenarios.
        This empowers you to perform stress testing calculations as needed.

        Required Params:
            includeScenario: The compilation of scenarios for which the user seeks to view PD results. Possible values: "Baseline", "S1", "S2", "S3", "S4".
            entityId: The ID (BVD ID or PID) of the entities of interest. This should accept both the identifier mentioned above and custom companies.
        Optional Params:
            asOfDate: If provided, generates a history of limit values to be generated in the format YYYY-MM-DD.
            projectionYears: Parameter to define the number of years of the projection. Ex. If the user selects 3, the response should only show 3 years of projections. Possible values: 1 to 5. Defaults to 5 if not provided.
            pd_at_time_t: The PD at time t. This is the PD to which the macro stress test will be applied in on demand calculations. This input is only needed for Case 3.
            pdLag: The PD at time t - 3 months. This input is only needed for Case 3. Only relevant if pd is also provided.
            primaryCountry: The primary country for the entity's economic activity. Valid values are the three-letter country codes from ISO 3166. This input is only needed for Case 3.
            primaryIndustryClassification: The primary industry code for the entity's economic activity. Possible values: NDY. Preset value: NDY. This input is only needed for Case 3
            primaryIndustry: The primary industry code for the entity's economic activity. Possible values: NDY codes. This input is only needed for Case 3.

        Sample response:

        """
        headers = self.EDFXHeaders()['JSONGet']['headers']
        endpoint = "/edfx/v1/tools/scenarioConditionedPds"
        url = urljoin(self.base_url, endpoint)
        params = {
            "includeScenario": includeScenario,
            "entityId": entityId
        }
        if asOfDate:
            params['asOfDate'] = asOfDate
        if projectionYears:
            params['projectionYears'] = projectionYears
        if pd_at_time_t:
            params['pd_at_time_t'] = pd_at_time_t
        if pdLag:
            params['pdLag'] = pdLag
        if primaryCountry:
            params['primaryCountry'] = primaryCountry
        if primaryIndustryClassification:
            params['primaryIndustryClassification'] = primaryIndustryClassification
        if primaryIndustry:
            params['primaryIndustry'] = primaryIndustry
        response = requests.post(url, headers=headers, json=params)
        return response.json()

    def EDFXCalculatingLGD(self, entities: list) -> dict:
        """
        Use this endpoint to calculate LGD in EDF-X API, the calculations are on-demand and use Loss Given Default 4.0 (LGD 4.0) model.
        Suggest Edits The main metrics currently accessible are:
        LGD (Loss Give Default) EL (Expected Loss) EL IR (Expected Loss Implied Rating)

        Required Params:
            entities: A list of entities.

        Examples:
        Minimum Inputs with Company & Loan Inputs
        [
            {
                "entityId": "Custom Company",
                "country": "USA",
                "primaryIndustry": "N02",
                "primaryIndustryClassification": "NDY",
                "loans": [
                    {
                        "loanParameters": {
                            "loanId": "loan1",
                            "loanName": "loan1",
                            "asOfDate": "2012-12-01",
                            "instrumentType": "Senior Bond",
                            "securedUnsecured": "Unsecured",
                            "recoveryCalculationMode": "Ultimate Recovery",
                            "capitalStructure": "Unknown"
                        },
                        "termStructureCumulativePd": { "cumulativePd1y": 0.0034 }
                    }
                ]
            }
        ]

        Full Inputs all company and Loan Information
        [
            {
                "entityId": "Custom Company",
                "country": "USA",
                "primaryIndustry": "N02",
                "primaryIndustryClassification": "NDY",
                "loans": [
                    {
                        "loanParameters": {
                            "loanId": "loan1",
                            "loanName": "loan1",
                            "asOfDate": "2012-12-01",
                            "exposure": 1000000,
                            "originationDate": "2022-12-31",
                            "maturityDate": "2025-06-30",
                            "exposureCurrency": "USD",
                            "instrumentType": "Senior Bond",
                            "securedUnsecured": "Unsecured",
                            "recoveryCalculationMode": "Ultimate Recovery",
                            "capitalStructure": "Unknown"
                        },
                        "termStructureCumulativePd": {
                            "cumulativePd1y": 0.0028,
                            "cumulativePd2y": 0.0058,
                            "cumulativePd3y": 0.0089,
                            "cumulativePd4y": 0.012,
                            "cumulativePd5y": 0.0152,
                            "cumulativePd6y": 0.0184,
                            "cumulativePd7y": 0.0216,
                            "cumulativePd8y": 0.0248,
                            "cumulativePd9y": 0.0279,
                            "cumulativePd10y": 0.0311
                        }
                    }
                ]
            }
        ]

        Full Inputs all company, Loan Information, and Collateral
        [
            {
                "entityId": "Custom Company",
                "country": "USA",
                "primaryIndustry": "N02",
                "primaryIndustryClassification": "NDY",
                "loans": [
                    {
                        "loanParameters": {
                            "loanId": "1a19c5a4-67c8-441d-b3be-7fd150ab82fb",
                            "loanName": "",
                            "asOfDate": "2023-06-01",
                            "originationDate": "2022-06-01",
                            "maturityDate": "2023-06-01",
                            "exposure": 1000000,
                            "exposureCurrency": "USD",
                            "instrumentType": "Term Loan",
                            "securedUnsecured": "Secured",
                            "recoveryCalculationMode": "Post-default Price",
                            "capitalStructure": "Unknown",
                            "loanScorecard": {
                                "loanScorecardId": "2b77f0d7-b0e4-4dbc-844d-aabb4376a688",
                                "blanketLien": "No",
                                "collateral": [
                                    {
                                        "customCollateralId": "1234",
                                        "loanId": "1a19c5a4-67c8-441d-b3be-7fd150ab82fb",
                                        "collateralName": "",
                                        "collateralType": "Accounts Receivable",
                                        "amount": 100000,
                                        "questionAnswers": [
                                            {
                                                "name": "Standard Payment Terms",
                                                "value": "Not Available"
                                            },
                                            {
                                                "name": "Customer Concentration",
                                                "value": "Not Available"
                                            },
                                            {
                                                "name": "Customer Credit Quality",
                                                "value": "Not Available"
                                            },
                                            {
                                                "name": "Borrowing Base",
                                                "value": "Not Available"
                                            },
                                            {
                                                "name": "Report Frequency",
                                                "value": "Not Available"
                                            },
                                            {
                                                "name": "Field Audit Frequency",
                                                "value": "Not Available"
                                            },
                                            {
                                                "name": "Dominion of Funds",
                                                "value": "Not Available"
                                            }
                                        ]
                                    }
                                ],
                                "guarantee": None,
                                "lgdQualitativeFactors": {
                                    "enterpriseValuation": None,
                                    "covenantStructure": None
                                }
                            }
                        },
                        "termStructureCumulativePd": {
                            "pdType": "pit",
                            "cumulativePd1y": 0.0027,
                            "cumulativePd2y": 0.0056,
                            "cumulativePd3y": 0.0087,
                            "cumulativePd4y": 0.0118,
                            "cumulativePd5y": 0.015,
                            "cumulativePd6y": 0.0181,
                            "cumulativePd7y": 0.0213,
                            "cumulativePd8y": 0.02439,
                            "cumulativePd9y": 0.0275,
                            "cumulativePd10y": 0.03062
                        }
                    }
                ]
            }
        ]

        """
        headers = self.EDFXHeaders()['JSONGet']['headers']
        endpoint = "/edfx/v1/entities/loans"
        url = urljoin(self.base_url, endpoint)
        params = {
            "entities": entities
        }
        response = requests.post(url, headers=headers, json=params)
        return response.json()

    def EDFXRetrievingLoanMedianCreditSpreads(self, currency: str, referenceRate: str, rating: str, startDate: str, endDate: str, tenor: int) -> dict:
        """
        Use this endpoint to retrieve Moody's Implied Ratings Median Credit Spreads (MIR Credit Spreads) for a specific date and rating.
        Provide information about the counterparty's loan(s) to calculate Loss Given Default metrics.
        The calculations leverage the Loss Given Default 4.0 (LGD 4.0) model. In this same endpoint you can also use Moody’s Loan Scorecard.

        Required Params:
        currency
        referenceRate
        rating
        startDate
        endDate
        tenor

        """
        headers = self.EDFXHeaders()['JSONGet']['headers']
        endpoint = "/edfx/v1/tools/loanSpreads"
        url = urljoin(self.base_url, endpoint)
        params = {
            "spreadCalculation": {
                    "currency": currency,
                    "referenceRate": referenceRate,
                    "rating": rating,
                    "startDate": startDate,
                    "endDate": endDate,
                    "tenor": tenor
            }
        }
        response = requests.post(url, headers=headers, json=params)
        return response.json()

    def EDFXDeteriorationProbability(self, entities:list[dict[str,str]],asyncResponse:bool=False,
                                     startDate:str=None, endDate:str=None,
                                     historyFrequency:str='monthly'):
        """
        Use this endpoint to access the latest available Deterioration Probability for the entity.

        min sample request:
        {
            "asyncResponse":false,
            "entities":[
                {
                    "entityId":"US942404110"
                }
            ]
        }
        """
        headers = self.EDFXHeaders()['JSONBasic']['headers']
        endpoint = "/edfx/v1/tools/deteriorationProbability"
        url = urljoin(self.base_url, endpoint)
        params = {
                    "startDate": startDate,
                    "endDate": endDate,
                    "historyFrequency": historyFrequency,
                    "asyncResponse": asyncResponse,
                    "entities": entities
                            }

        params = { key:value for key,value in params.items() if value is not None}
        response = requests.post(url, headers=headers, json=params)
        return response.json()

    def EDFXMoodysRating(self,entities:list[dict[str,str]],ratingType:str="SRA",historyFrequency:str="monthly",
                         asyncResponse:bool=False,startDate:str=None, endDate:str=None,):

        """
        Use this endpoint to access the latest value available for Moody's Rating:

        SRA rating.
        In this payload it can handle ratingType as a param

        Sample Request:

                {
                "ratingType":"SRA",
                "entities":[
                    {
                        "entityId":"US942404110"
                    }
                ]
                }
        """
        headers = self.EDFXHeaders()['JSONBasic']['headers']
        endpoint = "/edfx/v1/entities/moodysRating"
        url = urljoin(self.base_url, endpoint)
        params = {
                    "startDate": startDate,
                    "endDate": endDate,
                    "historyFrequency": historyFrequency,
                    "asyncResponse": asyncResponse,
                    "ratingType": ratingType,
                    "entities": entities
                }

        params = { key:value for key,value in params.items() if value is not None}
        response = requests.post(url, json=params, headers=headers)
        return response.json()

    def EDFXMoodysBondImpliedRating(self,entities:list[dict[str,str]],historyFrequency:str="monthly",
                                    asyncResponse:bool=False,startDate:str=None, endDate:str=None):

        """
        This endpoint give access to the latest Bonds-implied Rating for the firm.
        Sample JSON Request:

        This endpoint Cannot handle ratingType as a param

        {
        "entities":[
                        {
                            "entityId":"US942404110"
                        }
                    ]
                    }
        """
        headers = self.EDFXHeaders()['JSONBasic']['headers']
        endpoint = "/edfx/v1/entities/bonds"
        url = urljoin(self.base_url, endpoint)
        params = {
            "startDate": startDate,
            "endDate": endDate,
            "historyFrequency": historyFrequency,
            "asyncResponse": asyncResponse,
            "entities": entities
        }
        params = { key:value for key,value in params.items() if value is not None}
        response = requests.post(url, json=params, headers=headers)
        return response.json()

    def EDFXCDSImpliedRatings(self,entities:list[dict[str,str]],historyFrequency:str="monthly",
                              asyncResponse:bool=False,startDate:str=None, endDate:str=None):

        """
        Access the latest CDS-Implied PD and IR for the firm under analysis using this endpoint.

        {
        "entities":[
            {
                "entityId":"34537A"
            }
        ]
        }
        """

        headers = self.EDFXHeaders()['JSONBasic']['headers']
        endpoint = "/edfx/v1/entities/cds"
        url = urljoin(self.base_url, endpoint)
        params = {
                    "startDate": startDate,
                    "endDate": endDate,
                    "historyFrequency": historyFrequency,
                    "asyncResponse": asyncResponse,
                    "entities": entities
                }
        params = { key:value for key,value in params.items() if value is not None}
        response = requests.post(url, json=params, headers=headers)
        return response.json()

    @staticmethod
    def EDFXExportData(df:pd.DataFrame, output_format:str, file_name:str):
        """
        This is how we can export the data either in a pandas, csv, or excel dataframe
        depending on what the user selects in their parse methods. 
        """
        if output_format == OutputFormat.PANDAS.value:
            return df

        elif output_format == OutputFormat.EXCEL.value:
            df.to_excel(f"{file_name}.xlsx", index=False)
            print(f"Data saved as {file_name}.xlsx")
        
        elif output_format == OutputFormat.CSV.value:
            df.to_csv(f"{file_name}.csv", index=False)
            print(f"Data Saved as {file_name}.csv")

        else:
            raise ValueError(f"Unsupported OutputFormat: {output_format}.")

    @staticmethod
    def EDFXSearchParse(jsonresponse:dict, output_format:str = "pandas", file_name="SearchOutput"):

        """
        Leverage recursive helper functions to parse data frame

        """
        output_format = output_format.title()
        try:

            if not isinstance(jsonresponse,dict) or not jsonresponse:
                print(f"The API did not return a valid response or data. Response Below:\n {jsonresponse}")
                return None
            else:
                flat_data = [flatten_dict(entity) for entity in jsonresponse['entities']]
                df = pd.DataFrame(flat_data)

        except Exception as e:
            print(f"Error: {str(e)}")
            print("An error occured while processing the API response.")
            return None
        
        return EDFXEndpoints.EDFXExportData(df, output_format, file_name)


    @staticmethod
    def EDFXBatchParse(batch:json, output_format:str = "pandas", file_name = "batchoutput"):
        """
        Parses the Json Batch output and transforms it to either a pandas dataframe, .csv, or .xlsx file.


        Params:
        - JSONB  EDFXBatchEntitySearch dictionary object: dict
        - output_format:str (your choice of either'Pandas', 'Excel', 'Csv'), where csv and excel options save
        to your local path.

        THIS WILL BREAK IF MOODYS ANALYTICS CHANGES THE EDFX BATCH OUTPUT RESPONSE
        RECALL:
        If you're using iterrows() with a pandas DataFrame, each row is a Series, and accessing its elements
        by column labels returns the values in those columns for the current row.

        """

        output_format = output_format.title()
        try:            
            if not isinstance(batch,dict) or not batch:

                print(f"The API did not return a valid response or data. Response Below:\n {batch}")
                return None
     
            else:

                df = pd.DataFrame(batch['entities'])
                #Extract national ID into separate columns (I can vectorize this but this is clearer)
                for index, row in df.iterrows():
                    # This is saying if the column name is present and if that column is a list object
                    if 'nationalId' in row and isinstance(row['nationalId'],list):
                        #supress FutureWarnings in this block
                        with warnings.catch_warnings():
                            warnings.simplefilter('ignore', category = FutureWarning)

                            # now iterate the values within the list
                            for item in row['nationalId']:
                                col_name = 'nationalId_'+ item['idName']
                                # this is faster than .loc[index,col]
                                df.at[index, col_name] = item['idValue']

                # drop the original nationalId col if it exists
                if 'nationalId' in df.columns:
                    df.drop(columns=['nationalId'], inplace=True)

        except Exception as e:
            print(f"Error: {str(e)}")
            print("An error occurred while processing the API response.")
            return None   

        return EDFXEndpoints.EDFXExportData(df, output_format, file_name)

    @staticmethod
    def EDFXPDParse(data: dict, TimeSeries: bool = True, output_format:str = "pandas", file_name = "pd"):

        """
        Parses the provided JSON data into a pandas DataFrame.

        Parameters:
        - data (dict): The JSON data to be parsed.
        - TimeSeries: If set to True returned DataFrame will have datetime index

        Returns:
        - DataFrame: A pandas DataFrame
        """

        output_format = output_format.title()
        try:
            # Try seeing if there is an error.
            if not isinstance(data,dict) or not data:
                print(f"The API did not return a valid response or data. Response Below:\n {data}")
                return None
            # else perform the parse.
            else:
                flat_data = []
                for entity in data['entities']:
                    if 'history' in entity:
                        entity_data = flatten_dict({
                            k: v for k, v in entity.items()
                            if k != 'history' and
                            k not in entity['history'][0]
                        })
                        for history_record in entity['history']:
                            flat_data_record = entity_data.copy()
                            flat_data_record.update(flatten_dict(history_record))
                            flat_data.append(flat_data_record)
                    else:
                        # if there is no history you can't append the history. 
                        flat_data.append(flatten_dict(entity))

                df = pd.DataFrame(flat_data)
                if TimeSeries:
                    df.set_index(pd.to_datetime(df['asOfDate']), inplace=True)

        # print API exception if a global error occurs            
        except Exception as e:
            print(f"Error: {str(e)}")
            print("An error occurred while processing the API response.")
            return None   
        
        return EDFXEndpoints.EDFXExportData(df, output_format, file_name)

    @staticmethod
    def EDFXPD_DriversParse(json:dict, output_format:str = 'pandas', file_name="pdHistory"):

        """
        This parses, public, private, and multiple public and private Json Responses
        """
        # Extract data for all entities
        output_format = output_format.title()
        try:
            if not isinstance(json,dict) or not json:
                print(f"The API did not return a valid response or data. Response Below:\n {json}")
                return None
            
            else:
                all_ratios = []
                for entity in json['entities']:
                    all_ratios.extend(PDDrivers_extract_ratios(entity))

                # Convert the list of dictionaries into a DataFrame
                df = pd.DataFrame(all_ratios)

        except Exception as e:
            print(f"Error: {str(e)}")
            print("An error occurred while processing the API response.")
            return None
        
        return EDFXEndpoints.EDFXExportData(df, output_format, file_name)

    @staticmethod
    def EDFXParseTradeCredit(json:dict, output_format:str = "pandas", file_name = "TradeCredit"):

        """
        Parses the response of the EDFXRetrievinglimtsfortradecredit method to extract trade credit information
        and returns either Pandas DF, CSV, or Excel file.

        Parameters:
        - response (dict): The response object returned by EDFXRetrievinglimtsfortradecredit method
        - output_format: Pandas DataFrame, Excel, or Csv

        Returns:
        - DataFrame: A DataFrame with trade credit information
        """
        output_format = output_format.title()
        try:
            if isinstance(json, dict) or not json:
                print(f"The API did not return a valid response or data. Response Below:\n {json}")
                return None
            else:
                # Extract the list of entities
                entities = json.get("entities", [])
                # Create an empty dataframe to store all entities' data
                full_df = pd.DataFrame()
                # Create an empty list to store entityIds without credit information
                missing_data_ids = []
                # Loop through each entity and extract relevant data
                for entity_data in entities:
                    credit_limits = entity_data.get("creditLimits", [])
                    if credit_limits:
                        df = pd.DataFrame(credit_limits)
                        df["entityId"] = entity_data.get("entityId")

                        # Reordering the columns to have 'entityId' as the first column
                        cols = df.columns.tolist()
                        cols = [cols[-1]] + cols[:-1]
                        df = df[cols]

                        # Append to the main dataframe
                        full_df = pd.concat([full_df, df], ignore_index=True)
                    else:
                        missing_data_ids.append(entity_data.get("entityId"))

                # Print warning messages for entityIds without credit information
                for entity_id in missing_data_ids:
                    print(f"Unfortunately: {entity_id} has no credit information.")

        except Exception as e:
            print(f"Error: {str(e)}")
            print("An error occurred while processing the API response.")
            return None
        
        return EDFXEndpoints.EDFXExportData(full_df, output_format, file_name)

    @staticmethod
    def EDFXParsePeerGroupMetrics(json:dict, output_format='pandas', file_name = "PeerGroupMetrics"):

        """
        Parses the json of the EDFXRetrievingpeergroups_Metrics method to extract peer group metrics
        and return it as either a Pandas DataFrame, Excel or CSV file.

        Required Params:
        dictionary json response object and pandas Pd
        """
        output_format = output_format.title()
        try:
            if not isinstance(json, dict) or not json:
                print(f"The API did not return a valid response or data. Response Below:\n {json}")
                return None
            
            else:
                # Extract the list of results
                results = json.get("results", [])
                # Check if results are present
                if not results:
                    print(f"Unfortunately: No data found for peerId {json.get('peerId')}.")
                    return pd.DataFrame()
                # Create an empty dataframe to store all the data
                full_df = pd.DataFrame()
                # Loop through each result and extract relevant data
                for result_data in results:
                    as_of_date = result_data.get("asOfDate")
                    variable_name = result_data.get("variableName")
                    unit = result_data.get("unit")
                    currency = result_data.get("currency")
                    metric_list = result_data.get("metricList", [])
                    values = result_data.get("values", [])
                    # Convert metricList and values into a dictionary
                    data_dict = dict(zip(metric_list, values))
                    # Add other fields to this dictionary
                    data_dict.update({
                        "asOfDate": as_of_date,
                        "variableName": variable_name,
                        "unit": unit,
                        "currency": currency
                    })

                    # Convert the dictionary to DataFrame and append to the main dataframe
                    df = pd.DataFrame([data_dict])
                    full_df = pd.concat([full_df, df], ignore_index=True)

        except Exception as e:
            print(f"Error: {str(e)}")
            print("An error occurred while processing the API response.")
            return None
        
        return EDFXEndpoints.EDFXExportData(full_df, output_format, file_name)



    @staticmethod
    def EDFXParsePeerGroupPercentile(json:dict, output_format:str = 'Pandas', file_name = "PeerGroupPercentile"):

        """
        Parses the response of the EDFXRetrievingpeergroups_Percentile method to extract variable name and percentile
        and return it as a Pandas DataFrame.

        Parameters:

        - response (dict): The response object returned by EDFXRetrievingpeergroups_Percentile method
        - output_format: Pandas, Excel, Csv

        Returns:
        - DataFrame: A DataFrame with variable name and percentile information, Excel or Csv File.
        """
        output_format = output_format.title()
        try:

            if not isinstance(json, dict) or not json:
                print(f"The API did not return a valid response or data. Response Below:\n {json}")
                return None
            
            else:
                # get me the value for the 'results' key if it exists, else return me an empty list.
                #  Using "get" method with a default value avoids this potential KeyError issue thus is employed here. 
                results = json.get('results',[])
                if not results:
                    print(f"Unfortunately No data found for peerId {json.get('peerId')}.")
                    return pd.Dataframe()

                full_df = pd.DataFrame()
                for result_data in results:
                    variable_name = result_data.get("variableName")
                    percentile = result_data.get("percentile")
                    # Convert the extracted data into a dictionary
                    data_dict = {
                        "variableName": variable_name,
                        "percentile": percentile
                        }
                    # Convert the dictionary to DataFrame and append to the main dataframe
                    df = pd.DataFrame([data_dict])
                    full_df = pd.concat([full_df, df], ignore_index=True)

        except Exception as e:
            print(f"Error: {str(e)}")
            print("An error occurred while processing the API response.")
            return None
        
        return EDFXEndpoints.EDFXExportData(full_df, output_format, file_name)


    @staticmethod
    def EDFXParsePeerGroupMetaData(json:dict, output_format:str = 'Pandas', file_name = "PeerGroupMetaData"):
        """
        Parses the response of the EDFXRetrievingpeergroups_MetaData method to extract variable name and percentile
        and return it as a Pandas DataFrame.

        Parameters:

        - response (dict): The response object returned by EDFXRetrievingpeergroups_MetaData method
        - output_format: Pandas, Excel, Csv

        Returns:
        - DataFrame: A DataFrame with variable name and percentile information, Excel or Csv File.
        """
        output_format = output_format.title()
        try:
            if not isinstance(json, dict) or not json:
                print(f"The API did not return a valid response or data. Response Below:\n {json}")
                return None
            else:                               
                keys = ["peerId", "peerName", "count", "country", "region", "industryCode", "ownershipType"]
                # Check if peerId exists in the response
                if not json.get("peerId"):
                    print(f"Warning: No data found.")
                    # return pd.DataFrame()
                # Extract the metadata using list comprehension
                metadata = {key: json.get(key) for key in keys}
                # Convert the metadata dictionary into a DataFrame
                df = pd.DataFrame([metadata])

        except Exception as e:
            print(f"Error: {str(e)}")
            print("An error occurred while processing the API response.")
            return None
        
        return EDFXEndpoints.EDFXExportData(df, output_format, file_name)

    @staticmethod
    def EDFXParsePeerGroupRecommended(json:dict, output_format:str="Pandas", file_name="PeerGroupRecommended"):
        """
        Peer Group Parse.
        """
        output_format = output_format.title()

        try:
            if not isinstance(json, dict) or not json:
                print(f"The API did not return a valid response or data. Response Below:\n {json}")
                return None
            else:
                # Extracting the results: this is a list of a long dictionary so i'm just taking the entire dictionary
                results = json.get("results", [{}])[0]
                if not results:
                    print(f"Warning: No data found.")
                    return pd.DataFrame()
                # Convert the results dictionary into a list of tuples (key, value) format
                data = list(results.items())
                # Convert the list into a DataFrame
                df = pd.DataFrame(data, columns=['peerId_name', 'peerId_value'])

        except Exception as e:
            print(f"Error: {str(e)}")
            print("An error occurred while processing the API response.")
            return None
        
        return EDFXEndpoints.EDFXExportData(df, output_format, file_name)

    @staticmethod
    def EDFXEarlyWarningScoreParse(EDFXEarlyWarningScoreJSON:dict, output_format='Pandas',
                                   file_name = "EarlyWarningScore"):
        """
        Parses the provided JSON data into a pandas DataFrame.

        Parameters:
        - EDFXEarlyWarningScoreJSON (dict): The JSON data to be parsed.
        - output_format (str): The putput format, can be "Pandas", "Excel", "CSV".

        Returns:
        - DataFrame: A pandas DataFrame.
        """
        # catches errors.
        output_format = output_format.title()
        try:
            if not isinstance(EDFXEarlyWarningScoreJSON,dict) or not EDFXEarlyWarningScoreJSON:
                print(f"The API did not return a valid response or data. Response Below:\n {EDFXEarlyWarningScoreJSON}")
                return None
            else:
                 df = pd.DataFrame(EDFXEarlyWarningScoreJSON['entities'])

        except Exception as e:
            print(f"Error: {str(e)}")
            print("An error occurred while processing the API response.")
            return None
        
        return EDFXEndpoints.EDFXExportData(df, output_format, file_name)
        

    @staticmethod
    def EDFXEarlyWarningTriggersParse(TriggerJson:dict,output_format:str='pandas',file_name = 'EarlyWarningTrigger'):

        """
        Parses Triggers Dictionary
        """
        output_format = output_format.title()
        try:
            if not isinstance(TriggerJson,dict) or not TriggerJson:
                print(f"The API did not return a valid response or data. Response Below:\n {TriggerJson}")
                return None
            else:
                df = pd.DataFrame(TriggerJson['triggers'])
                # Convert 'asOfDate' column to datetime format
                df['asOfDate'] = pd.to_datetime(df['asOfDate'])
                # # Sort the DataFrame based on 'asOfDate'
                df = df.sort_values(by='asOfDate').reset_index(drop=True)
                # Check OutputFormat

        except Exception as e:
            print(f"Error: {str(e)}")
            print("An error occurred while processing the API response.")
            return None
        
        return EDFXEndpoints.EDFXExportData(df, output_format, file_name)

    @staticmethod
    def EDFXStatementsParse(StatementsJSON: dict, FormatType: str = 'Long', output_format='Pandas',
                            file_name = 'FinancialStatement'):
        """
        Parses the provided JSON data into a pandas DataFrame.

        Parameters:
        - data (dict): The JSON data to be parsed.
        - FormatType (str): The format to which the data should be parsed. Either "wide" or "long".

        Returns:
        - DataFrame: A pandas DataFrame in the specified format.
        """
        # catches errors.
        FormatType = FormatType.title()
        output_format = output_format.title()
        try:
            if not isinstance(StatementsJSON, dict) or not StatementsJSON:
                print(f"The API did not return a valid response or data. Response Below:\n {StatementsJSON}")
                return None

            # Check for error response in JSON
            elif 'message' in StatementsJSON:
                print(f"Error in received data: {StatementsJSON['message']}")
                return None
            # Make sure 'entities' key exists in StatementsJSON
            elif 'entities' not in StatementsJSON:
                raise ValueError("The provided data does not contain 'entities'. Ensure the correct data format.")
            else:
                if FormatType not in ('Long', 'Wide'):
                    raise ValueError("Invalid FormatType provided. Choose either 'Wide' or 'Long'.")
                # Build Out
                flat_data = []
                for entity in StatementsJSON['entities']:
                    if FormatType == 'Long':
                        for statement in entity['statements']:
                            # gives me key,value pairs as dictionary elements within the list that are not nested
                            flat_data.append(filter_out_list_and_dict(entity))
                            #flat_data[-1] maps to the last element (a dictionary) in the flat_data list and updates
                            # that element
                            flat_data[-1].update(filter_out_list_and_dict(statement, 'statement'))
                            flat_data[-1].update(filter_out_list_and_dict(statement['balanceSheet'], 'balanceSheet'))
                            flat_data[-1].update(filter_out_list_and_dict(statement['incomeStatement'], 'incomeStatement'))
                    elif FormatType == 'Wide':
                        flat_data.append(filter_out_list_and_dict(entity))
                        for statement in entity['statements']:
                            flat_data[-1].update(filter_out_list_and_dict(statement, f'{statement["financialStatementDate"]}_statement'))
                            flat_data[-1].update(filter_out_list_and_dict(statement['balanceSheet'], f'{statement["financialStatementDate"]}_balanceSheet'))
                            flat_data[-1].update(filter_out_list_and_dict(statement['incomeStatement'], f'{statement["financialStatementDate"]}_incomeStatement'))

                df = pd.DataFrame(flat_data)

        except Exception as e:
            print(f"Error: {str(e)}")
            print("An error occurred while processing the API response.")
            return None
        
        return EDFXEndpoints.EDFXExportData(df, output_format, file_name)

    @staticmethod
    def EDFXRatiosParse(RatiosJSON: dict, FormatType: str = 'Long', output_format='Pandas',
                        file_name = "FinancialRatios"):
        """
        Parses the provided JSON data into a pandas DataFrame.

        Parameters:
        - data (dict): The JSON data to be parsed.
        - FormatType (str): The format to which the data should be parsed. Either "wide" or "long".

        Returns:
        - DataFrame: A pandas DataFrame in the specified format.
        """
        # catches errors.
        FormatType = FormatType.title()
        output_format = output_format.title()

        try:
            if not isinstance(RatiosJSON, dict) or not RatiosJSON:
                print(f"The API did not return a valid response or data. Response Below:\n {RatiosJSON}")
                return None
            # Make sure 'entities' key exists in StatementsJSON
            elif 'entities' not in RatiosJSON:
                raise ValueError("The provided data does not contain 'entities'. Ensure the correct data format.")

            elif FormatType not in ('Long', 'Wide'):
                raise ValueError("Invalid FormatType provided. Choose either 'Wide' or 'Long'.")
            else:
        # Build Out
                flat_data = []
                for entity in RatiosJSON['entities']:
                    if FormatType == 'Long':
                        for ratio in entity['ratios']:
                            flat_data.append(filter_out_list_and_dict(entity))
                            flat_data[-1].update(filter_out_list_and_dict(ratio['leverage'], 'leverage'))
                            flat_data[-1].update(filter_out_list_and_dict(ratio['liquidity'], 'liquidity'))
                            flat_data[-1].update(filter_out_list_and_dict(ratio['operational'], 'operational'))
                            flat_data[-1].update(filter_out_list_and_dict(ratio['profitability'], 'profitability'))
                    elif FormatType == 'Wide':
                        flat_data.append(filter_out_list_and_dict(entity))
                        for ratio in entity['ratios']:
                            flat_data[-1].update(filter_out_list_and_dict(ratio['leverage'], f'{ratio["financialStatementDate"]}_leverage'))
                            flat_data[-1].update(filter_out_list_and_dict(ratio['liquidity'], f'{ratio["financialStatementDate"]}_liquidity'))
                            flat_data[-1].update(filter_out_list_and_dict(ratio['operational'], f'{ratio["financialStatementDate"]}_operational'))
                            flat_data[-1].update(filter_out_list_and_dict(ratio['profitability'], f'{ratio["financialStatementDate"]}_profitability'))

                df = pd.DataFrame(flat_data)

        except Exception as e:
            print(f"Error: {str(e)}")
            print("An error occurred while processing the API response.")
            return None
        
        return EDFXEndpoints.EDFXExportData(df, output_format, file_name)

    @staticmethod
    def EDFXRatioCalculationsParse(RatiosCalculationJson: dict, FormatType: str = 'Long', output_format='Pandas',
                                   file_name="RatioCalculations"):
        """
        Parses the provided JSON data into a pandas DataFrame.

        Parameters:
        - data (dict): The JSON data to be parsed.
        - FormatType (str): The format to which the data should be parsed. Either "wide" or "long".

        Returns:
        - DataFrame: A pandas DataFrame in the specified format.
        """
        # catches errors.
        FormatType = FormatType.title()
        output_format = output_format.title()
        try:
            if not isinstance(RatiosCalculationJson, dict) or not RatiosCalculationJson:
                    print(f"The API did not return a valid response or data. Response Below:\n {RatiosCalculationJson}")
                    return None
            else:
                if FormatType not in ('Long', 'Wide'):
                    raise ValueError("Invalid FormatType provided. Choose either 'Wide' or 'Long'.")

                # Build Out
                flat_data = []
                if FormatType == 'Long':
                    for ratio in RatiosCalculationJson['ratios']:
                        flat_data.append(filter_out_list_and_dict(ratio))
                        flat_data[-1].update(filter_out_list_and_dict(ratio['leverage'], 'leverage'))
                        flat_data[-1].update(filter_out_list_and_dict(ratio['liquidity'], 'liquidity'))
                        flat_data[-1].update(filter_out_list_and_dict(ratio['operational'], 'operational'))
                        flat_data[-1].update(filter_out_list_and_dict(ratio['profitability'], 'profitability'))
                elif FormatType == 'Wide':
                    flat_data.append(filter_out_list_and_dict(ratio))
                    for ratio in RatiosCalculationJson['ratios']:
                        flat_data[-1].update(filter_out_list_and_dict(ratio['leverage'], f'{ratio["financialStatementDate"]}_leverage'))
                        flat_data[-1].update(filter_out_list_and_dict(ratio['liquidity'], f'{ratio["financialStatementDate"]}_liquidity'))
                        flat_data[-1].update(filter_out_list_and_dict(ratio['operational'], f'{ratio["financialStatementDate"]}_operational'))
                        flat_data[-1].update(filter_out_list_and_dict(ratio['profitability'], f'{ratio["financialStatementDate"]}_profitability'))

                df = pd.DataFrame(flat_data)

        except Exception as e:
            print(f"Error: {str(e)}")
            print("An error occurred while processing the API response.")
            return None
        
        return EDFXEndpoints.EDFXExportData(df, output_format, file_name)


    @staticmethod
    def EDFXSmartProjectionParse(SmartProjectionJSON: dict, FormatType: str = 'Long', output_format='Pandas',
                                 file_name = "SmartProjects"):
        """
        Parses the provided JSON data into a pandas DataFrame.

        Parameters:
        - data (dict): The JSON data to be parsed.
        - FormatType (str): The format to which the data should be parsed. Either "wide" or "long".

        Returns:
        - DataFrame: A pandas DataFrame in the specified format.
        """
        # catches errors.
        FormatType = FormatType.title()
        output_format = output_format.title()
        try: 
            if not isinstance(SmartProjectionJSON, dict) or not SmartProjectionJSON:
                    print(f"The API did not return a valid response or data. Response Below:\n {SmartProjectionJSON}")
                    return None
            else:

                if FormatType not in ('Long', 'Wide'):
                    raise ValueError("Invalid FormatType provided. Choose either 'Wide' or 'Long'.")
                # Build Out
                flat_data = []
                for entity in SmartProjectionJSON['entities']:
                    if FormatType == 'Long':
                        for projection in entity['projections']:
                            statement = projection['statement']
                            flat_data.append(filter_out_list_and_dict(entity))
                            flat_data[-1].update(filter_out_list_and_dict(projection, 'projection'))
                            flat_data[-1].update(filter_out_list_and_dict(statement['balanceSheet'], 'balanceSheet'))
                            flat_data[-1].update(filter_out_list_and_dict(statement['incomeStatement'], 'incomeStatement'))
                    elif FormatType == 'Wide':
                        flat_data.append(filter_out_list_and_dict(entity))
                        for projection in entity['projections']:
                            statement = projection['statement']
                            flat_data[-1].update(filter_out_list_and_dict(projection, f'{projection["financialStatementDate"]}_projection'))
                            flat_data[-1].update(filter_out_list_and_dict(statement['balanceSheet'], f'{projection["financialStatementDate"]}_balanceSheet'))
                            flat_data[-1].update(filter_out_list_and_dict(statement['incomeStatement'], f'{projection["financialStatementDate"]}_incomeStatement'))

                df = pd.DataFrame(flat_data)

        except Exception as e:
            print(f"Error: {str(e)}")
            print("An error occurred while processing the API response.")
            return None
        
        return EDFXEndpoints.EDFXExportData(df, output_format, file_name)

    @staticmethod
    def EDFXLGDParse(LGDJSON: dict, FormatType: str = 'Long', output_format='Pandas',
                     file_name = "LGD"):

        """
        Parses the provided JSON data into a pandas DataFrame.

        Parameters:
        - data (dict): The JSON data to be parsed.
        - FormatType (str): The format to which the data should be parsed. Either "wide" or "long".

        Returns:
        - DataFrame: A pandas DataFrame in the specified format.
        """
        # catches errors.
        FormatType = FormatType.title()
        output_format = output_format.title()
        try:
            if not isinstance(LGDJSON, dict) or not LGDJSON:
                    print(f"The API did not return a valid response or data. Response Below:\n {LGDJSON}")
                    return None
            else:
                if FormatType not in ('Long', 'Wide'):
                    raise ValueError("Invalid FormatType provided. Choose either 'Wide' or 'Long'.")
                # Build Out
                flat_data = []
                for entity in LGDJSON['entities']:
                    if FormatType == 'Long':
                        for loan in entity['loans']:
                            flat_data.append(filter_out_list_and_dict(entity))
                            flat_data[-1].update(filter_out_list_and_dict(loan['tenorMatchedResults'], 'tenorMatchedResults'))
                            for term_structure in ('annualized', 'cumulative'):
                                for inner_term_structure in loan['termStructureLgd'][term_structure]:
                                    if loan['termStructureLgd'][term_structure][inner_term_structure]:
                                        flat_data[-1].update(filter_out_list_and_dict(loan['termStructureLgd'][term_structure][inner_term_structure], f'termStructureLgd_{term_structure}_{inner_term_structure}'))

                            if loan['termStructureLgd']['longRun']:
                                flat_data[-1].update(filter_out_list_and_dict(loan['termStructureLgd']['longRun'], 'termStructureLgd_longRun'))
                            if loan['termStructureCumulativePd']:
                                flat_data[-1].update(filter_out_list_and_dict(loan['termStructureCumulativePd'], 'termStructureCumulativePd'))
                            if loan['scoreCardResults']:
                                flat_data[-1].update(filter_out_list_and_dict(loan['scoreCardResults'], 'scoreCardResults'))

                    elif FormatType == 'Wide':
                        flat_data.append(filter_out_list_and_dict(entity))
                        for loan in entity['loans']:
                            flat_data[-1].update(filter_out_list_and_dict(loan['tenorMatchedResults'], 'tenorMatchedResults'))
                            for term_structure in ('annualized', 'cumulative'):
                                for inner_term_structure in loan['termStructureLgd'][term_structure]:
                                    if loan['termStructureLgd'][term_structure][inner_term_structure]:
                                        flat_data[-1].update(filter_out_list_and_dict(loan['termStructureLgd'][term_structure][inner_term_structure], f'termStructureLgd_{term_structure}_{inner_term_structure}'))

                            if loan['termStructureLgd']['longRun']:
                                flat_data[-1].update(filter_out_list_and_dict(loan['termStructureLgd']['longRun'], 'termStructureLgd_longRun'))
                            if loan['termStructureCumulativePd']:
                                flat_data[-1].update(filter_out_list_and_dict(loan['termStructureCumulativePd'], 'termStructureCumulativePd'))
                            if loan['scoreCardResults']:
                                flat_data[-1].update(filter_out_list_and_dict(loan['scoreCardResults'], 'scoreCardResults'))

                df = pd.DataFrame(flat_data)

        except Exception as e:
            print(f"Error: {str(e)}")
            print("An error occurred while processing the API response.")
            return None
        
        return EDFXEndpoints.EDFXExportData(df, output_format, file_name)

    @staticmethod
    def EDFXClimateIndustryTransitionRiskDriversParse(data: dict, output_format: str = 'Pandas', file_name: str = 'ClimateIndustryTransitionRiskDriversParse'):
        
        """
        Parses Climate Transition Risk Drivers
        """
        try:
            if not isinstance(data, dict) or not data:
                print(f"The API did not return a valid response or data. Response Below:\n {LGDJSON}")
                return None
            else:
                flat_data = []
                for scenario_name, scenario_items in data.items():
                    for scenario_item in scenario_items:
                        flat_data_item = {'scenario': scenario_name}
                        flat_data_item.update(scenario_item)
                        flat_data.append(flat_data_item)

                df = pd.DataFrame(flat_data)
                
        except Exception as e:
            print(f"Error: {str(e)}")
            print("An error occurred while processing the API response.")
            return None
        
        return EDFXEndpoints.EDFXExportData(df, output_format, file_name)


if __name__ == "__main__":

    public  = mk.EDF_X()['Client'],# EDFX public key
    private = mk.EDF_X()['Client_Secret'], # EDFX private key.
    endpoints = EDFXEndpoints(public, private)











