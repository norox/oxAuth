

from org.xdi.oxauth.service import AuthenticationService
from org.xdi.oxauth.security import Identity
from org.xdi.model.custom.script.type.auth import PersonAuthenticationType
from org.xdi.service.cdi.util import CdiUtil
from org.xdi.util import StringHelper,ArrayHelper
from org.xdi.oxauth.util import ServerUtil
from org.xdi.oxauth.service import UserService, AuthenticationService,SessionIdService
from org.xdi.oxauth.service.net import HttpService
from org.xdi.oxauth.service import EncryptionService 

from java.util import Arrays
from java.net import URLEncoder

import java
import json, ast

    
class PersonAuthentication(PersonAuthenticationType):


    def __init__(self, currentTimeMillis):
        self.currentTimeMillis = currentTimeMillis
        self.client = None

    def init(self, configurationAttributes):
       
        print "inWebo. Initialization"

        #iw_cert_store_type = "pkcs12"   
        #iw_cert_path = "/etc/certs/Gluu_dev.p12"  
        #iw_creds_file = "/etc/certs/iw_creds.json"  
        iw_cert_store_type = configurationAttributes.get("iw_cert_store_type").getValue2()
        iw_cert_path = configurationAttributes.get("iw_cert_path").getValue2()
        iw_creds_file = configurationAttributes.get("iw_creds_file").getValue2()
        # Load credentials from file
        f = open(iw_creds_file, 'r')
        try:
           creds = json.loads(f.read())
        except:
            print "unexpected error - "+sys.exc_info()[0]
            return False
        finally:
            f.close()
        iw_cert_password = creds["CERT_PASSWORD"]
        #TODO: the password should not be in plaintext
        #try:
         #   encryptionService = CdiUtil.bean(EncryptionService)
          #  iw_cert_password = encryptionService.decrypt(iw_cert_password)
        #except:
         #   print("oops!",sys.exc_info()[0],"occured.")
          #  return False

        httpService = CdiUtil.bean(HttpService)
        self.client = httpService.getHttpsClient(None, None, None, iw_cert_store_type, iw_cert_path, iw_cert_password)
        print "inWebo. Initialized successfully"
        return True   
  

    def destroy(self, configurationAttributes):
        print "inWebo. Destroyed successfully"
        return True

    def getApiVersion(self):
        return 1

    def isValidAuthenticationMethod(self, usageType, configurationAttributes):
        return True

    def getAlternativeAuthenticationMethod(self, usageType, configurationAttributes):
        return None

    def authenticate(self, configurationAttributes, requestParameters, step):
        
        userService = CdiUtil.bean(UserService)
        authenticationService = CdiUtil.bean(AuthenticationService)
        identity = CdiUtil.bean(Identity)
        
        iw_api_uri = "https://api.myinwebo.com/FS?"  # onfigurationAttributes.get("iw_api_uri").getValue2()
        iw_service_id = 5686  # configurationAttributes.get("iw_service_id").getValue2()
        
        credentials = identity.getCredentials()
        user_name = credentials.getUsername()
        
        if (step == 1):
            identity.setWorkingParameter("iw_count_login_steps", 1)
            user_password = credentials.getPassword()
            logged_in = False
            if (StringHelper.isNotEmptyString(user_name) and StringHelper.isNotEmptyString(user_password)):
                userService = CdiUtil.bean(UserService)
                
                logged_in = authenticationService.authenticate(user_name, user_password)
                response_validation = self.validateInweboToken(iw_api_uri, iw_service_id, user_name, "",step)
                if logged_in is True and response_validation is True:
                    identity.setWorkingParameter("iw_count_login_steps", 2)
                    print "setting 2, return true"
                    return True
                else:
                    identity.setWorkingParameter("iw_count_login_steps", 1)
                    print "setting 1, return false"
                    return False
            return logged_in
        elif (step == 2):
            print "inWebo. Authenticate for step 2. ", authenticationService.getAuthenticatedUser().getUserId()

            passed_step1 = self.isPassedDefaultAuthentication
            if (not passed_step1):
                return False
            
            iw_token_array = requestParameters.get("iw_token")
            if ArrayHelper.isEmpty(iw_token_array):
                print "InWebo. Authenticate for step 2. iw_token is empty"
                return False

            iw_token = iw_token_array[0]
            response_validation = self.validateInweboToken(iw_api_uri, iw_service_id, authenticationService.getAuthenticatedUser().getUserId(), iw_token,step)
            print "step 2, response_validation:", response_validation
            if response_validation is True:
                identity.setWorkingParameter("iw_count_login_steps", 3)
            else:
                identity.setWorkingParameter("iw_count_login_steps", 2)
                
            return response_validation
        elif (step == 3):
            print "inWebo. Authenticate for step 3. ", authenticationService.getAuthenticatedUser().getUserId()
            session_id = CdiUtil.bean(SessionIdService).getSessionIdFromCookie()
            user_name = authenticationService.getAuthenticatedUser().getUserId()
            #TODO:
            # passed_step1 = self.isPassedDefaultAuthentication
            # if not passed_step1:
             #   return False
            #hardcoding timeout to 2 minutes
            response_check = self.checkStatus(iw_api_uri, iw_service_id, user_name, 20, session_id)
            return response_check 
        
        else:
            return False

    def prepareForStep(self, configurationAttributes, requestParameters, step):
        if (step == 1):
            print "InWebo. Prepare for step 1"
            return True
        elif (step == 2):
            print "InWebo. Prepare for step 2"
            return True
        elif (step == 3):
            print "InWebo. Prepare for step 3"
            return True
        else:
            return False
        
    def getExtraParametersForStep(self, configurationAttributes, step):
        return None

    def getCountAuthenticationSteps(self, configurationAttributes):
        print "inside getCountAuthenticationSteps"
        identity = CdiUtil.bean(Identity)
        if (identity.isSetWorkingParameter("iw_count_login_steps")):
            print "identity.getWorkingParameter(iw_count_login_steps) - ", identity.getWorkingParameter("iw_count_login_steps")
            return identity.getWorkingParameter("iw_count_login_steps")
        return 3
        
    def getPageForStep(self, configurationAttributes, step):
        print " inside getPageForStep"
        if (step == 1):
            return "/auth/inwebo/iwlogin.xhtml"
        elif (step == 2):
            return "/auth/inwebo/iwauthenticate.xhtml"
        elif (step == 3):
            return "/auth/inwebo/iwpushnotification.xhtml" 
        else:
            return ""
    
    def isPassedDefaultAuthentication(self):
        identity = CdiUtil.bean(Identity)
        credentials = identity.getCredentials()
        user_name = credentials.getUsername()
        passed_step1 = StringHelper.isNotEmptyString(user_name)
        return passed_step1

    def validateInweboToken(self, iw_api_uri, iw_service_id, user_name, iw_token, step):
        httpService = CdiUtil.bean(HttpService)
        
        request_uri = iw_api_uri + "action=authenticateExtended" + "&serviceId=" + str(iw_service_id) + "&userId=" + httpService.encodeUrl(user_name) + "&token=" + str(iw_token)+"&format=json"
        print "InWebo. Token verification. Attempting to send authentication request:", request_uri
        
        try:
            http_service_response = httpService.executeGet(self.client, request_uri)
            http_response = http_service_response.getHttpResponse()
            print "status - ", http_response.getStatusLine().getStatusCode()
        except: 
            print "inWebo validate method. Exception: ", sys.exc_info()[1]
            return False

        try:
            if (http_response.getStatusLine().getStatusCode() != 200):
                print "inWebo. Invalid response from validation server: ", str(http_response.getStatusLine().getStatusCode())
                httpService.consume(http_response)
                return None
            
            response_bytes = httpService.getResponseContent(http_response)
            response_string = httpService.convertEntityToString(response_bytes)
            httpService.consume(http_response)
        
        finally:
            http_service_response.closeConnection()
        
        if response_string is None:
            print "inWebo. Get empty response from inWebo server"
            return None
    
        print "response string:",response_string
        json_response = json.loads(response_string)
        
        #in the first step, a check is made to see if the user exists on inWebo's end
        if (step == 1):
            print "in validate method and step 1", StringHelper.equalsIgnoreCase(json_response['err'], "NOK:no device found")
            
            if StringHelper.equalsIgnoreCase(json_response['err'], "NOK:no device found"):
                print "user exists"
                return True
            else:
                print "user not found in inWebo"
                return False
        elif step == 2: 
            # in the second step we pass the token to Inwebo    
            if not StringHelper.equalsIgnoreCase(json_response['err'], "OK"):
                print "inWebo. Get response with status: ", json_response['err']
                return False
            
        return True   # response_validation

    def checkStatus(self, iw_api_uri, iw_service_id, user_name, timeout, session_id):
        # step 1: call action=pushAthenticate
        httpService = CdiUtil.bean(HttpService)
        request_uri = iw_api_uri + "action=pushAuthenticate" + "&serviceId=" + str(iw_service_id) + "&userId=" + httpService.encodeUrl(user_name) + "&format=json&withoutpin=1"
        curTime = java.lang.System.currentTimeMillis()
        endTime = curTime + (timeout * 1000)
        
        try:
            response_status = None
            http_service_response = httpService.executeGet(self.client, request_uri)
            http_response = http_service_response.getHttpResponse()
             
            if (http_response.getStatusLine().getStatusCode() != 200):
                print "inWebo. Invalid response from inwebo server: checkStatus ", str(http_response.getStatusLine().getStatusCode())
                httpService.consume(http_response)
                return None
            
            response_bytes = httpService.getResponseContent(http_response)
            response_string = httpService.convertEntityToString(response_bytes)
            httpService.consume(http_response)
        
        except: 
            print "inWebo validate method. Exception: ", sys.exc_info()[1]
            return False
    
        finally:
            http_service_response.closeConnection()
            
        print "response string:", response_string
        json_response = json.loads(response_string)

        if StringHelper.equalsIgnoreCase(json_response['err'], "OK"):
            
            session_id = json_response['sessionId']
            checkResult_uri = iw_api_uri + "action=checkPushResult" + "&serviceId=" + str(iw_service_id) + "&userId=" + httpService.encodeUrl(user_name) + "&sessionId="+ URLEncoder.encode(session_id, "UTF-8") + "&format=json&withoutpin=1"
            print "checkPushResult_uri:",checkResult_uri
            while (endTime >= curTime):
                try:
                    # step 2: call action=checkPushResult; using session id from step 1
                    http_check_push_response = httpService.executeGet(self.client, checkResult_uri)
                    check_push_response = http_check_push_response.getHttpResponse()
                    check_push_response_bytes = httpService.getResponseContent(check_push_response)
                    check_push_response_string = httpService.convertEntityToString(check_push_response_bytes)
                    httpService.consume(check_push_response)
                    
                    check_push_json_response = json.loads(check_push_response_string)
                    print "check_push_json_response :",check_push_json_response 
                    if StringHelper.equalsIgnoreCase(check_push_json_response['err'], "OK"):
                        return True
                    elif StringHelper.equalsIgnoreCase(check_push_json_response['err'], "NOK:REFUSED"):
                        print "Push request rejected for session", session_id
                        return False
                    else:
                        continue
                    java.lang.Thread.sleep(5000)
                    curTime = java.lang.System.currentTimeMillis()
                finally:
                    http_check_push_response.closeConnection()
        else:
            print "Unexpected response from server."
            return False
        
        print "inWebo. CheckStatus. The process has not received a response from the phone yet"

        return False
  
    def logout(self, configurationAttributes, requestParameters):
        return True