import io
import sys

import dropbox
from dropbox.exceptions import ApiError, AuthError

import util
from save_base import BaseSaver

# Chunk size for uploading large files to Dropbox
CHUNK_SIZE = 32 * 1024 * 1024


class DropboxSaver(BaseSaver):
    def __init__(self, base_path, token):
        super().__init__(base_path)
        self.token = token
        self.dbx = dropbox.Dropbox(token, timeout=180)

        try:
            self.dbx.users_get_current_account()
        except AuthError:
            sys.exit('Invalid Dropbox access token.')

    def exists(self, relative_path):
        """Check whether a file or a folder already exists at the given path relative in Dropbox."""
        path = util.dbpath(self.base_path + util.rpath(relative_path))

        try:
            self.dbx.files_get_metadata(path)
        except ApiError:
            return False
        return True

    def create_folder(self, relative_path):
        """Creating a folder at the given path in Dropbox."""
        if not self.exists(relative_path):
            path = util.dbpath(self.base_path + util.rpath(relative_path))
            self.dbx.files_create_folder_v2(path=path, autorename=False)

    def save_file(self, relative_path, content):
        """Save the file in Dropbox by uploading it with the Dropbox API."""
        try:
            path = util.dbpath(self.base_path + util.rpath(relative_path))
            file_size = len(content)

            # If file exceeds CHUNK_SIZE, upload in smaller chunks
            if int(file_size) > CHUNK_SIZE:
                file = io.BytesIO(content)
                result = self.dbx.files_upload_session_start(file.read(CHUNK_SIZE))
                cursor = dropbox.files.UploadSessionCursor(session_id=result.session_id, offset=file.tell())
                commit = dropbox.files.CommitInfo(path=path)

                while file.tell() < int(file_size):
                    if (int(file_size) - file.tell()) <= CHUNK_SIZE:
                        self.dbx.files_upload_session_finish(file.read(CHUNK_SIZE), cursor, commit)
                        return True
                    else:
                        self.dbx.files_upload_session_append(file.read(CHUNK_SIZE), cursor.session_id,
                                                             cursor.offset)
                        cursor.offset = file.tell()
            
            # File is uploaded as a whole
            else:
                self.dbx.files_upload(content, path, mute=False)
                return True
        #
        except ApiError as err:
            sys.stderr.write('Failed to upload to {}\n{}\n'.format(path, err))
            return False

    def download_file_to(self, relative_download_path, destination_path):
        down = util.dbpath(self.base_path + util.rpath(relative_download_path))
        with open(destination_path, 'wb') as f:
            metadata, res = self.dbx.files_download(down)
            f.write(res.content)
