
"""
Created on Fri Mar 31 07:04:08 2023

@author: user


Spyder Editor
"""


import pandas as pd
import numpy as np
import json
import requests





def EDF_X():
 
    """
    This fuction returns the EDF-X API Key

    """
    API_Public_Key = 'YOURPUBLICKEY'
    API_Private_Key = 'YOURPRIVATEKEY'
    # with dual keys I prefer returning a dictionary
    edfx = {'Client': API_Public_Key, 'Client_Secret': API_Private_Key}
    return edfx

