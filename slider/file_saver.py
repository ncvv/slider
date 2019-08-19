import os

import util
from base_saver import BaseSaver


class FileSaver(BaseSaver):
    def __init__(self, base_path):
        super().__init__(base_path)

    def exists(self, relative_path):
        """Check whether a file or a folder already exists at the given relative path."""
        path = self.base_path + util.rpath(relative_path)
        return os.path.exists(path)

    def create_folder(self, relative_path):
        """Creating a folder at the given relative path."""
        if not self.exists(relative_path):
            path = self.base_path + util.rpath(relative_path)
            os.makedirs(path)

    def save_file(self, relative_path, content, *args):
        """Save the file locally."""
        path = self.base_path + util.rpath(relative_path)
        with open(path, 'wb') as file:
            try:
                file.write(content)
                return True
            except IOError:
                return False
