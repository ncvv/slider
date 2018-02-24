#!/usr/bin/python3
'''Main module for crawling the content.'''

__version__ = '1.3'
__author__ = 'Nicolas Wipfler'

import io
import os
import mimetypes
import re
import sys
import logging

import requests
import dropbox
from bs4 import BeautifulSoup

import request_handler

#logging.basicConfig(level=logging.INFO)
#logger = logging.getLogger(__name__)

# Chunk size for uploading large files to Dropbox
CHUNK_SIZE = 32 * 1024 * 1024

class Colors:
    BOLD = '\033[1m'
    LIGHTGREY = '\033[37m'
    RED = '\033[31m'
    GREEN = '\033[32m'
    BLUE = '\033[34m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'

class Crawler:
    '''A crawler for downloading university e-learning content.'''

    def __init__(self, req_handler, dbx):
        self.dbx = dbx
        self.req_handler = req_handler
        self.count = 0
        self.removed_dat_flag = False
        self.new_downloads = []

    def __str__(self):
        if not self.count:
            return '{}Files were already up to date.{}'.format(Colors.BOLD, Colors.ENDC)
        else:
            return '{}{}{} new file{} downloaded from ILIAS.{}'.format(Colors.BOLD, Colors.GREEN, str(self.count), ('s' if self.count != 1 else ''), Colors.ENDC)

    def start(self):
        '''Loop through top level courses and crawl the content for every course.'''
        response = self.req_handler.post_request()
        html_text = response.text

        if 'Anmeldedaten wurden nicht akzeptiert' in html_text: # has to be done this way, because http response on failed auth is 200 - OK.
            sys.stderr.write('Authorization @CAS failed.\nPlease maintain user and password correctly.\n')
            sys.exit(1)

        soup_courses = BeautifulSoup(html_text, 'html.parser')
        for soup_course in soup_courses.findAll('a', {'class': 'il_ContainerItemTitle'}):
            course_name = self.check_if_course_names_contain(soup_course.string)
            relative_link = soup_course.get('href')
            course_url = 'https://ilias.uni-mannheim.de/' + relative_link

            if course_name != None:
                self.crawl(course_url, course_name + '/')
            else:
                print('{}No download requested for course >> {}{}'.format(Colors.BOLD, Colors.ENDC, soup_course.string.lstrip()))

    def crawl(self, course_url, path):
        '''Recursively call this method until there is something
        to download for this course in the respective path.'''
        html_text_course = self.req_handler.session.get(course_url).text
        soup_course = BeautifulSoup(html_text_course, 'html.parser')
        containers = soup_course.find_all('div', {'class': 'il_ContainerListItem'})

        if containers:
            if not self.removed_dat_flag:
                print('folder_path: ' + path)

            for container in containers:
                file_ending = ''
                soup_line = container.find('a', {'class': 'il_ContainerItemTitle'})
                if soup_line:
                    link = soup_line.get('href')
                else: continue
                item_properties = container.find('div', {'class': 'ilListItemSection il_ItemProperties'})
                if item_properties != None:
                    item_prop = item_properties.find_all('span', {'class', 'il_ItemProperty'})
                    properties = [prop.string.strip().split() for prop in item_prop if prop.string != None]
                    if properties:
                        file_ending = properties[0][0]

                if 'download' in link:
                    folder_path = self.req_handler.path + path
                    self.create_folder(folder_path[:-1])
                    self.prepare_for_upload(folder_path, soup_line.string, file_ending, link)

                else:
                    self.crawl('https://ilias.uni-mannheim.de/' + link,
                               path + self.remove_edge_characters(soup_line.string))
        else:
            print('{}no_files_in: {}{}'.format(Colors.LIGHTGREY, str(path), Colors.ENDC))

    def prepare_for_upload(self, path, filename, file_ending, url):
        '''Prepare the file to be uploaded in dropbox. Remove edge characters,
           trim and add the correct file ending.'''
        # remove edge characters and trim
        filename = re.sub(r'[&]', 'and', filename)
        filename = re.sub(r'[!@#$/\:;*?<>|]', '', filename).strip()

        http_header = self.req_handler.session.head(url, headers={'Accept-Encoding': 'identity'})
        file_size = http_header.headers['content-length']
        path += filename + '.'

        if file_ending:
            path += file_ending
        else:
            path += str(mimetypes.guess_extension(http_header.headers['content-type']))

        display_path = path[len(self.req_handler.path):len(path)]

        if float(file_size) >= 3E7: #2E8: 200.000.000 byte; 5E7: 30MB
            print('{}file_skiped:{} {}'.format(Colors.BLUE, Colors.ENDC, display_path))
        elif self.exists(path):
            print('file_exists: ' + display_path)
        else:
            self.save_file(path, url, file_size, '{}downloading{}'.format(Colors.BOLD, Colors.ENDC))

    def create_folder(self, folder_path):
        '''Creating a folder in dropbox at the given path.'''
        if not self.exists(folder_path):
            self.dbx.files_create_folder(folder_path)

    def exists(self, path):
        '''Check whether a file or a folder already exists in dropbox at the given path.'''
        try:
            self.dbx.files_get_metadata(path)
            return True
        except dropbox.exceptions.ApiError:
            return False

    def save_file(self, db_path, url, file_size, action):
        '''Upload the file to dropbox.'''
        path_name = db_path[len(self.req_handler.path):len(db_path)]
        print('{}: {} from {}'.format(action, path_name, url))

        try:
            content = self.req_handler.session.get(url).content
            file = io.BytesIO(content)

            if int(file_size) > CHUNK_SIZE:
                result = self.dbx.files_upload_session_start(file.read(CHUNK_SIZE))
                cursor = dropbox.files.UploadSessionCursor(session_id=result.session_id, offset=file.tell())
                commit = dropbox.files.CommitInfo(path=db_path)

                while file.tell() < int(file_size):
                    if (int(file_size) - file.tell()) <= CHUNK_SIZE:
                        self.dbx.files_upload_session_finish(file.read(CHUNK_SIZE), cursor, commit)
                        self.new_downloads.append(path_name)
                        self.count += 1
                    else:
                        self.dbx.files_upload_session_append(file.read(CHUNK_SIZE), cursor.session_id, cursor.offset)
                        cursor.offset = file.tell()

            else: # file is uploaded as a whole
                self.dbx.files_upload(content, db_path, mute=False)
                self.new_downloads.append(path_name)
                self.count += 1

        except dropbox.exceptions.ApiError as err:
            sys.stderr.write('Failed to upload to %s\n%s\n' % (db_path, err))

    def check_if_course_names_contain(self, original):
        '''Check in the config data whether the user wants to download content for this course.'''
        for name in self.req_handler.course_names:
            compiler = re.compile(name)

            if compiler.search(original) != None:
                return name

        return None

    def remove_edge_characters(self, line):
        r'''Replaces all !@#$/\:;*?<>| with _
            Dateien/ will be removed from the string (which would lead to duplicate print of folder_path without removed_dat_flag)'''
        parse_edge_characters = re.sub(r'[!@#$/\:;*?<>|]', '_', line) + '/'
        if parse_edge_characters == 'Dateien/':
            self.removed_dat_flag = True
            return ''
        else:
            self.removed_dat_flag = False
            return parse_edge_characters

def run():
    '''Run the module.'''
    session = requests.Session()
    req_handler = request_handler.RequestHandler(session)
    try:
        drop = dropbox.Dropbox(req_handler.token)
    except AssertionError as err:
        sys.stderr.write(err + '\n')

    slide_crawler = Crawler(req_handler, drop)
    try:
        slide_crawler.start()
        print(slide_crawler)
    except requests.exceptions.ConnectionError as e:
        sys.stderr.write('{}\n\n{}\n'.format(e, 'A ConnectionError occurred. Please check your internet connection.'))
        sys.exit(1)

if __name__ == '__main__':
    try: run()

    except KeyboardInterrupt:
        sys.stderr.write(' {}{}Crawler Terminated.{}\n'.format(Colors.BOLD, Colors.RED, Colors.ENDC))
        sys.exit(1)
