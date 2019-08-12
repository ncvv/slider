import io
import logging
import sys

import dropbox

from base_saver import BaseSaver
logger = logging.getLogger(__name__)

# Chunk size for uploading large files to Dropbox
CHUNK_SIZE = 32 * 1024 * 1024


class DropboxSaver(BaseSaver):

    def __init__(self, path_in_db, token):
        if path_in_db[0] != '/':
            path_in_db = '/' + path_in_db
        super().__init__(path_in_db)  # Dropbox requires slash in front of path
        self.token = token
        try:
            self.dbx = dropbox.Dropbox(token, timeout=180)
        except AssertionError as err:
            sys.stderr.write(err + '\n')

    def exists(self, relative_path):
        """Check whether a file or a folder already exists at the given path relative in Dropbox."""
        try:
            self.dbx.files_get_metadata(self.path_in_db + relative_path)
            return True
        except dropbox.exceptions.ApiError:
            return False

    def create_folder(self, relative_path):
        """Creating a folder at the given path in Dropbox."""
        full_db_path = self.path_in_db + relative_path
        if not self.exists(full_db_path):
            self.dbx.files_create_folder(full_db_path)

    def save_file(self, relative_path, content, *args):
        """Save the file in Dropbox by uploading it with the Dropbox API."""
        try:
            full_db_path = self.path_in_db + relative_path
            file = io.BytesIO(content)
            file_size = args[0]

            if int(file_size) > CHUNK_SIZE:
                result = self.dbx.files_upload_session_start(file.read(CHUNK_SIZE))
                cursor = dropbox.files.UploadSessionCursor(session_id=result.session_id, offset=file.tell())
                commit = dropbox.files.CommitInfo(path=full_db_path)

                while file.tell() < int(file_size):
                    if (int(file_size) - file.tell()) <= CHUNK_SIZE:
                        self.dbx.files_upload_session_finish(file.read(CHUNK_SIZE), cursor, commit)
                        self.new_downloads.append(relative_path)
                        self.count += 1
                    else:
                        self.dbx.files_upload_session_append(file.read(CHUNK_SIZE), cursor.session_id, cursor.offset)
                        cursor.offset = file.tell()

            else:  # file is uploaded as a whole
                self.dbx.files_upload(content, full_db_path, mute=False)
                self.new_downloads.append(relative_path)
                self.count += 1

        except dropbox.exceptions.ApiError as err:
            sys.stderr.write('Failed to upload to {}\n{}\n'.format(full_db_path, err))
            pass
