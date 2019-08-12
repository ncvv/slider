# import io

import os
import logging

from base_saver import BaseSaver
logger = logging.getLogger(__name__)


class FileSaver(BaseSaver):

    def __init__(self, base_path):
        super().__init__(base_path)

    def exists(self, relative_path):
        """Check whether a file or a folder already exists at the given relative path."""
        full_path = self.base_path + relative_path
        return os.path.exists(full_path)

    def create_folder(self, relative_path):
        """Creating a folder at the given relative path."""
        if not self.exists(relative_path):
            full_path = self.base_path + relative_path
            os.makedirs(full_path)

    def save_file(self, relative_path, content, *args):
        """Save the file locally."""
        full_path = self.base_path + relative_path
        with open(full_path, 'wb') as file:
            file.write(content)
