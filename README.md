

# MoodysEDFXAPI

------

# ATTENTION: Before you continue UNDERSTAND:

# Moodys Analytics DOES NOT support this code.  This code is for assistance and demonstration purposes only. 

Licensed Clients should reference https://hub.moodysanalytics.com/products and the functional endpoint examples when formatting their exact questions to support.

-----

## Introduction
Moody’s Analytics stands at the forefront of financial modeling and analytics, boasting a rich legacy of crafting industry-leading models derived from an expansive proprietary dataset. This dataset comprises company financials, default histories, and recovery information. The Moody's Analytics Probability of Default (PD) represents our premier estimation, meticulously crafted from the data at hand. It is the culmination of years of rigorous analysis and empirical testing, offering our clients an unparalleled blend of quality and comprehensive coverage. With the EDF-X API, accessing these sophisticated calculations and PD values becomes seamless, granting direct access to PDs for the approximate 400 million companies (both public and private) documented in Orbis globally.

### About this Repository
Contained within this repository are refined scripts, structured with an object-oriented design, geared towards interfacing with the Moody’s EDF-X API. These scripts are open-source, adhering to the Apache License agreement found within the repository. They are designed for use by developers and industry professionals alike; however, users should employ them judiciously.

## Our overarching aim with this repository is twofold:

### For Licensed Moody’s Analytics End-users: We seek to enhance your experience with the EDF-X REST API, providing a seamless integration pathway.

### For Developers and Innovators: We demonstrate how to adeptly incorporate the classes tailored for all EDF-X API Endpoints. As the realm of endpoints expands, this repository will continually evolve, reflecting the latest advancements.

## EDF-X API: What to Expect
The EDF-X API is versatile, accommodating one of two distinct inputs:

Pre-existing Company Data: For companies within our vast database of roughly 400 million, all you need to provide is an identifier. In return, we furnish our most refined estimate of credit risk.

User-provided Data: If the company isn't within our dataset or if you opt to use custom data, the API transforms into a powerful credit risk calculator. It discerns the most fitting model based on the input and subsequently generates the corresponding PD.

### Based on the input provided, the EDF-X API provides the access to following outputs:

- A PD for any company. This is our best-estimate of the one-year probability of default given the information available.
- A PD term structure providing annualized, cumulative, and forward PD values out to ten years
- An implied rating indicating the Moody’s Analytics rating with a consistent default profile.
- A confidence indicator explaining which methodology and data were used to derive the estimate. This helps the end user understand and assess their confidence in the estimate.
- Full details of the model calculation, including input variables and links to the relevant methodology document.
- Limits for trade credit corresponding to conservative, balanced, and aggressive assumptions.
- The peer groups a company belongs to as well as their main traits.
- The appropriate Early Warning category for the company, as well as PD thresholds that are considered as triggers in the calculation.
- CDS-Implied EDF taking information from the credit markets
- Deterioration Estimate for estimates on potential MIS rating downgrades for Rated entities and adverse/'Shadow' downgrades/adverse actions for private companies
- Loss Gived Default estiamte (tailored for a particular entity sepcific credit).
- Climate
- Smart Projections (Project Financial Statment/Pro Forma) (ADDED AND PARSED 10/1/2023)

### Additional end points help the user:

- Search for entity identifiers
- Access peer group metrics
- Access financial statements and key ratios
- Scenario ConditionedPD's have been added.
- LGD SCORECARD Class LIVE.  You can use this DATACLASS to help you generate the appropriate scorecard payload. 
  



### Coming Soon

#### Loss Given Default interoperatability between legacy RiskCalc and EDFX API along with EDFX API Only Loss Given Default Large File Jupyter Notebooks. (ETA February 9 2024)
  - Will support use cases for employees who have uploaded their portfolio within EDFX and have downloaded the .csv file as well as for users who only have the entities IDs.
  - We will demonstrate how to output a legacy RiskCalc.csv 'input file' for Legacry RiskCalc however the main use case we anticipate is for the EDFX-API Only solution.
  - 
#### Bond Model Metrics (ETA JULY 1 2024)
  - Time Series of Deterioration of Probability metrics.
  - Time Series of Fair Value Spread.
  - OAS Endpoints. 


  
