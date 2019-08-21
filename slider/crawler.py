#!/usr/bin/python3
"""Main module for crawling the content."""

from datetime import datetime
import hashlib
import mimetypes
import os
import re
import shutil
import sys

from bs4 import BeautifulSoup
from requests.exceptions import ConnectionError
import click

from database import Database
from request import RequestHandler
from save_file import FileSaver
from save_drop import DropboxSaver
from util import Colors as clr
import util

SECRETS_FILE = 'app_secrets.py'
CHLOG_FOLDER = '.changelog/'

try:
    import app_secrets as secrets
except ImportError:
    if not os.path.exists(SECRETS_FILE):
        util.create_secrets(SECRETS_FILE)
    else:
        print('app_secrets file is malformed. Please start over.')
        shutil.rm(SECRETS_FILE)
        sys.exit(1)


class Crawler:
    """A crawler for downloading university e-learning content."""
    def __init__(self, dropbox, logall, mail, maxsize):
        self.dropbox = dropbox
        self.logall = logall
        self.sendmail = mail
        self.maxsize = maxsize

        if self.dropbox:
            self.save_path = secrets.PATH_IN_DB
            self.file_handler = DropboxSaver(self.save_path, secrets.DROPBOX_TOKEN)
        else:
            self.save_path = secrets.PATH
            self.file_handler = FileSaver(self.save_path)

        self.req = RequestHandler(secrets.USER, secrets.PASSWORD)
        self.file_handler.create_folder(CHLOG_FOLDER)
        self.database = Database(self.file_handler, self.dropbox)

        self.courses = secrets.COURSES
        self.removed_label_flag = False
        self.downloads = []
        self.changelog = []

    def __str__(self):
        if not self.downloads:
            return 'Files were already up to date.'
        else:
            s = 's' if len(self.downloads) != 1 else ''
            d = 'DROPBOX/' if self.dropbox else ''
            p = d + self.save_path
            restr = '{} new file{} downloaded from ILIAS to {}.'.format(str(len(self.downloads)), s, p)
            return restr

    def run(self):
        """Main entry point."""
        # authentication
        try:
            response = self.req.login()
            html_text = response.text
        except ConnectionError as err:
            print(err, 'A ConnectionError occurred. Please check your internet connection.', sep='\n')
            sys.exit(1)

        # check whether authentication worked;
        # has to be done this way since HTTP response
        # on failed authentication is 200 - OK.
        auth_failed_msg = 'Anmeldedaten wurden nicht akzeptiert'
        if auth_failed_msg in html_text:
            print('Authorization failed. Please maintain user and password correctly.')
            sys.exit(1)

        # crawl courses
        self.crawl(html_text)

        # wrap up: close database, write changelog and send mail
        self.database.close(self.file_handler, self.dropbox, True)
        self.write_changelog()
        if self.sendmail and self.downloads:
            self.req.send_mail(self, self.downloads)

        # print download stats
        clrone = clr.BOLD
        clrtwo = clr.GREEN if self.downloads else clr.ENDC
        clrend = clr.ENDC
        print(clrone, clrtwo, self, clrend, sep='')

    def crawl(self, html_text):
        """Loop through top level courses and crawl the content for every course."""
        soup_courses = BeautifulSoup(html_text, 'html.parser')

        for soup_course in soup_courses.findAll('a', {'class': 'il_ContainerItemTitle'}):
            scs = soup_course.string
            course_name = util.course_contains(scs, self.courses)
            relative_link = soup_course.get('href')
            course_url = 'https://ilias.uni-mannheim.de/' + relative_link

            if course_name is not None:
                self.crawl_course(course_url, course_name + '/')
            else:
                print(clr.BOLD, 'No download requested for course >> ', clr.ENDC, scs.lstrip(), sep='')

    def crawl_course(self, course_url, folder_path):
        """Recursively call this method until there is something to download
           for this course in the respective path."""
        html_text_course = self.req.session.get(course_url).text
        soup_course = BeautifulSoup(html_text_course, 'html.parser')
        containers = soup_course.find_all('div', {'class': 'il_ContainerListItem'})

        if containers:
            if not self.removed_label_flag:
                util.print_method('folder_path', folder_path)

            for container in containers:
                file_ending = ''
                soup_line = container.find('a', {'class': 'il_ContainerItemTitle'})
                if soup_line:
                    link = soup_line.get('href')
                else:
                    continue
                item_properties = container.find('div', {'class': 'ilListItemSection il_ItemProperties'})
                if item_properties is not None:
                    item_prop = item_properties.find_all('span', {'class', 'il_ItemProperty'})
                    properties = [str(prop.string.strip()) for prop in item_prop if prop.string is not None]
                    if properties:
                        file_ending = properties[0]
                        last_update = properties[2]
                        # 22. May 2019, 14:15 ->2019-05-22 14:15:00
                        d = datetime.strptime(last_update, '%d. %b %Y, %H:%M')
                        # 201905221415
                        last_update = d.strftime('%Y%m%d%H%M')

                if 'download' in link:
                    self.file_handler.create_folder(folder_path)
                    self.check_save(folder_path, soup_line.string, file_ending, last_update, link)
                else:
                    parsed = util.remove_edge_characters(soup_line.string)
                    if not parsed:
                        self.removed_label_flag = True
                    self.crawl_course('https://ilias.uni-mannheim.de/' + link, folder_path + parsed)
        else:
            util.print_method('no_files_in', str(folder_path))

    def check_save(self, folder_path, filename, file_ending, last_update, url):
        """Prepare the file to be saved. Remove edge characters,
           trim and add the correct file ending."""
        # remove edge characters and trim
        filename = re.sub(r'[&]', 'and', filename)
        filename = re.sub(r'[!@#$/\:;*?<>|]', '', filename).strip()

        http = self.req.session.head(url, headers={'Accept-Encoding': 'identity'})
        file_size = http.headers['content-length']
        if not file_ending:
            file_ending = str(mimetypes.guess_extension(http.headers['content-type']))

        relative_file = folder_path + filename
        relative_path = relative_file + '.' + file_ending

        # for printing what is done with that file
        clrone = clr.ENDC
        clrtwo = clr.ENDC
        method = ''
        messag = relative_path

        # query db for path and update
        res_pu = self.database.get_name_update(relative_path, last_update)

        # example file sizes 2E8: 200.000.000 Bytes; 5E7: 30 MB
        if float(file_size) >= self.maxsize:  # Skip
            clrone = clr.BLUE
            method = 'file_skiped'
        # if db contains entry with path and update, file was already downloaded
        elif res_pu:  # exists
            method = 'loaded_once'
        else:
            # download file to compute hash
            content = self.req.session.get(url).content
            # compute content hash
            content_hash = hashlib.sha1(content).hexdigest()

            # query db for hash
            res_h = self.database.get_hash(content_hash)
            # filename or last update may have changed but hash exists
            # thus file is known and was already downloaded
            if res_h:  # exists
                method = 'loaded_once'
            else:
                # query db for name
                res_p = self.database.get_name(relative_path)
                # if this name already exists in the database
                # must be an update because otherwise the name + last_update
                # or the hash should have been in the db already
                if res_p:
                    method = 'file_update'
                    clrone = clr.GREEN
                    relative_path = '{}_UP{}.{}'.format(relative_file, content_hash[:4], file_ending)
                    messag = relative_path
                # not an update: new file
                else:
                    # check if this filename exists already at the destination path
                    # should not happen unless user renamed file to exactly this downloaded file name
                    # check also only exists to inform user that file is not just overwritten
                    # but safely moved to the .overwritten/ folder
                    exists = self.file_handler.exists(relative_path)
                    if not exists:
                        method = 'downloading'
                        clrone = clr.BOLD
                    else:
                        method = 'safe_overwr'
                        clrone = clr.RED
                    messag = relative_path + ' from ' + url
                saved = self.file_handler.save_file(relative_path, content)
                if saved:
                    self.database.insert(relative_path, content_hash, last_update)
                    self.downloads.append(relative_path)

        if method != ('file_skiped' and 'loaded_once') or self.logall:
            self.changelog.append(str(method + ': ' + messag))

        util.print_method(method, messag, clrone, clrtwo)

    def write_changelog(self):
        """Write a changelog to /chosen_dir/.changelog/changelog_{datetime}."""
        if not self.changelog:
            return
        d = datetime.today().strftime('%Y-%m-%d_%H-%M-%S')
        tmp = '# Changelog from {}\n'.format(d)
        tmp += str(len(tmp) * '-') + '\n'
        tmp += '\n'.join(self.changelog) + '\n'
        b = tmp.encode('utf-8')
        self.file_handler.save_file(CHLOG_FOLDER + 'changelog_{}.txt'.format(d), b, mute=True)


@click.command()
@click.option('-d', '--dropbox', is_flag=True, help='Upload files using Dropbox API (requires access token).')
@click.option('-l', '--logall', is_flag=True, help='Log everything to the changelog, not just downloads.')
@click.option('-m', '--mail', is_flag=True, help='Send an email if there are new downloads.')
@click.option('-x', '--maxsize', default=5E7, help='Define the maximum size of a file to be downloaded.')
def cli(dropbox, logall, mail, maxsize):
    crawler = Crawler(dropbox, logall, mail, maxsize)
    try:
        crawler.run()
    except KeyboardInterrupt as kie:
        print(kie, '\n', clr.BOLD, clr.RED, 'KeyboardInterrupt. Crawler terminated.', clr.ENDC, sep='')
        sys.exit(1)


if __name__ == '__main__':
    cli()
