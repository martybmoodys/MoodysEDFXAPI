import io
import requests
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
from urllib.parse import urljoin
from EDFXAuthentication import EDFXClient




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

    def EDFXPD_Endpoint(self,entities:list[dict[str,str]], startDate:str=None, endDate:str=None, historyFrequency:str='monthly',
                        asyncResponse:bool=False, asReported:bool=False, modelParameters:bool=False, includeDetailResult:bool=False,
                        includdeDetailInput:bool = False, includeDetailModel:bool=False, processId:str=None, 
                        CreditEdge:bool=False, RiskCalc:bool=False, TradePayment:bool=False ):
    
        """
        Params: These are the values of the paramater dictionary you are feeding the method.

            Entities:  Parameter is REQUIRED. The object is a list of dictionary elements: value = [{'entityId': 'identifier'}]
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
            'entities': entities, 
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
                "modelDetail": includeDetailModel
            }
        }
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

        if response.status_code == 200:
            payload = response.json()
            return payload
        else:
            print(f"Request failed with status code {response.status_code} {response.text}")
            return None
        
    def EDFXPD_History(self,entities:list[dict[str,str]], startDate:str=None, endDate:str=None, historyFrequency:str=None,
                        asyncResponse:bool=False, asReported:bool=False, modelParameters:bool=False,includeDetailResult:bool=False,
                        includdeDetailInput:bool = False, includeDetailModel:bool=False, processId:str=None, 
                        CreditEdge:bool=False, RiskCalc:bool=False, TradePayment:bool=False ):
 
            
            """  
            I need to determine the above method to know the following structure for the below. 

            We MUST set the boolean values otherwise the parameter function will not return appropriately

            Required arguments are: entities, startDate
            
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
            
    def EDFXTemplateDownload(self, financialtemplate = 'Universal', output_format = 'Pandas'):


        """
        Specify what template you'd like to retrieve and the output format you'd like to use.

        Proper FinancialTemplate options: 
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
            return status
        else:
            print(response.status_code)
            print(response.text)

    def EDFXModelInputsGetFiles(self, processID: str):
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
        print(response.text)
        return response.text
    
    @staticmethod
    def excel_to_csv(excel_path:str, csv_path:str, sheet_name:str = None):
        """ 
        Converts an Excel file to a CSV file
        Parameters:
        - excel_path (str): Path to the Excel file.
        - csv_path (str): Desired path to save the resulting CSV file.
        - sheet_name (str, optional): Name of the sheet to be converted. By default, it converts the first sheet.
        """
        df = pd.read_excel(excel_path, sheet_name=sheet_name if sheet_name else 0)
        print(type(df))
        df.to_csv(csv_path, index=False)
        print(f"Converted {excel_path} to {csv_path} successfully!")



    @staticmethod
    def EDFXSearchParse(jsonresponse:dict, output_format:str = "pandas"):
        
        """
        Parses the search json dataframe
        """
        output_format = output_format.title()
        entities = jsonresponse['entities']
        #create an empty list fo collect the data for each entity
        entity_data = []

        #Expected fields for each entity
        expected_fields = [
            'entityId', 'internationalName', 'countryName', 'entityType',
            'primaryIndustryNACE', 'primaryIndustryNAICS', 'contactCity',
            'entitySize', 'latestPdModel'] 
        
        # Loop through each entity
        for entity in entities:
            entity_details = {}
            # Get each expected field and populate it, even if it's missing 
            for field in expected_fields:
                # says get value else None =Value
                entity_details[field] = entity.get(field,None)

            # If 'nationalId' is present in entity, flatten it and merge it to entity details
            national_ids = entity.get('nationalId',[])
            #notice it's a list so i iterate through the list
            for nid in national_ids:
                entity_details[nid['idName']] = nid['idValue']
            # Append the entity details to the list
            entity_data.append(entity_details)
            df = pd.DataFrame(entity_data)

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
            raise ValueError(f"Unsupported OutputFormat: {output_format}")

    
    @staticmethod
    def EDFXBatchParse(batch:json, output_format:str = "pandas"):
        """
        Allows me to take the Json batch output and transform it to a pandas dataframe or .csv file for storage/use:

        OutputFormat = 'Pandas' or 'CSV'

        THIS WILL BREAK IF MOODYS ANALYTICS CHANGES THE EDFX BATCH OUTPUT RESPONSE
        RECALL:   
        If you're using iterrows() with a pandas DataFrame, each row is a Series, and accessing its elements
        by column labels returns the values in those columns for the current row. 

        """
        df = pd.DataFrame(batch['entities'])
        output_format = output_format.title()

        #Extract national ID into separate columns (I can vectorize this but this is clearer)
        for index, row in df.iterrows():
            # This is saying if the column name is present and if that column is a list object
            if 'nationalId' in row and isinstance(row['nationalId'],list):
                # now iterate the values within the list
                for item in row['nationalId']:
                    col_name = 'nationalId_'+ item['idName']
                    # this is faster than .loc[index,col]
                    df.at[index, col_name] = item['idValue']

        # drop the original nationalId col if it exists
        if 'nationalId' in df.columns:
            df.drop(columns=['nationalId'], inplace=True)

        # Check OutputFormat
        if output_format == OutputFormat.PANDAS.value:
            return df
        
        elif output_format == OutputFormat.EXCEL.value:
            # You can change the file name as needed or even pass it as a parameter
            df.to_excel("batchoutput.xlsx", index=False)
            print("Data saved to batchoutput.xlsx")
            return None
        
        elif output_format == OutputFormat.CSV.value:
            df.to_csv('batchoutput.csv',index=False)
            print('Data Saved to batchoutput.csv')
            return None
        else:
            raise ValueError(f"Unsupported OutputFormat: {output_format}.")
        
    @staticmethod    
    def EDFXPDParse(PDsJSON:dict, FormatType = 'Long', output_format='Pandas', TimeSeries:bool = False):

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
        #Build Out
        if TimeSeries:
            pass

        if FormatType == "Wide":
            rows = []
            for entity in PDsJSON['entities']:
                row = {
                    'entityId': entity['entityId'],
                    'asOfDate': entity['asOfDate'],
                    'pd': entity['pd'],
                    'impliedRating': entity['impliedRating'],
                    'confidence': entity['confidence'],
                    'confidenceDescription': entity['confidenceDescription'],
                }
                
                # Extract term structure data
                for term_type, term_data in entity['termStructure'].items():
                    for term, value in term_data.items():
                        row[f"{term_type}_{term}"] = value
                
                rows.append(row)

            df = pd.DataFrame(rows)
        
        elif FormatType == "Long":
            rows = []
            for entity in PDsJSON['entities']:
                for term_type, term_data in entity['termStructure'].items():
                    for term, value in term_data.items():
                        row = {
                            'entityId': entity['entityId'],
                            'asOfDate': entity['asOfDate'],
                            'pd': entity['pd'],
                            'impliedRating': entity['impliedRating'],
                            'confidence': entity['confidence'],
                            'confidenceDescription': entity['confidenceDescription'],
                            'termType': term_type,
                            'term': term,
                            'value': value
                        }
                        rows.append(row)
            
            df = pd.DataFrame(rows)

        else:
            raise ValueError("Invalid FormatType provided. Choose either 'wide' or 'long'.")
        # Check OutputFormat
        if output_format == OutputFormat.PANDAS.value:
            return df
        
        elif output_format == OutputFormat.EXCEL.value:
            # You can change the file name as needed or even pass it as a parameter
            df.to_excel("PDs.xlsx", index=False)
            print("Data saved to PDs.xlsx")
            return None
        
        elif output_format == OutputFormat.CSV.value:
            df.to_csv('PDs.csv',index=False)
            print('Data Saved to PDs.csv')
            return None
        else:
            raise ValueError(f"Unsupported OutputFormat: {output_format}")




if __name__ == "__main__":

    public  = mk.EDF_X()['Client'],# EDFX public key
    private = mk.EDF_X()['Client_Secret'], # EDFX private key.
    endpoints = EDFXEndpoints(public, private)

    # Get financial template CSV file
    endpoints.EDFXFinancialsTemplateUniversal('FinancialsTemplateUniversal.csv')
    
    # Create model inputs process
    model_inputs_response = endpoints.EDFXModelInputs(uploadFilename='test_001', localFilename='CleanVersionTarget.xlsx')
    
    # If a model input process was created we will start checking the process status every 20 seconds until it completes
    if model_inputs_response:
        while True:
            model_inputs_process_status = endpoints.EDFXModelInputsGetStatus(processID=model_inputs_response['processId'])
            if model_inputs_process_status is None:
                print('No process status returned.')
                break
            if model_inputs_process_status['status'] == 'Processing':
                print('Model is still processing, retrying in 20 seconds')
                time.sleep(20) # wait 20 seconds and try again
            else:
                print('Model processing finished, getting files')
                files = endpoints.EDFXModelInputsGetFiles(processID=model_inputs_response['processId'])
                print(files)
                break
    else:
        print('No model input response')
    
    
    # print(data)
    # print('FinancialTemplate Next:\n ')
    # try:
    #     # this should work either way, I could have put FinancialTemplate.UNIVERSAL or 'Pandas'
    #     data = endpoints.EDFXFinancialTemplate(FinancialTemplate ='Universal',OutputFormat= OutputFormat.PANDAS)
    #     print(data)
    # except ValueError as e:
    #     print(f"Error: {e}")

    # # Test EDFXPD_Endpoint
    # print('Testing EDFXPD_Endpoint()')
    # data = endpoints.EDFXPD_Endpoint(
    #     entities=[{ "entityId": "US380549190" }],
    #     startDate="2016-02-01",
    #     endDate="2018-03-01"
    # )
    # print(data)
    
    # # Test EDFXPD_History
    # print('Testing EDFXPD_History()')
    # data = endpoints.EDFXPD_History(
    #     entities=[{ "entityId": "US380549190" }],
    #     startDate="2016-02-01",
    #     endDate="2018-03-01"
    # )
    # print(data)    




    


        








