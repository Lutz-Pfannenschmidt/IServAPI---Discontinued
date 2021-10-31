# -*- coding: utf-8 -*-
"""
IServAPI
~~~~~~~~~~~~

IServAPI is an library to query and post from/to ISERV, written in Python.
Basic usage:

   >>> import iservapi
   >>> iserv = IServ("username", "password", "https://your_iserv.com")
   >>> iserv.login():
   >>> print( iserv.getMailFolders() )
   >>> iserv.logout()

:copyright: (c) 2021 by Lutz Pfannenschmidt.
"""
import requests
import random,string
from bs4 import BeautifulSoup
from re import findall, compile
import sys
from requests_toolbelt import MultipartEncoder
import json
from webdav3.client import Client


encoding = 'utf-8'

class colors:
    CEND      = '\33[0m'
    CBOLD     = '\33[1m'
    CITALIC   = '\33[3m'
    CURL      = '\33[4m'
    CBLINK    = '\33[5m'
    CBLINK2   = '\33[6m'
    CSELECTED = '\33[7m'

    CBLACK  = '\33[30m'
    CRED    = '\33[31m'
    CGREEN  = '\33[32m'
    CYELLOW = '\33[33m'
    CBLUE   = '\33[34m'
    CVIOLET = '\33[35m'
    CBEIGE  = '\33[36m'
    CWHITE  = '\33[37m'

    CBLACKBG  = '\33[40m'
    CREDBG    = '\33[41m'
    CGREENBG  = '\33[42m'
    CYELLOWBG = '\33[43m'
    CBLUEBG   = '\33[44m'
    CVIOLETBG = '\33[45m'
    CBEIGEBG  = '\33[46m'
    CWHITEBG  = '\33[47m'

    CGREY    = '\33[90m'
    CRED2    = '\33[91m'
    CGREEN2  = '\33[92m'
    CYELLOW2 = '\33[93m'
    CBLUE2   = '\33[94m'
    CVIOLET2 = '\33[95m'
    CBEIGE2  = '\33[96m'
    CWHITE2  = '\33[97m'

def last_param(text:list, same_line_text, split_after="="):
    """returns the last url parameter that is in the same line as 'same_line_text' .  
    ---Each line has to be in an own string in an list---  
    !!!RETURNS THE FIRST LINE WITHE THE SAME_LINE_TEXT!!!"""  

    for line in text:
        if same_line_text in line:
            s = BeautifulSoup(line.replace("\n", "").replace("  ", ""), "html.parser")
            tag = s.find('a')
            return (tag.attrs["href"].split(split_after)[-1])


def trueJson(falseJson):
    return str(falseJson).replace("'", '"').replace("True", "true").replace("False", "false")


class IServ:
    paths = {
        "login": "/iserv/app/login",
        "logout": "/iserv/app/logout",
        "tasks": "/iserv/exercise.csv",
        "vc_load": "/iserv/videoconference/api/health"
    }
    messages = {
        "login_failed": "login-form"
    }

    def __init__(self,username:str, password:str, domain:str):
        """
        Opens a new IServ session using:
        -username   :str (name.lastname)!!!NO @YOUR_ISERV.COM!!!,
        -password   :str,
        -domain     :str (https://your_iserv.com)
        """
        self._csrf_token = None
        self._session = requests.Session()
        self._username = username
        self._password = password
        self.paths = {
            "login": "/iserv/app/login",
            "logout": "/iserv/app/logout",
            "tasks": "/iserv/exercise",
            "vc_load": "/iserv/videoconference/api/health",
            "mailquery": "/iserv/mail/api/message/list?path=PATHGOESHERE&length=LENGTHGOESHERE&start=0&order%5Bcolumn%5D=date&order%5Bdir%5D=DIRECTION",
            "mailapi": "/iserv/mail/api/"
        }
        options = {
            'webdav_hostname': domain + "/webdav",
            'webdav_login':    username,
            'webdav_password': password
        }
        self.webdav = Client(options)
        self.domain = domain

    def login(self):

        r = self._session.post(
            url=self.domain + IServ.paths['login'],
            data=f"_password={self._password}&_username={self._username}",
            headers={
                "Content-Type": "application/x-www-form-urlencoded"
            }
        )

        if IServ.messages["login_failed"] in r.text:
            return False

        # Sucht nach dem CSRF Token , welches zum ausloggen benötigt wird
        self._csrf_token = self._find_csrf(r)

        # return True wenn den Login erfolgreich war
        return True

    def logout(self):
        self._session.get(
            url=self.domain + IServ.paths['logout'],
            params={"_csrf": self._csrf_token}          # Sendet das CSRF Token, welches zum abmelden benötigt wird.
        )
        return True

    @staticmethod
    def _find_csrf(doc):
        text = doc.text.split("\n")

        return(last_param(text, "logout?_csrf="))
        

    def getMailFolders(self):
        r = self._session.get(self.domain + "/iserv/mail/api/folder/list").json()

        return(trueJson(r))
    
    def getMailList(self, folder = "INBOX", length = 50, direction = "desc"):
        r = self._session.get(self.domain + self.paths["mailquery"].replace("PATHGOESHERE", folder).replace("LENGTHGOESHERE", str(length)).replace("DIRECTION", direction)).json()
        return(trueJson(r))
    
    def getMail(self, msg_uid :str, folder= "INBOX"):
        r = self._session.get(self.domain + self.paths["mailapi"] + f"message?path={folder}&msg={msg_uid}").json()
        return(trueJson(r))

    def writeMail(self, subject :str, content :str, mail_to :str):
        r = self._session.get(self.domain + "/iserv/mail/")
        s = BeautifulSoup(r.text, "html.parser")
        text = r.text.split("\n")

        mail_csrf = last_param(text, "new?csrf_token=")

        r = self._session.get(self.domain + "/iserv/mail/compose/create/new?csrf_token=" + mail_csrf)

        draftId = (r.url.split("compose/")[1].split("?")[0])
        _token = r.text.split("</form>")[0].split("<form")[-1].split("\n")[-1].split('"')[-2]

        data = {
            "iserv_mail_compose[to][]": mail_to,
            "iserv_mail_compose[subject]": subject,
            "iserv_mail_compose[files][picker][]": "",
            "iserv_mail_compose[content]": content,
            "iserv_mail_compose[actions][send]": "",
            "iserv_mail_compose[html]": "",
            "iserv_mail_compose[draftId]": draftId,
            "iserv_mail_compose[styles]": "",
            "iserv_mail_compose[_token]": _token
        }

        m = MultipartEncoder(data, boundary = '----WebKitFormBoundary' + ''.join(random.sample(string.ascii_letters + string.digits, 16)))
        r = self._session.post((self.domain + "/iserv/mail/compose/" + draftId +"?type=new"), headers={'Content-Type': m.content_type}, data=m.to_string())

        return True
        
    def getFiles(self):
        r = self._session.get(self.domain + "/iserv")
        code = last_param(r.text.split("\n"), "file.html/", "file.html/")
        r = self._session.get(self.domain + "/iserv/file.html/" + code)
        headers = {
            "accept": "application/json",
            "accept-encoding": "gzip, deflate, br"
        }
        r = self._session.get(r.url + "?_=1635447349407", allow_redirects=False, headers=headers)

        return(r.text)

    def uploadFile(self, remote_path :str, local_path :str):
        self.webdav.upload(remote_path, local_path)
    
    def downloadFile(self, remote_path :str, local_path :str):
        self.webdav.download(remote_path, local_path)









if __name__ == "__main__":
    print("please install this package")
