import requests
import urllib.parse
import datetime
import jwt
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



class AuthenticationError(Exception):
    pass

class EDFXClient():

    #20 mintues for bearer token to be alive. 
    AUTH_TOKEN_RENEWAL_THRESHOLD_IN_SECONDS = 20*60


    def __init__(self, api_publickey:str = None, api_privatekey:str = None, proxies = {}, logger = None):

        """
        EDF-X Class.  For Continuous Authentication within an application that leverages the MOODYS 
        Analytics API.  

        Key functionality includes continuous bearer token authentication, and logging functionality while
        a session is running.
        """
        self.api_publickey = api_publickey if api_publickey is not None else os.getenv('API_Public_Key')
        self.api_privatekey = api_privatekey if api_privatekey is not None else os.getenv('API_Private_Key')
        self.proxies = proxies
        self.base_url = "https://api.edfx.moodysanalytics.com"
        self.authentication_url = "https://sso.moodysanalytics.com/sso-api/v1/token"
        
        self.bearer_token = None
        self.auth_token = None
        self.bearer_token_claimset= None
        self.expiration_timestamp = None
        self.expiration_datetime = None
        # this just is more readable so I call it self.logger instead of self.construct_logger() when I want to use it.
        self.logger = logger or self.construct_logger()

    def construct_logger(self):
        """
        Creates logger object such that every log message 
        will display the time it was created, 
        the log level (e.g., INFO, ERROR, etc.), followed by the actual log message. 
        Then, this format is set to both the handlers.
        """
        logger = logging.getLogger('EDFXClient')
        # file handler and stream handler tell us where message is getting sent they're both sending the log messages to the console.
        file_handler = logging.StreamHandler()
        #the name file_handler is a bit misleading because it doesn't log to a file but to the console just like the stream_handler.
        stream_handler = logging.StreamHandler()
        # lets define format for the log messages
        formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
        file_handler.setFormatter(formatter)
        stream_handler.setFormatter(formatter)
        # attaching handlers to each file_handler and stream_handerler objects => displays message on console
        logger.addHandler(file_handler)
        logger.addHandler(stream_handler)
        # This line sets the minimum level of severity for messages that the logger will handle. 
        # Here, it's set to INFO, which means it will capture messages of INFO level and above (i.e., INFO, WARNING, ERROR, CRITICAL)
        logger.setLevel(logging.INFO)
        return logger


    def get_bearer_token(self):

        """
        Check if bearer token exists and if it needs to be renewed.
        Get bearer token. Then store authentication variable.
        """
        if self.api_publickey is None or self.api_privatekey is None:
            raise AuthenticationError("API public key or private key is not set")
        
        if self.bearer_token is None:
            # this is the 'result' object from self.request_new_bearer_token()
            self.bearer_token = self.request_new_bearer_token()
            self.logger.info(f"Security token has been generated.")
            self.update_bearer_token_claimset_expiration_info()
            bearer = self.bearer_token
            return bearer

        #If it's a time to renew bearer token, renew bearer token.
        if self.is_bearer_token_renewal():
            try:
                self.bearer_token = self.renew_bearer_token()
                self.update_bearer_token_claimset_expiration_info()
                return self.bearer_token
            except AuthenticationError:
                # Note, This apparently can happen if token is fully expired.  In this case, we can request a new token
                self.bearer_token = self.request_new_bearer_token()
                self.update_bearer_token_claimset_expiration_info()
                result = self.bearer_token
                return result
        else:
            return self.bearer_token

    def request_new_bearer_token(self):
        """
        This gives you the Bearer Token.  
        Initial Code found here may have incorrectly been trying to 
        pull access token: https://github.com/moodysanalytics/apic/edit/master/api_client/security.py
        """

        url = self.authentication_url

        bearer_token_params  = {
                                'client_id': self.api_publickey,
                                'client_secret': self.api_privatekey,
                                'grant_type': 'client_credentials',
                                'scope': 'openid'
                                }
        headers = {
                    'Content-Type': 'application/x-www-form-urlencoded'
                    }

        response = requests.post(
                                url,
                                data=bearer_token_params,
                                headers=headers,
                                auth=(self.api_publickey, self.api_privatekey),
                                proxies=self.proxies
                                )

        if response.status_code != 200:
            response_detail = response.json() if response.content else {}
            raise AuthenticationError(
                                        f"Error in response. Status code: {response.status_code}, message: {response.reason}, detail: {response_detail}"
                                        )
        response_body_json = response.json()
        # new python dictionary query bearer token
        bearer = response_body_json.get('id_token')
        
        # print(f"Bearer token: {bearer}")
        # print(f"Type: {type(bearer)}")

        # Check1: See if I get a result
        if bearer is None or bearer == "":
                raise AuthenticationError(
                    f"Authorization token is empty. "
                    f"Authentication token has not been retrieved from "
                    f".env or is incorrect for {self.api_publickey}"
                )
        token_type = response_body_json.get('token_type')
        #Check2: If I get a result, check and see if the token_type is 'Bearer'
        if token_type != 'Bearer':
            raise AuthenticationError(f"Wrong token type '{token_type}'. Expected token type is 'Bearer'. ")

        # Here we set the authentication parameters
        self.auth_token = response_body_json.get('access_token')

        if self.auth_token is None or self.auth_token == "":
            raise AuthenticationError(
                f"Access token is empty. "
                f"Access token has not been retrieved from"
                f".env or is incorrect for {self.api_publickey} and/or {self.api_privatekey}."
                )

        return bearer

    def update_bearer_token_claimset_expiration_info(self):

        """
        This method is updated to jwt.decode the bearer token to self.bearer_token_claimsetparamater

        UNDERSTAND: Users may need to converst public and/or private key to PEM Format.  Currently
        Moodys Public and Private keys are not in this format and as such verify_signature must be 
        set to False.  
        """

        if self.bearer_token is None:
            raise AuthenticationError("The auth token is None, cannot decode it.")
        
        # encode to bytes if it's a string
        if isinstance(self.bearer_token, str):
            self.bearer_token = self.bearer_token.encode('utf-8')  

        try:
            # This line decodes the bearer_token attribute of the class instance (represented by self.bearer_token) using the decode method from the jwt (JSON Web Token) library.
            # The verify=False parameter indicates that the token should be decoded without verifying its signature. 
            self.bearer_token_claimset= jwt.decode(self.bearer_token, options={"verify_signature": False})
            self.expiration_timestamp = self.bearer_token_claimset['exp']
            # print(f"Self.expiration_timestamp: {self.expiration_timestamp}/n")
            self.expiration_datetime = datetime.datetime.fromtimestamp(self.expiration_timestamp)
            # print(f"Self.expiration_datetime: {self.expiration_datetime}/n")
            # print(f"This is the whole self.bearer_token_claimset: {self.bearer_token_claimset}")

        except Exception as e:
            raise AuthenticationError(f"Error decoding auth token: {e}")


    def delete_bearer_token(self, auth_token:str):
        """
        We are deleting the authentication for the client. 
        """
        url = self.authentication_url
        # Create the headers using the new static method
        headers = EDFXClient.create_request_headers('delete', auth_token)
        response = requests.delete(url, headers=headers, proxies=self.proxies)
        response.raise_for_status()

    
    def revoke_bearer_token(self):
        """
        Revoke authentication token
        """
        self.delete_bearer_token(self.auth_token)
        # Here we just set all variables related to the authentication token back to None
        self.auth_token = None
        self.bearer_token_claimset= None
        self.expiration_timestamp = None
        self.expirattion_datetime = None
    
    def renew_bearer_token(self):
        """
        Ends an existing authentication and provides a new authication token "bearer"
        """
        #Revoke current token
        self.revoke_bearer_token()
        #Wait 5 seconds for token revocation process
        time.sleep(5)
        # request a new token
        result = self.request_new_bearer_token()
        return result

    def is_bearer_token_renewal(self):
        
        # this method is complete

        if self.expiration_datetime is None:
            raise AuthenticationError(
                "Error checking renewal time of the authentication token."
                "The Token's expiration date/time is empty."
                "Get authentication token calling get_auth_token() first.")

        time_left = self.expiration_datetime - self.get_current_date_time()

        if time_left.days == -1:
            return True
        if time_left.seconds < EDFXClient.AUTH_TOKEN_RENEWAL_THRESHOLD_IN_SECONDS:
            return True
        #else return False is the logic
        return False

    
    def __enter__(self):

        """
        The __enter__ method logs a message and then returns self, 
        which is the instance of the EDFXClient. This instance is
        then used as client within the with statement.
        """

        self.logger.info(f"Entered authtication session.")
        return self

    def __exit__(self, exit_type, exit_value, traceback):

        """ 
        EX Case:

        with EDFXClient(api_publickey, api_privatekey) as client:
        client.ping() 

        When the with statement ends (either normally or due to an exception), 
        Python automatically calls the __exit__ method, which in this case calls self.close()
        """
        self.close()

    def close(self):
        if self.auth_token is None:
            return
        self.revoke_bearer_token()
    
    def ping(self):

        """
        This ping method is performing a basic connectivity
        check to the API server. It sends a GET request to a 
        specific endpoint (/sso-api/docs/) and checks if it 
        receives a successful response (HTTP status code 200).
        """

        url_path = "/ping"
        url = urllib.parse.urljoin(self.base_url, url_path)
        print(f"path i'm pinging: {url}")
        headers = {"Authorization": f"Bearer {self.get_bearer_token()}"}
        response = requests.get(url, proxies=self.proxies, headers=headers)
        if response.ok:
            self.logger.info(f"Single Sign-on (SSO) service connectivity test to '{self.base_url}' - PASSED")
            return True
        else:
            self.logger.error(
                f"Single Sign-On (SSO) connectivity test to '{self.base_url}' - FAILED."
                f"Status Code: {response.status_code}; Reason: {response.reason}")
        return False
    
    def get_current_date_time(self):
        result = datetime.datetime.now()
        return result

    @staticmethod
    def create_request_headers(request_type:str, auth_token:str):
        
        """
        This allows us to place the relevant headers where we need them. 
        Will be usefule when making the endpoint in other classes
        """
        base_headers = {
            'get': {'Content-Type': 'application/json'},
            'post': {'Content-Type': 'application/json'},
            'put': {'Content-Type': 'application/json'},
            'delete': {} }
        if request_type not in base_headers:
            raise ValueError(f"Unknown request type: {request_type}")
        # We start with the base headers for the given type of request
        headers = base_headers[request_type]
        # Then we add the Authorization header if an auth_token was provided
        if auth_token is not None:
            headers['Authorization'] = f'Bearer {auth_token}'
        return headers


if __name__ == '__main__':
    # not linking to os.environ() check Xing Yuan
    # I'm not using public and private key here because I don't want a circular reference for ENDPoint Class


    #---------------Below Works-----------------------------
    public  = mk.EDF_X()['Client'],# EDFX public key
    private = mk.EDF_X()['Client_Secret'], # EDFX private key.
    client = EDFXClient(public, private)
    token = client.get_bearer_token()

    print("Bearer token:", token)
    print('Bearer Token TypeObject:' ,type(token))

    #----------Requesting a relevant Ping Endpoing------------
    # I need t find a light endpoint to ping. 
    # if client.ping():
    #     print("Ping was successful.")
    # else:
    #     print("Ping failed.")