"""Database module."""

import os
import shutil

from tinydb import TinyDB, Query

import util

DATABASE_FOLDER = '.db/'
DATABASE_PATH = DATABASE_FOLDER + 'files.json'


class Database:
    """A class to handle a TinyDB instance for keeping track of downloads."""
    def __init__(self, file_handler, dropbox):
        curr = util.bpath(os.getcwd())
        self.db_folder_path = curr + DATABASE_FOLDER
        self.db_path = curr + DATABASE_PATH
        self.setup(file_handler, dropbox)

        self.db = TinyDB(self.db_path)

    def insert(self, filepath, filehash, fileupdate):
        """Insert an element into the database."""
        self.db.insert({'path': filepath, 'hashvalue': filehash, 'lastupdate': fileupdate})

    def get_hash(self, filehash):
        """Retrieve all elements with the given hashvalue filehash."""
        file = Query()
        return self.db.search(file.hashvalue == filehash)

    def get_name(self, filepath):
        """Retrieve all elements with the given path filepath."""
        file = Query()
        return self.db.search(file.path == filepath)

    def get_name_update(self, filepath, fileupdate):
        """Retrieve all elements with the given path filepath and last update fileupdate."""
        file = Query()
        return self.db.search((file.path == filepath) & (file.lastupdate == fileupdate))

    def setup(self, file_handler, dropbox):
        """Setup the database.

        Create the folder where the database will be stored,
        create the database itself or, if the database already exists
        copy its file in the working directory. This is required
        because when the Dropbox API is used, the file must be available
        locally to read from and write to it.
        """
        if not os.path.exists(self.db_folder_path):
            os.makedirs(self.db_folder_path)
        # database does not exist yet
        if not file_handler.exists(DATABASE_PATH):
            file_handler.create_folder(DATABASE_FOLDER)
        # database exists
        else:
            # database is saved in Dropbox
            # download it to working dir
            if dropbox:
                file_handler.download_file(DATABASE_PATH, self.db_path)
            # database file is saved locally
            # copy it to working dir
            else:
                src = file_handler.base_path + DATABASE_PATH
                shutil.copyfile(src, self.db_path)

    def close(self, file_handler, dropbox):
        """Close the database.

        Close the database connection and put it to
        the chosen download folder, i.e. upload it
        to dropbox or move it to the respective local folder.
        """
        self.db.close()

        if dropbox:
            with open(self.db_path, 'rb') as f:
                file_handler.save_file(DATABASE_PATH, f.read(), mute=True, overwrite=True)
        else:
            dest = file_handler.base_path + DATABASE_PATH
            shutil.copyfile(self.db_path, dest)

        # remove db file from local working dir
        shutil.rmtree(self.db_folder_path)
