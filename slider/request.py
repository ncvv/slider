"""Handler module for requests and user specific configuration data."""

from datetime import datetime
import re
import smtplib
import urllib.parse

import requests

# URL for accessing Ilias
ILIAS_URL = 'https://cas.uni-mannheim.de/cas/login?' \
            'service=https://ilias.uni-mannheim.de/ilias.php?' \
            'baseClass=ilPersonalDesktopGUI&cmd=jumpToSelectedItems'


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
        url = urllib.parse.quote_plus(ILIAS_URL)
        response = self.session.post(url, data=payload, cookies=cookies)
        return response

    def send_mail(self, subject, new_lst):
        """Send an email via Uni Mannheim smtp server.
           Content of the mail in new_lst is every
           new academic record since last run of the program."""
        # mail headers
        headers = {
            'Content-Type': 'text/plain; charset=utf-8',
            'Content-Disposition': 'inline',
            'Content-Transfer-Encoding': '8bit',
            'From': self.mail,
            'To': self.mail,
            'Date': datetime.now().strftime('%a, %d %b %Y  %H:%M:%S %Z'),
            'Subject': str(subject)
        }

        # mail content
        message = ''
        for h, v in headers.items():
            message += '{}: {}\n'.format(h, v)
        recs_new = '\n'.join(map(str, new_lst))
        message += '\n{}\n'.format(recs_new)

        # send email
        server = smtplib.SMTP('smtp.mail.uni-mannheim.de', 587)
        server.starttls()
        server.login(self.mail, self.password)
        server.sendmail(self.mail, self.mail, message)
        server.quit()
