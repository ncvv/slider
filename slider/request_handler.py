"""Handler module for requests and user specific configuration data."""

import re
import sys

import requests

# Url for accessing Ilias
ILIAS_URL = 'https://cas.uni-mannheim.de/cas/login?service=https%3A%2F%2Filias.uni-mannheim.de%2Filias.php%3FbaseClass%3DilPersonalDesktopGUI%26cmd%3DjumpToSelectedItems'


class RequestHandler:
    """Handler Class for the HTTP requests."""
    def __init__(self, user, password):
        self.session = requests.Session()
        self.username = user
        self.password = password
        if not self.username or not self.password:
            print('Maintain credentials in secrets.py first.')
            sys.exit(1)

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
