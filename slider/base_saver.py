from abc import ABC, abstractmethod


class BaseSaver(ABC):

    def __init__(self, base_path):
        if not base_path.startswith('/'):
            base_path = '/' + base_path
        if not base_path.endswith('/'):
            base_path = base_path + '/'
        self.base_path = base_path

    @abstractmethod
    def exists(self, relative_path):
        """Check whether a file or a folder already exists at the given relative path."""
        pass

    @abstractmethod
    def create_folder(self, relative_path):
        """Creating a folder at the given path."""
        pass

    @abstractmethod
    def save_file(self, relative_path, content, *args):
        """Save the file."""
        pass
