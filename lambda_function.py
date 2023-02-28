import requests, json
from datetime import datetime
import os
import urllib.parse

def logToTelegram(event, message):
    today = datetime.now()
    params = {'chat_id': '88212345', 'text': f"```\n-[{event}][{today}]:{message}```", "parse_mode":"MarkdownV2"}
    query =  urllib.parse.urlencode(params, safe='')
    readUrl = f"https://api.telegram.org/bot{os.environ['telegram_bot']}/sendMessage?{query}"

    res = requests.request("GET", readUrl, headers=headers)

def readDatabase(databaseId, headers):
    readUrl = f"https://api.notion.com/v1/databases/{databaseId}/query"

    res = requests.request("POST", readUrl, headers=headers)
    data = res.json()
    return data
    
def createPage(databaseId, headers, newInput):

    createUrl = 'https://api.notion.com/v1/pages'

    newPageData = {
        "parent": { "database_id": databaseId },
        "properties": {
            "Name": {
                "title": [
                    {
                        "text": {
                            "content": newInput['token']
                        }
                    }
                ]
            },
            "owner": {
                "rich_text": [
                    {
                        "text": {
                            "content": newInput['owner']
                        }
                    }
                ]
            },
            "username": {
                "rich_text": [
                    {
                        "text": {
                            "content": newInput['username']
                        }
                    }
                ]
            },
            "Status": {
                "select":  {
                  "id": "36825eac-0d1d-4802-b722-17f3276961bc",
                  "name": "Free",
                  "color": "green"
                },
        
            },
             "expire": {
                "date":  {
                  "start":newInput['expireAt'].strftime('%Y-%m-%d')
                },
        
            },
            "Tags":{
                "multi_select":[
                    {
                      "id": "5a6a6ab5-e33c-4c47-9f7e-a670f5a2d7e3",
                      "name": "Github",
                      "color": "red"
                    },
                    {
                      "id": "e552a430-6bc8-4487-aa2c-18d184c44447",
                      "name": "token",
                      "color": "brown"
                    }
                ]
            }
        }
    }
    
    data = json.dumps(newPageData)
    # print(str(uploadData))

    res = requests.request("POST", createUrl, headers=headers, data=data)

    return res.json()
    
def get_db_schema(databaseId,headers):
    url = f"https://api.notion.com/v1/databases/{databaseId}"
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        database_schema = response.json()["properties"]
        print(database_schema)
    else:
        print("Failed to retrieve database schema")
    return database_schema



def markAsExpired(pageId, headers):
    updateUrl = f"https://api.notion.com/v1/pages/{pageId}"
    status_code =  {
          "name": "expired",
        }
    updateData = {
        "properties": 
        {
            "Status": 
            {
                "select":  status_code
            }
        }
    }

    data = json.dumps(updateData)

    response = requests.request("PATCH", updateUrl, headers=headers, data=data)

    return response.json()


def updatePage(pageId, headers, markAsBusy):
    updateUrl = f"https://api.notion.com/v1/pages/{pageId}"
    redStat =  {
          "id": "48a8edc9-c996-46e7-ab67-a29f79d58887",
          "name": "In Use",
          "color": "red"
        };
    greenStat = {
          "id": "36825eac-0d1d-4802-b722-17f3276961bc",
          "name": "Free",
          "color": "green"
        }
    status_code = redStat if markAsBusy else greenStat
    updateData = {
        "properties": 
        {
            "Status": 
            {
                "select":  status_code
            }
        }
    }

    data = json.dumps(updateData)

    response = requests.request("PATCH", updateUrl, headers=headers, data=data)

    return response.json()
    
def isTokenInUse(username,token):
    response = requests.head(
        'https://api.github.com/user/repos',
        auth=(username, token),
    )
    data = response.headers
    if int(data['x-ratelimit-limit']) == 0 or int(data['x-ratelimit-used']) >= 10 : # we cut them some slack here!
        return True
    return False

def isTokenValid(username,token):
    try:
        response = requests.head(
            'https://api.github.com/user/repos',
            auth=(username, token),
        )
        data = response.headers
        logToTelegram("dasd",data['github-authentication-token-expiration'])
        expireDate = datetime.strptime(data['github-authentication-token-expiration'],"%Y-%m-%d %H:%M:%S %z").replace(tzinfo=None)
        today = datetime.now()
        if expireDate <= today:
            return False
        
        if int(data['x-ratelimit-limit']) > 60:
            return expireDate
            
    except Exception as e:
        logToTelegram("error", f"error in isTokenValid:{e}")
        return False

def isTokenUnique(databaseId, headers, username, token):
    query = {
        "and": [
            {
                "property": "Name",
                "rich_text": {
                    "equals":token,
                }
            },
            {
                "property": "username",
                "rich_text": {
                    "equals":username,
                }
            }
        ]
    }
    print(query)

    response = requests.post(
        f"https://api.notion.com/v1/databases/{databaseId}/query",
        headers=headers,
        json={
            "filter": query
        }
    )
    pages= []
    print(response.text)
    if response.status_code == 200:
        pages = response.json().get("results")
    print(pages)
    return len(pages) == 0


def updateListStatus(event, context):   
    # token = '**RMOMOVED**'

    # databaseId = '**RMOMOVED**'
    
    # headers = {
    #     "Authorization": "Bearer " + token,
    #     "Content-Type": "application/json",
    #     "Notion-Version": "2021-05-13"
    # }
    
    tokens = readDatabase(databaseId,headers)
    
    today = datetime.now()
    for token in tokens['results']:
        pageId = token['id']
        expireDate =  datetime.strptime(token['properties']['expire']['date']['start'], '%Y-%m-%d') 
        if expireDate <  today:
            markAsExpired(pageId, headers)
            continue
        isInUse = isTokenInUse(
            token['properties']['username']['rich_text'][0]['text']['content'],
            token['properties']['Name']['title'][0]['text']['content']
        )
        updatePage(pageId, headers,isInUse)

    return {
            'statusCode': 200,
            'body': json.dumps({"message":"Success"})
    };

token = os.environ['notion_token']

databaseId = os.environ['notion_db_id']

headers = {
    "Authorization": "Bearer " + token,
    "Content-Type": "application/json",
    "Notion-Version": "2021-05-13"
}
def lambda_handler(event, context):
    try:
        isUpdate = event['queryStringParameters']['update_status']
        if isUpdate!="secret":
            raise Exception("Not update!")
        try:
            logToTelegram("update status","updating status started")
            return updateListStatus(event,context)
        except:
            logToTelegram("error","updating status failed")
            return {"statusCode":500,"boddy":{"message":"updating error"}}
    except:
        print("user request recorded!")
        
    if "body" in event:
        logToTelegram("Add Token", f"Adding new token\n input:{json.dumps(event['body'])}")
        info = json.loads(event['body'])
        print('info', info)
        # try:
        tokenNotExist = isTokenUnique(databaseId, headers, info['username'],info['token'])
        if not tokenNotExist:
            return {"statusCode":400, "body":{"message": "Token already Exist"}}
            
        tokenIsValid = isTokenValid(info['username'],info['token'])
        logToTelegram("Add Token",f"Validation:{tokenIsValid}")
        if not tokenIsValid:
            return {"statusCode":400, "body":{"message": "Token is not valid"}}
            
        info['expireAt']=tokenIsValid
        logToTelegram("Add Token",f"Token Validated:({info['username']},{info['token']})")

        record = createPage(databaseId,headers, info)
        # database = get_db_schema(databaseId,headers)
        if record['id']:
            logToTelegram("Add Token",f"Add successfully!")
            return {"statusCode":200, "body":{"message": "Success"}}
                
        # except Exception as e:
        #     print(e)
        #     logToTelegram("error",f"Add token failed!")
        #     pass
        return {"statusCode":500,  "body":{"message": "Failure"}}
    else:
        logToTelegram("list token",f"List tokens started!")
        # return  get_db_schema(databaseId,headers)
        PASSWORD = os.environ['PASS']
        # try:
        inputPassword= event['queryStringParameters']['passcode']
        # except:
        #     return {"statusCode":403,  "body":{"message": "Incorrect password!"}}
        print(inputPassword)
        if inputPassword != PASSWORD:
            return {"statusCode":403,  "body":{"message": "Incorrect password!"}}
            
        tokens = readDatabase(databaseId,headers)
        tokenList = []
        for token in tokens['results']:
            tokenList.append((
                token['properties']['username']['rich_text'][0]['text']['content'],
                token['properties']['Name']['title'][0]['text']['content']
            ))
        logToTelegram("list token",f"List prepared successfully!")
        return {
            'statusCode': 200,
            'body': json.dumps(tokenList)
        }
