""""""

import util

from abc import ABC, abstractmethod


class BaseSaver(ABC):
    """"""
    OVERW_FOLDER = '.overwritten/'

    def __init__(self, base_path):
        self.base_path = util.bpath(base_path)

    @abstractmethod
    def exists(self, relative_path):
        """Check whether a file or a folder already exists at the given relative path."""
        pass

    @abstractmethod
    def create_folder(self, relative_path):
        """Create a folder at the given path."""
        pass

    @abstractmethod
    def save_file(self, relative_path, content, overwrite=False):
        """Save the file."""
        pass
