#!/usr/bin/python3
"""Main module for crawling the content."""

import click
import mimetypes
import os
import re
import sys
import logging
import logging.config
# import yaml

import requests
from bs4 import BeautifulSoup

from request_handler import RequestHandler
from drop_saver import DropboxSaver
from file_saver import FileSaver
from utils import Colors as clr

# Logger
LOGGER = logging.getLogger(__name__)

try:
    import secrets
except ImportError:
    if os.path.exists('secrets.py'):
        print('Secrets file exists but it is malformed. Consider to remove it and start over or figure out what is missing.')
    else:
        with open('secrets.py', 'w') as secfile:
            secfile.write(('# Maintain your credentials below. Do not remove fields you don\'t need.'
                           'USER = \'\'\nPASSWORD = \'\'\nCOURSES = []\n\n'
                           '# $ Required if you want to download files to a local folder (for example to the Dropbox client)\n'
                           'PATH = \'\'  # Path to the destination folder\n\n'
                           '# $ Required if you want to download files and upload them to Dropbox\n'
                           'DROPBOX_TOKEN = \'\'  # Personal Dropbox API token\n'
                           'PATH_IN_DB = \'\'  # Destination path of downloaded files within your Dropbox\n'))
        print('File secrets.py was created. Please maintain your credentials.')
        sys.exit(1)


class Crawler:
    """A crawler for downloading university e-learning content."""

    def __init__(self, dropbox):
        self.courses = secrets.COURSES
        self.count = 0
        self.removed_label_flag = False
        self.new_downloads = []
        self.req_handler = RequestHandler(secrets.USER, secrets.PASSWORD)
        if dropbox:
            self.save_handler = DropboxSaver(secrets.PATH_IN_DB, secrets.DROPBOX_TOKEN)
        else:
            self.save_handler = FileSaver(secrets.PATH)

    def __str__(self):
        if not self.count:
            return '{}Files were already up to date.{}'.format(clr.BOLD, clr.ENDC)
        else:
            return '{}{}{} new file{} downloaded from ILIAS.{}'.format(clr.BOLD, clr.GREEN, str(self.count), ('s' if self.count != 1 else ''), clr.ENDC)

    def run(self):
        """Loop through top level courses and crawl the content for every course."""
        try:
            response = self.req_handler.post_request()
        except requests.exceptions.ConnectionError as e:
            sys.stderr.write('{}\n\n{}\n'.format(e, 'A ConnectionError occurred. Please check your internet connection.'))
            sys.exit(1)

        html_text = response.text
        if 'Anmeldedaten wurden nicht akzeptiert' in html_text:  # has to be done this way, because http response on failed auth is 200 - OK.
            sys.stderr.write('Authorization @CAS failed.\nPlease maintain user and password correctly.\n')
            sys.exit(1)

        soup_courses = BeautifulSoup(html_text, 'html.parser')
        for soup_course in soup_courses.findAll('a', {'class': 'il_ContainerItemTitle'}):
            course_name = self.course_contains(soup_course.string)
            relative_link = soup_course.get('href')
            course_url = 'https://ilias.uni-mannheim.de/' + relative_link

            if course_name is not None:
                self.crawl_course(course_url, course_name + '/')
            else:
                print('{}No download requested for course >> {}{}'.format(clr.BOLD, clr.ENDC, soup_course.string.lstrip()))

        print(self)

    def crawl_course(self, course_url, folder_path):
        """Recursively call this method until there is something to download for this course in the respective path."""
        html_text_course = self.req_handler.session.get(course_url).text
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
                item_properties = container.find('div', {'class': 'ilListItemSection il_ItemProperties'})
                if item_properties is not None:
                    item_prop = item_properties.find_all('span', {'class', 'il_ItemProperty'})
                    properties = [prop.string.strip().split() for prop in item_prop if prop.string is not None]
                    if properties:
                        file_ending = properties[0][0]

                if 'download' in link:
                    self.save_handler.create_folder(folder_path)
                    self.prepare_saving(folder_path, soup_line.string, file_ending, link)
                else:
                    self.crawl_course('https://ilias.uni-mannheim.de/' + link,
                                      folder_path + self.remove_edge_characters(soup_line.string))
        else:
            print('{}no_files_in: {}{}'.format(clr.LIGHTGREY, str(folder_path), clr.ENDC))

    def prepare_saving(self, folder_path, filename, file_ending, url):
        """Prepare the file to be saved. Remove edge characters, trim and add the correct file ending."""
        # remove edge characters and trim
        filename = re.sub(r'[&]', 'and', filename)
        filename = re.sub(r'[!@#$/\:;*?<>|]', '', filename).strip()

        http_header = self.req_handler.session.head(url, headers={'Accept-Encoding': 'identity'})
        file_size = http_header.headers['content-length']
        relative_path = folder_path + filename + '.'

        if file_ending:
            relative_path += file_ending
        else:
            relative_path += str(mimetypes.guess_extension(http_header.headers['content-type']))

        if float(file_size) >= 3E7:  # Skip # 2E8: 200.000.000 Bytes; 5E7: 30 MB
            print('{}file_skipped{} {}'.format(clr.BLUE, clr.ENDC, relative_path))
        elif self.save_handler.exists(relative_path):  # Exists
            print('file_exists: ' + relative_path)
        else:  # Download
            content = self.req_handler.session.get(url).content
            self.save_handler.save_file(relative_path, content, file_size)
            print('{}: {} from {}'.format('{}downloading{}'.format(clr.BOLD, clr.ENDC), relative_path, url))

    def course_contains(self, original):
        """Check in the config data whether the user wants to download content for this course."""
        for name in self.courses:
            compiler = re.compile(name)

            if compiler.search(original) is not None:
                return name

        return None

    def remove_edge_characters(self, line):
        r"""Replaces all !@#$/\:;*?<>| with _
            Dateien/ will be removed from the string (which would lead to duplicate print of folder_path without removed_label_flag)"""
        parse_edge_characters = re.sub(r'[!@#$/\:;*?<>|]', '_', line) + '/'
        if parse_edge_characters == 'Dateien/':
            self.removed_label_flag = True
            return ''
        else:
            self.removed_label_flag = False
            return parse_edge_characters


@click.command()
@click.option('-d', '--dropbox', is_flag=True, help=('Whether to use the Dropbox API.'
                                                     'This is not necessary if you have Dropbox installed on your host machine.'))
def cli(dropbox):
    try:
        Crawler(dropbox).run()
    except KeyboardInterrupt:
        sys.stderr.write(' {}{}KeyboardInterrupt. Crawler terminated.{}\n'.format(clr.BOLD, clr.RED, clr.ENDC))
        sys.exit(1)


if __name__ == '__main__':
    cli()

# try:
#     with open('../logs/logging.yaml', 'rt') as f:
#         logging.config.dictConfig(yaml.safe_load(f.read()))
# except (FileNotFoundError, Exception) as e:
#     sys.stderr.write('{}\nDefault logging configuration enabled.\n'.format(e))
#     logging.basicConfig(level=logging.INFO)
