"""Handler module for requests and user specific configuration data."""

import re
import smtplib
from datetime import datetime

import requests

# Url for accessing Ilias
ILIAS_URL = 'https://cas.uni-mannheim.de/cas/login?service=https%3A%2F%2Filias.uni-mannheim.de%2Filias.php%3FbaseClass%3DilPersonalDesktopGUI%26cmd%3DjumpToSelectedItems'


class RequestHandler:
    """Handler Class for the HTTP requests."""
    def __init__(self, user, password):
        self.session = requests.Session()
        self.username = user
        self.password = password
        self.mail = self.username + '@mail.uni-mannheim.de'

    def get_login_cookies(self):
        """HTTP GET request for getting cookies."""
        response = requests.get(ILIAS_URL)
        cookies = response.cookies
        lt = re.findall('(LT-.*?)\"', response.text)[0]
        return lt, cookies

    def login(self):
        """HTTP POST request to login and get
           the HTML response from Ilias for crawling."""
        lt, cookies = self.get_login_cookies()
        payload = {
            'username': self.username,
            'password': self.password,
            'lt': lt,
            'execution': 'e1s1',
            '_eventId': 'submit',
            'submit': 'Anmelden'
        }
        response = self.session.post(ILIAS_URL, data=payload, cookies=cookies)
        return response

    def send_mail(self, subject, new_lst, newlen):
        """Send an email via Uni Mannheim smtp server.
           Content of the mail in new_lst is every
           new academic record since last run of the program."""
        # Mail headers
        headers = {
            'Content-Type': 'text/plain; charset=utf-8',
            'Content-Disposition': 'inline',
            'Content-Transfer-Encoding': '8bit',
            'From': self.mail,
            'To': self.mail,
            'Date': datetime.now().strftime('%a, %d %b %Y  %H:%M:%S %Z'),
            'Subject': str(subject)
        }

        # Mail content
        message = ''
        for h, v in headers.items():
            message += '{}: {}\n'.format(h, v)
        recs_new = '\n'.join(map(str, new_lst))
        message += '\n{}\n'.format(recs_new)

        # Send email
        server = smtplib.SMTP('smtp.mail.uni-mannheim.de', 587)
        server.starttls()
        server.login(self.mail, self.password)
        server.sendmail(self.mail, self.mail, message)
        server.quit()
