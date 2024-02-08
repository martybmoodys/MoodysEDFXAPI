from dataclasses import dataclass

@dataclass
class CollateralTypes:

    ACCOUNTS_RECEIVABLE = "Accounts Receivable"
    INVENTORY = "Inventory"
    PROPERTY_PLANT_AND_EQUIPMENT = "Property, Plant, & Equipment"
    CASH_AND_EQUIVALENTS = "Cash & Equivalents"
    CASH_SURRENDER_VALUE_OF_LIFE_INSURANCE = "Cash Surrender Value of Life Insurance"
    MARKETABLE_SECURITIES = "Marketable Securities "
    TIME_DEPOSITS = "Time Deposits"
    REAL_ESTATE = "Real Estate"
    INTELLECTUAL_PROPERTY = "Intellectual Property"
    LETTERS_OF_CREDIT = "Letters of Credit"
    OTHER_ASSETS = "Other Assets"

@dataclass
class LoanScorecardParameterValues:
    NO = "No"
    YES = "Yes"

@dataclass
class CollateralQuestions:

    REPORT_FREQUENCY = "Report Frequency"
    FIELD_AUDIT_FREQUENCY = "Field Audit Frequency"
    #Accts Receivable additions
    STANDARD_PAYMENT_TERMS = "Standard Payment Terms"
    CUSTOMER_CONCENTRATION = "Customer Concentration"
    CUSTOMER_CREDIT_QUALITY = "Customer Credit Quality"
    BORROWING_BASE = "Borrowing Base"
    DOMINION_OF_FUNDS = "Dominion of Funds"
    # Inventory Additions
    MARKET_TO_BOOK = "Market to Book"
    APPRAISAL_AGE = "Appraisal Age"
    INVENTORY_LOCATION = "Inventory Location"
    INSURANCE_AMOUNT = "Insurance Amount"
    #PP&E Additions
    PHYSICAL_CONDITION = "Physical Condition"
    #Cash & Equivalents 
    LOCATION_OF_ACCOUNTS = "Location of Accounts"
    #Case Surrender Value of Life Insurance
    PAYMENT_STATUS = "Payment Status"
    #Marketable Securities Additions
    SECURITY_RATING = "Security Rating"
    #Time Deposits Additions
    ISSUER_CREDIT_RATING = "Issuer Credit Rating"
    #RealEstate Additions
    PROPERTY_TYPE = "Property Type"
    OWNER_OCCUPIED = "Owner Occupied"
    ENVIRONMENTAL_AUDIT = "Environmental Audit"
    #Intellectual Property and other assets 
    NOT_APPLICABLE = 'n/a'



@dataclass
class CollateralAnswers:

    NOT_AVAILABLE = "Not Available"
    WEEKLY = "Weekly"
    MONTHLY = "Monthly"
    QUARTERLY = "Quarterly"
    SEMI_ANNUALLY = "Semi-Annually"
    ANNUALLY = "Annually"
    MORE_THAN_ANNUALLY = "> Annually"

    #Collateral Specific
    DAYS_0_30 = "0-30 Days"
    DAYS_31_60= "31-60 Days"
    DAYS_61_90 = "61-90 Days"
    DAYS_MORE_THAN_90 = "> 90 Days"
    LOW = "Low"
    AVERAGE = "Average"
    HIGH = "High"
    EXTREME = "Extreme"
    EXCELLENT = "Excellent"
    AVERAGE = "Average"
    BELOW_AVERAGE = "Below Average"

    YES = "Yes"
    NO = "No"

    # Inventory additions
    MORE_THAN_2 = "> 2"
    ONE_OR_TWO = "1-2"
    LESS_THAN_1 = "< 1"
    DAYS_LESS_THAN_90 = "< 90 Days"
    DAYS_90_179 = "90-179 Days"
    DAYS_180_360 = "180-360 Days"
    DAYS_MORE_THAN_360 = "> 360 Days"
    OWNED = "Owned"
    LEASED_W_WAIVER = "Leased w/ Waiver"
    LEASED_WO_WAIVER = "Leased w/o Waiver"
    AT_OR_ABOVE_MARKET_VALUE = "At or Above Market Value"
    BELOW_MARKET_VALUE = "Below Market Value"
    NOT_INSURED = "Not Insured"
    #PP&E Additions = None
    #Cash & Equivalents Additions
    OUR_INSTITUTION = "Our Institution"
    OTHER_BANK = "Other Bank"
    #CASE Surrender Value of Life Insurance additions
    CURRENT = "Current"
    DELINQUENT = "Delinquent"
    #Marketable Securities additions
    NOT_RATED = "Not Rated"
    SECURITY_RATING = "Investment Grade"
    SPECULATIVE_RATING = "Speculative Grade"
    #Time Deposits Additions = None
    #Real Estate Additions
    OFFICE_BUILDING = "Office Building"
    WAREHOUSE = "Warehouse"
    OTHER = 'Other'
    LAND = "Land"
    PERFORMED_NO_FURTHER_ACTION = "Performed; No Further Action"
    PHASE1_AUDIT_NOT_PERFORMED = "Phase I Audit Not Performed"
    PERFORMED_REMEDIATION_REQUIRED = "Performed; Remediation Required"
    #Intellectual Property & Other assets
    NOT_APPLICABLE = "n/a"

@dataclass
class CollateralQuestionAnswer:
    name: CollateralQuestions
    value: CollateralAnswers

    def to_dict(self):
        return {
            "name": self.name,
            "value": self.value
        }

@dataclass
class Collateral:
    customCollateralId:str
    loanId:str
    collateralType:CollateralTypes
    amount:float
    questionAnswers:list[CollateralQuestionAnswer]

    def to_dict(self):
        """
         "questionAnswers": [q.to_dict() for q in self.questionAnswers] we must use q.to_dict() becuase 
         CollateralQuestionAnswer is a class object when it's being iterated through. 
        """
        return {
            "customCollateralId": self.customCollateralId,
            "loanId": self.loanId,
            "collateralType": self.collateralType,
            "amount": self.amount,
            "questionAnswers": [q.to_dict() for q in self.questionAnswers]
        }

@dataclass
class GuaranteeType:
    CORPORATE = "Corporate"
    GOVERNMENT = "Government"
    PERSONAL = "Personal"


@dataclass
class GuaranteeQuestions:

    CREDIT_RATING_MOODYS_SNP = "Credit Rating (Moody's / S&P)"
    PROBABILITY_OF_DEFAULT_1Y = "Probability of Default (1 Year)"
    TOTAL_LIABILITIES_TO_TANGIBLE_NET_WORTH = "Total Liabilities to Tangible Net Worth"
    CASH_AND_EQUIVALENTS_TO_TOTAL_DEBT = "Cash and Equivalents to Total Debt"
    FINANCIAL_STATEMENT_TYPE = "Financial Statement Type"
    LEGAL_CONSIDERATIONS = "Legal Considerations"
    ACCESS_TO_CAPITAL = "Access to Capital"
    GOVERNMENT_ENTITY = "Government Entity"
    CREDIT_SCORE = "Credit Score"
    ADJUSTED_NET_WORTH_TO_LIABILITIES = "Adj. Net Worth to Total Liabilities"
    DEBT_TO_INCOME = "Debt to Income"
    INCOME_VERIFICATION = "Income Verification"
    PERSONAL_FINANCIAL_STATEMENT_TYPE = "Personal Financial Statement Type"

@dataclass
class GuaranteeAnswers:
    NOT_RATED = "Not Rated"
    NOT_AVAILABLE = "Not Available"
    # Ratings 
    AAA_AAA = "Aaa/AAA"
    AA1_AA_PLUS = "Aa1/AA+"
    AA2_AA = "Aa2/AA"
    AA3_AA_MINUS = "Aa3/AA-"
    A2_A = "A2/A"
    A3_A_MINUS = "A3/A-"
    BAA1_BBB_PLUS = "Baa1/BBB+"
    BAA2_BBB = "Baa2/BBB"
    BAA3_BBB_MINUS = "Baa3/BBB-"
    BA1_BB_PLUS = "Ba1/BB+"
    BA2_BB = "Ba2/BB"
    BA3_BB_MINUS = "Ba3/BB-"
    B1_B_PLUS = "B1/B+"
    B2_B = "B2/B"
    B3_B_MINUS = "B3/B-"
    CAA1_CCC_PLUS = "Caa1/CCC+"
    CAA2_CCC = "Caa2/CCC"
    CAA3_CCC_MINUS = "Caa3/CCC-"
    # PD's
    PD_LESS_THAN_07 = "< 0.07%"
    PD_0_08_TO_0_30 = "0.08% - 0.30%"
    PD_0_31_TO_0_66 = "0.31% - 0.66%"
    PD_0_67_TO_1_78 = "0.67% - 1.78%"
    PD_1_79_TO_2_44 = "1.79% - 2.44%"
    PD_2_45_TO_3_79 = "2.45% - 3.79%"
    PD_3_80_TO_6_84 = "3.80% - 6.84%"
    PD_6_85_TO_8_81 = "6.85% - 8.81%"
    PD_MORE_THAN_8_81 = "> 8.81%"
    # Total Liabilities to Tangible Net Worth
    LESS_THAN_1_1 = "< 1:1"
    LESS_THAN_2_1 = "< 2:1"
    LESS_THAN_3_1 = "< 3:1"
    LESS_THAN_4_1 = "< 4:1"
    MORE_THAN_4_1 = "> 4:1"
    # Cash and Equivalents to Total Debt
    P_MORE_THAN_25 = "> 25%"
    P_16_25 = "16% - 25%"
    P_5_15 = "5% - 15%"
    P_LESS_THAN_5 = "< 5%"
    #Financial Statement Type
    UNQUALIFIED = "Unqualified"
    QUALIFIED = "Qualified"
    REVIEWED = "Reviewed"
    COMPILED = "Compiled"
    COMPILED_PREPARED = "Company Prepared"
    NO_ISSUES = "No Issues"
    #Legal Considerations
    MINOR_CONCERNS = "Minor Concerns"
    MATERIAL_ISSUES = "Material Issues"
    #Acess to Capital
    PROVEN_AND_DEMONSTRATED = 'Proven and Demonstrated'
    LIMITED_ACCESS = "Limited Access"
    MINIMAL_OR_COST_PROHIBITIVE = "Minimal or Cost Prohibitive"
    # Government Entity
    FEDERAL = "Federal"
    STATE = "State"
    LOCAL = "Local"
    # Credit Score
    CS_MORE_THAN_759 = "> 759"
    CS_700_759 = "700 - 759"
    CS_660_699 = "660 - 699"
    CS_620_659 = "620 - 659"
    CS_LESS_THAN_620 = "< 620"
    #Adjusted Net worth to Total Liabilities additions
    P_MORE_THAN_100 = "> 100%"
    P_76_100 = "76% - 100%"
    P_51_75 = "51% - 75%"
    P_25_50 = "25% - 50%"
    P_LESS_THAN_25 = "< 25%"
    # Debt to Income  additions
    P_LESS_THAN_20 = "< 20%"
    P_20_30 = "20% - 30%"
    P_31_40 = "31% - 40%"
    P_41_40 = "41% - 50%"
    P_MORE_THAN_50 = "> 50%"
    #Income Verification additions
    FILES_TAX_RETURN = "Filed Tax Return"
    PERSONAL_FINANCIAL_STATEMENT = "Personal Financial Statement"
    OTHER = "Other"
    # Personal Financial Statement Type Additions
    AUDITED = "Audited"
    INDIVIDUALLY_PREPARED = "Individually Prepared"
    #Legal Consideration Additions additions = None


@dataclass
class GuaranteeQuestionAnswer:
    name: GuaranteeQuestions
    value: GuaranteeAnswers

    def to_dict(self):
        return {
            "name": self.name,
            "value": self.value
        }

@dataclass
class Guarantee:
    amount: float
    customGuaranteeId:str
    guaranteeId: str
    guaranteeName: str
    guaranteeType: GuaranteeType
    loanId: str
    questionAnswers:list[GuaranteeQuestionAnswer]

    def to_dict(self):
        return {
            "amount": self.amount,
            "customGuaranteeId": self.customGuaranteeId,
            "guaranteeId": self.guaranteeId,
            "guaranteeName": self.guaranteeName,
            "guaranteeType": self.guaranteeType,
            "loanId": self.loanId,
            "questionAnswers": [q.to_dict() for q in self.questionAnswers]
            }


@dataclass
class LgdQualitativeFactor:

    COVENANT_STRUCTURE = "Covenant Structure"
    ENTERPRISE_VALUATION = "Enterprise Valuation"

@dataclass
class LgdQualitativeFactorsQuestion:

    COVENANT_VIOLOATION_HISTORY = "Covenant Violation History"
    COMPLIANCE_MONITORING = "Compliance Monitoring"
    REPORTING_FREQUENCY = "Reporting Frequency"
    COMPLIANCE_CERTIFICATE = "Compliance Certificate"
    MINIMUM_NET_WORTH = "Minimum Net Worth"
    MINIMUM_LIQUIDITY = "Minimum Liquidity"
    MINIMUM_DEBT_SERVICE_COVERAGE = "Minimum Debt Service Coverage"
    MAXIMUM_LEVERAGE = "Maximum Leverage"
    VALUATION_METHODOLOGY = "Valuation Methodology"
    ENTERPRISE_VALUE_TO_TOTAL_DEBT = "Enterprise Value to Total Debt"

@dataclass
class LgdQualitativeFactorsAnswers:
    
    NONE = "None"
    NOT_AVAILABLE = "Not Available"
    #Covenant Structure | Covenant Violation history
    LESS_THAN_3 = "< 3"
    BETWEEN_3_5 = "3-5"
    MORE_THAN_5 = "> 5"
    #Covenant Structure | Compliance Monitoring (additions)
    FORMAL_CHECKLIST = "Formal Checklist"
    INFORMALLY_CALCULATED = "Informally Calculated"
    INTERNALLY_REVIEWED = "Internally Reviewed"
    #Covenant Structure | Reporting Frequency (additions)
    MONTHLY = "Monthly"
    QUARTERLY = "Quarterly"
    SEMI_ANNUALLY = "Semi-Annually"
    ANNUALLY = "Annually"
    MORE_THAN_ANNUALLY = "> Annually"
    #Covenant Structure | Compliance Certification (additions)
    SIGNED_BY_AUDITOR = "Signed by Auditor"
    SIGNED_BY_OFFICER = "Signed by Officer"
    UNSIGNED = "Unsigned"
    #Covenant Structure | Minimum Net Worth (additions)
    IMPROVEMENT_REQUIRED = "Improvement Required"
    MAINTENANCE_REQUIRED = "Maintenance Required"
    DETERIORATION_ALLOWED = "Deterioration Allowed"
    NO_COVENANT_PRESENT = "No Covenant Present"
    #Covenant Structure | Minimum Liquidity (additions = None)
    #Covenant Structure | Minimum Debt Service Coverage (additions = None)
    #Covenant Structure | Maximum Leverage (additions = None)
    #Covenant Structure | Valuation Methodology (additions)
    MARKET_CAPITALIZATION = "Market Capitalization"
    DISCOUNTED_CASH_FLOW = "Discounted Cash Flow"
    RECENT_TRANSACTION_COMPS = "Recent Transaction (Comps)"
    TRADING_MULTIPLE_PE = "Trading Multiple (P/E)"
    OTHER = "Other"
    #Covenant Structure | Enterprise Value to Debt (additions)
    LESS_THAN_1_1 = "< 1:1"
    LESS_THAN_2_1 = "< 2:1"
    LESS_THAN_3_1 = "< 3:1"
    LESS_THAN_4_1 = "< 4:1"
    MORE_THAN_4_1 = "> 4:1"


@dataclass
class LgdQualitativeFactorsQuestionAnswers:
    
    name:LgdQualitativeFactorsQuestion
    value:LgdQualitativeFactorsAnswers

    def to_dict(self):
        return {"name": self.name,
                "value": self.value}
      
@dataclass
class CovenantStructure:

    covenantStructureId:str 
    loanId:str
    questionAnswer:list[LgdQualitativeFactorsQuestionAnswers]    

    def to_dict(self):
        return {
            "covenantStructureId": self.covenantStructureId,
            "loanId": self.loanId,
            "questionAnswers": [qa.to_dict() for qa in self.questionAnswer]
        }

@dataclass
class EnterpriseValuation:

  enterpriseValuationId:str
  loanId:str
  questionAnswer: list[LgdQualitativeFactorsQuestionAnswers]

  def to_dict(self):
      return {
          "covenantStructureId": self.enterpriseValuationId,
          "loanId": self.loanId,
          "questionAnswers": [qa.to_dict() for qa in self.questionAnswer]
      }

@dataclass
class LGDQualitativeFactorOverlay:

    covenantStructure : CovenantStructure
    enterpriseValuationId : EnterpriseValuation

    def to_dict(self):
        return {
            "covenantStructure": self.covenantStructure.to_dict(),
            "enterpriseValuationId": self.enterpriseValuationId.to_dict()
        }
    


@dataclass
class LoanScorecard:
    loanScorecardId:str
    blanketLien:LoanScorecardParameterValues
    collateral:list[Collateral] = None
    guarantee: list[Guarantee] = None
    lgdQualitativeFactors:list[LGDQualitativeFactorOverlay] = None

    def to_dict(self):
        scorecard_dict = {
            "loanScorecardId": self.loanScorecardId,
            "blanketLien": self.blanketLien,
            
        }
        if self.guarantee:
            scorecard_dict["guarantee"] = [g.to_dict() for g in self.guarantee]
        if self.collateral:
            scorecard_dict["collateral"] = [c.to_dict() for c in self.collateral]
        if self.lgdQualitativeFactors:
            scorecard_dict["lgdQualitativeFactorsOverlay"] = [qol.to_dict() for qol in self.lgdQualitativeFactors]

        return scorecard_dict

if __name__ == '__main__':
    # Example usage
    my_loan_scorecard = LoanScorecard(
        loanScorecardId="2b77f0d7-b0e4-4dbc-844d-aabb4376a688",
        blanketLien=LoanScorecardParameterValues.NO,
        collateral=[
            Collateral(
                customCollateralId="123",
                loanId="123",
                collateralType=CollateralTypes.ACCOUNTS_RECEIVABLE,
                amount=10000,
                questionAnswers=[
                    CollateralQuestionAnswer(name=CollateralQuestions.STANDARD_PAYMENT_TERMS,
                                            value=CollateralAnswers.NOT_AVAILABLE),
                    CollateralQuestionAnswer(name=CollateralQuestions.CUSTOMER_CONCENTRATION,
                                            value=CollateralAnswers.HIGH),
                    CollateralQuestionAnswer(name=CollateralQuestions.CUSTOMER_CREDIT_QUALITY,
                                            value=CollateralAnswers.EXCELLENT),
                ]
            )
        ],
        guarantee=[
            Guarantee(
                amount=10000,
                customGuaranteeId=123,
                guaranteeId=123,
                guaranteeName="test",
                guaranteeType=GuaranteeType.CORPORATE,
                loanId="123",
                questionAnswers=[
                    GuaranteeQuestionAnswer(name=GuaranteeQuestions.TOTAL_LIABILITIES_TO_TANGIBLE_NET_WORTH,
                                            value=GuaranteeAnswers.A2_A),
                    GuaranteeQuestionAnswer(name=GuaranteeQuestions.TOTAL_LIABILITIES_TO_TANGIBLE_NET_WORTH,
                                            value=GuaranteeAnswers.A2_A),
                    GuaranteeQuestionAnswer(name=GuaranteeQuestions.TOTAL_LIABILITIES_TO_TANGIBLE_NET_WORTH,
                                            value=GuaranteeAnswers.A2_A)
                ]
            )
        ],

        lgdQualitativeFactors = [
            LGDQualitativeFactorOverlay(    
                CovenantStructure(
                    covenantStructureId="007",
                    loanId="88",
                    questionAnswer=[
                        LgdQualitativeFactorsQuestionAnswers(name=LgdQualitativeFactorsQuestion.COMPLIANCE_CERTIFICATE,
                                                            value=LgdQualitativeFactorsAnswers.SIGNED_BY_AUDITOR),
                        LgdQualitativeFactorsQuestionAnswers(name=LgdQualitativeFactorsQuestion.COVENANT_VIOLOATION_HISTORY,
                                                            value=LgdQualitativeFactorsAnswers.NONE),
                        LgdQualitativeFactorsQuestionAnswers(name=LgdQualitativeFactorsQuestion.COMPLIANCE_MONITORING,
                                                            value=LgdQualitativeFactorsAnswers.FORMAL_CHECKLIST),
                        LgdQualitativeFactorsQuestionAnswers(name=LgdQualitativeFactorsQuestion.MINIMUM_NET_WORTH,
                                                            value=LgdQualitativeFactorsAnswers.DETERIORATION_ALLOWED)
                    ]
                ),
                EnterpriseValuation(
                    enterpriseValuationId="10",
                    loanId="33",
                    questionAnswer=[
                        LgdQualitativeFactorsQuestionAnswers(name=LgdQualitativeFactorsQuestion.VALUATION_METHODOLOGY,
                                                                value=LgdQualitativeFactorsAnswers.TRADING_MULTIPLE_PE),
                        LgdQualitativeFactorsQuestionAnswers(name=LgdQualitativeFactorsQuestion.ENTERPRISE_VALUE_TO_TOTAL_DEBT,
                                                                value=LgdQualitativeFactorsAnswers.LESS_THAN_3_1)
                    ]
                                                                                
                )
            )
            ]
    )
                                            
                    

        
    

    # Print the scorecard
    print(my_loan_scorecard.to_dict())
