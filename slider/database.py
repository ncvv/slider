import os

import shutil

from tinydb import TinyDB, Query

import util

DATABASE_FOLDER = '.db/'
DATABASE_PATH = DATABASE_FOLDER + 'files.json'


class Database:
    def __init__(self, file_handler, dropbox):
        curr = util.bpath(os.getcwd())
        self.db_folder_path = curr + DATABASE_FOLDER
        self.db_path = curr + DATABASE_PATH
        self.setup(file_handler, dropbox)

        self.db = TinyDB(self.db_path)

    def insert(self, filepath, filehash, fileupdate):
        """"""
        self.db.insert({'path': filepath, 'hashvalue': filehash, 'lastupdate': fileupdate})

    def get_hash(self, filehash):
        """"""
        file = Query()
        return self.db.search(file.hashvalue == filehash)

    def get_name(self, filepath):
        """"""
        file = Query()
        return self.db.search(file.path == filepath)

    def get_name_update(self, filename, fileupdate):
        """"""
        file = Query()
        return self.db.search((file.path == filename) & (file.lastupdate == fileupdate))

    def setup(self, file_handler, dropbox):
        """"""
        if not os.path.exists(self.db_folder_path):
            os.makedirs(self.db_folder_path)
        # Database does not exist yet
        if not file_handler.exists(DATABASE_PATH):
            file_handler.create_folder(DATABASE_FOLDER)
        # Database exists
        else:
            # Database is saved in Dropbox
            # Download it to working dir
            if dropbox:
                file_handler.download_file(DATABASE_PATH, self.db_path)
            # Database file is saved locally
            # Copy it to working dir
            else:
                src = file_handler.base_path + DATABASE_PATH
                shutil.copyfile(src, self.db_path)

    def close(self, file_handler, dropbox, regular=False):
        """"""
        self.db.close()
        if regular:
            if dropbox:
                with open(self.db_path, 'rb') as f:
                    file_handler.save_file(DATABASE_PATH, f.read(), overwrite=True)
            else:
                dest = file_handler.base_path + DATABASE_PATH
                shutil.copyfile(self.db_path, dest)
        os.remove(self.db_path)
