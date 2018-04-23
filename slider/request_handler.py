"""Handler module for requests and user specific configuration data."""

# import os
# import json
import re
import sys

import requests

try:
    from secrets import USER, PASSWORD, DROPBOX_TOKEN, PATH_IN_DB, COURSES  # , PATH_TO_DB
except ImportError:
    with open('secrets.py', 'w') as secfile:
        secfile.write('USER = \'\'\nPASSWORD = \'\'\n\nDROPBOX_TOKEN = \'\'\n\nPATH_TO_DB = \'\'\nPATH_IN_DB = \'\'\nCOURSES = []')
    print('File secrets.py was missing and thus created.')
    sys.exit(1)

# Url for accessing Ilias
ILIAS_URL = 'https://cas.uni-mannheim.de/cas/login?service=https%3A%2F%2Filias.uni-mannheim.de%2Filias.php%3FbaseClass%3DilPersonalDesktopGUI%26cmd%3DjumpToSelectedItems'


class RequestHandler:
    """Handler Class for the HTTP requests."""

    def __init__(self):
        self.session = requests.Session()

        self.username = USER
        self.password = PASSWORD
        self.token = DROPBOX_TOKEN

        if not self.username or not self.password or not self.token:
            print('Maintain keys in secrets.py first.')
            sys.exit(1)

        self.course_names = COURSES
        self.path = PATH_IN_DB

    def get_request(self):
        """HTTP GET request for getting cookies."""
        get_re = requests.get(ILIAS_URL)
        cookies = get_re.cookies
        lt_ = re.findall('(LT-.*?)\"', get_re.text)[0]
        return [lt_, cookies]

    def post_request(self):
        """HTTP POST request to login and get the HTML response from Ilias for crawling."""
        get_request_list = self.get_request()
        lt_ = get_request_list[0]
        cookies = get_request_list[1]
        payload = {
            'username': self.username,
            'password': self.password,
            'lt': lt_,
            'execution': 'e1s1',
            '_eventId': 'submit',
            'submit': 'Anmelden'
        }
        response = self.session.post(ILIAS_URL, data=payload, cookies=cookies)
        return response
