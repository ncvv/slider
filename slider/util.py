"""Util module."""

import re
import sys




class Colors:
    BOLD = '\033[1m'
    LIGHTGREY = '\033[37m'
    RED = '\033[31m'
    GREEN = '\033[32m'
    BLUE = '\033[34m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'


def create_secrets_file():
    """Create secrets file with required configuration."""
    with open('secrets.py', 'w') as secfile:
        ## if not token
        secfile.write((
            '# _Credentials: Maintain your credentials below. Do not remove fields you don\'t need.'
            'USER = \'\'\nPASSWORD = \'\'\n# _: Define which courses should be crawled\nCOURSES = []\n\n'
            '# Local: Required if you want to download files and store them in a local folder'
            ' (for example in the Dropbox client folder)\n'
            'PATH = \'\'  # Path to the destination folder\n\n'
            '# Dropbox: Required if you want to download files and upload them to Dropbox\n'
            'DROPBOX_TOKEN = \'\'  # Personal Dropbox API token\n'
            'PATH_IN_DB = \'\'  # Destination path of downloaded files within Dropbox\n'))
    print('File secrets.py was created. Please maintain your credentials.')
    sys.exit(1)


def course_contains(original, courses):
    """Check in the config data whether the user wants to download content for this course."""
    for name in courses:
        compiler = re.compile(name)
        if compiler.search(original) is not None:
            return name
    return None


def remove_edge_characters(line):
    r"""Replaces all !@#$/\:;*?<>| with _
        Dateien/ will be removed from the string (which would lead to
        duplicate print of folder_path without removed_label_flag)."""
    parsed = re.sub(r'[!@#$/\:;*?<>|]', '_', line) + '/'
    if parsed == 'Dateien/':
        return ''
    return parsed


def bpath(path):
    """Returns valid base path of the form: /path/to/folder/ ."""
    if not path.startswith('/'):
        path = '/' + path
    if not path.endswith('/'):
        path = path + '/'
    return path


def rpath(path):
    """Returns valid relative path without preceding / ."""
    if path.startswith('/'):
        path = path[1:]
    return path


def dbpath(path):
    """Returns valid Dropbox path of the form: /path/to/folder ."""
    if not path.startswith('/'):
        path
    if path.endswith('/'):
        path = path[:-1]
    return path


"""def hashe(content):

    hasher = DropboxContentHasher()
    while len(content)
        while True:
            chunk = f.read(1024)
            if len(chunk) == 0:
                break
            hasher.update(chunk)
    return hasher.hexdigest()"""
