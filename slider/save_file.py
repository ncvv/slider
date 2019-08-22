"""Module for local file system saving."""

import os
import shutil

from save_base import BaseSaver
import util


class FileSaver(BaseSaver):
    """A class for operations on files, handling the interaction with the local filesystem."""
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

    def save_file(self, relative_path, content, overwrite=False):
        """Save the file locally."""
        path = self.base_path + util.rpath(relative_path)

        # move file instead of overwriting it
        if self.exists(relative_path) and not overwrite:
            to = self.base_path + util.rpath(BaseSaver.OVERW_FOLDER + relative_path)
            shutil.move(path, to)

        # save file
        with open(path, 'wb') as file:
            try:
                file.write(content)
                return True
            except IOError:
                return False
