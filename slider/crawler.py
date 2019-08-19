#!/usr/bin/python3
"""Main module for crawling the content."""

import os
import re
import sys
import hashlib
import mimetypes
from datetime import datetime

import click
import requests
from requests.exceptions import ConnectionError
from bs4 import BeautifulSoup

import util
from util import Colors as clr
from file_saver import FileSaver
from drop_saver import DropboxSaver
from request_handler import RequestHandler
from data import Database


CHLOG_FOLDER = '.changelog/'


try:
    import secrets
except ImportError:
    if not os.path.exists('secrets.py'):
        util.create_secrets_file()
    else:
        print('Secrets file exists but it is malformed. '
              'Consider to remove it and start over or figure out what is missing.')


class Crawler:
    """A crawler for downloading university e-learning content."""
    def __init__(self, dropbox, maxsize, logall):
        self.dropbox = dropbox
        self.maxsize = maxsize
        self.logall = logall

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
        self.count = 0
        self.downloads = []
        self.changelog = []

    def __str__(self):
        if not self.count:
            return '{}Files were already up to date.{}'.format(clr.BOLD, clr.ENDC)
        else:
            return '{}{}{} new file{} downloaded from ILIAS to {}.{}'.format(
                clr.BOLD, clr.GREEN, str(self.count), ('s' if self.count != 1 else ''),
                self.save_path, clr.ENDC)

    def run(self):
        """Loop through top level courses and crawl the content for every course."""
        try:
            response = self.req.post_request()
        except ConnectionError as err:
            sys.stderr.write('{}\n\n{}\n'.format(
                err, 'A ConnectionError occurred. '
                'Please check your internet connection.'))
            sys.exit(1)

        html_text = response.text
        # Has to be done this way since http response on failed auth is 200 - OK.
        if 'Anmeldedaten wurden nicht akzeptiert' in html_text:
            sys.stderr.write('Authorization @CAS failed.\n'
                             'Please maintain user and password correctly.\n')
            sys.exit(1)

        soup_courses = BeautifulSoup(html_text, 'html.parser')
        for soup_course in soup_courses.findAll('a', {'class': 'il_ContainerItemTitle'}):
            course_name = util.course_contains(soup_course.string, self.courses)
            relative_link = soup_course.get('href')
            course_url = 'https://ilias.uni-mannheim.de/' + relative_link

            if course_name is not None:
                self.crawl_course(course_url, course_name + '/')
            else:
                print('{}No download requested for course >> {}{}'.format(
                    clr.BOLD, clr.ENDC, soup_course.string.lstrip()))

        self.database.close(self.file_handler, self.dropbox, True)
        self.write_changelog()
        print(self)

    def crawl_course(self, course_url, folder_path):
        """CRecursively call this method until there is something to download
           for this course in the respective path."""
        html_text_course = self.req.session.get(course_url).text
        soup_course = BeautifulSoup(html_text_course, 'html.parser')
        containers = soup_course.find_all('div', {'class': 'il_ContainerListItem'})

        if containers:
            if not self.removed_label_flag:
                print('folder_path: ' + folder_path)

            for container in containers:
                file_ending = ''
                soup_line = container.find('a', {'class': 'il_ContainerItemTitle'})
                if soup_line:
                    link = soup_line.get('href')
                else:
                    continue
                item_properties = container.find('div',
                                                 {'class': 'ilListItemSection il_ItemProperties'})
                if item_properties is not None:
                    item_prop = item_properties.find_all('span', {'class', 'il_ItemProperty'})
                    properties = [
                        prop.string.strip().split() for prop in item_prop if prop.string is not None
                    ]
                    if properties:
                        file_ending = properties[0][0]

                if 'download' in link:
                    self.file_handler.create_folder(folder_path)
                    self.prepare_saving(folder_path, soup_line.string, file_ending, link)
                else:
                    parsed = util.remove_edge_characters(soup_line.string)
                    if not parsed:
                        self.removed_label_flag = True
                    self.crawl_course('https://ilias.uni-mannheim.de/' + link, folder_path + parsed)
        else:
            print('{}no_files_in: {}{}'.format(clr.LIGHTGREY, str(folder_path), clr.ENDC))

    def prepare_saving(self, folder_path, filename, file_ending, url):
        """Prepare the file to be saved. Remove edge characters, trim and add the correct file ending."""
        # Remove edge characters and trim
        filename = re.sub(r'[&]', 'and', filename)
        filename = re.sub(r'[!@#$/\:;*?<>|]', '', filename).strip()

        http_header = self.req.session.head(url, headers={'Accept-Encoding': 'identity'})
        file_size = http_header.headers['content-length']
        relative_path = folder_path + filename + '.'

        if file_ending:
            relative_path += file_ending
        else:
            relative_path += str(mimetypes.guess_extension(http_header.headers['content-type']))

        msg = {'clrone': clr.ENDC, 'clrtwo': clr.ENDC, 'method': '--', 'messag': relative_path}
        content = self.req.session.get(url).content
        content_hash = hashlib.sha1(content).hexdigest()
        already_exists = self.database.get(content_hash)
        if float(file_size) >= self.maxsize:  # Skip # 2E8: 200.000.000 Bytes; 5E7: 30 MB
            msg['clrone'] = clr.BLUE
            msg['method'] = 'file_skiped'
        elif already_exists:  # self.file_handler.exists(relative_path):  # Exists
            msg['method'] = 'file_exists'
        else:  # Download
            saved = self.file_handler.save_file(relative_path, content)
            if saved:
                self.database.insert(relative_path, content_hash)
                self.downloads.append(relative_path)
                self.count += 1
                msg['clrone'] = clr.BOLD
                msg['method'] = 'downloading'
                msg['messag'] = '{} from {}'.format(relative_path, url)
        method = '{}{}:{} {}'.format(msg['clrone'], msg['method'], msg['clrtwo'], msg['messag'])
        if msg['method'] == 'download' or self.logall:
            self.changelog.append('{}: {}'.format(msg['method'], msg['messag']))
        print(method)

    def write_changelog(self):
        """Write a changelog to /chosen_dir/.changelog/changelog_{datetime}."""
        d = datetime.today().strftime('%Y-%m-%d_%H-%M-%S')
        tmp = '# Changelog from {}\n'.format(d)
        tmp += str(len(tmp) * '-')
        tmp += '\n'.join(self.changelog) + '\n'
        b = tmp.encode('utf-8')
        self.file_handler.save_file(CHLOG_FOLDER + 'changelog_{}.txt'.format(d), b)


@click.command()
@click.option('-d',
              '--dropbox',
              is_flag=True,
              help='Upload files using the Dropbox API. Requires a Dropbox API token.')
@click.option('-m',
              '--maxsize',
              default=5E7,
              help='Define the maximum allowed size of a file to be downloaded.')
@click.option('-l',
              '--logall',
              is_flag=True,
              help='Log everything to the changelog, not just downloads.')
def cli(dropbox, maxsize, logall):
    try:
        crawler = Crawler(dropbox, maxsize, logall)
        crawler.run()
    except KeyboardInterrupt as kie:
        sys.stderr.write('{}\n\n {}{}KeyboardInterrupt. Crawler terminated.{}\n'.format(
            kie, clr.BOLD, clr.RED, clr.ENDC))
        sys.exit(1)


if __name__ == '__main__':
    cli()
