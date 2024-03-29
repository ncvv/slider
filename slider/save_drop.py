"""Module for Dropbox file saving."""

import io
import sys

from dropbox.exceptions import ApiError, AuthError
import dropbox

from save_base import BaseSaver
import util

# chunk size for uploading large files to Dropbox
CHUNK = 32 * 1024 * 1024


class DropboxSaver(BaseSaver):
    """A class for operations on files, handling the interaction with Dropbox."""
    def __init__(self, base_path, token):
        super().__init__(base_path)
        assert token != ''
        self.token = token
        self.dbx = dropbox.Dropbox(token, timeout=180)

        try:
            self.dbx.users_get_current_account()
        except AuthError:
            print('Invalid Dropbox access token.')
            sys.exit(1)

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

    def save_file(self, relative_path, content, mute=False, overwrite=False):
        """Save the file in Dropbox by uploading it with the Dropbox API."""
        path = util.dbpath(self.base_path + util.rpath(relative_path))

        file_size = len(content)
        large_file = file_size > CHUNK

        # handle potential overwriting
        if not overwrite:  # default
            upload_mode = dropbox.files.WriteMode.add
        else:  # allow overwriting
            upload_mode = dropbox.files.WriteMode.overwrite

        # if file exists and it should not be overwritten or it is a large file
        # move it to the overwritten folder to avoid overwriting the existing file
        if self.exists(relative_path) and (not overwrite or large_file):
            try:
                self.move_file(relative_path, BaseSaver.OVERW_FOLDER + relative_path)
            except ApiError as err:
                print('Moving {} failed due to:\n{}\n'.format(path, err))
                return False

        try:
            # file is uploaded as a whole
            if not large_file:
                self.dbx.files_upload(content, path, mute=mute, mode=upload_mode)
                return True

            # file exceeds size CHUNK, upload in smaller chunks
            else:
                f = io.BytesIO(content)
                result = self.dbx.files_upload_session_start(f.read(CHUNK))
                cursor = dropbox.files.UploadSessionCursor(session_id=result.session_id, offset=f.tell())
                commit = dropbox.files.CommitInfo(path=path)

                while f.tell() < int(file_size):
                    if (int(file_size) - f.tell()) <= CHUNK:
                        self.dbx.files_upload_session_finish(f.read(CHUNK), cursor, commit)
                        return True
                    else:
                        self.dbx.files_upload_session_append(f.read(CHUNK), cursor.session_id, cursor.offset)
                        cursor.offset = f.tell()

        except ApiError as err:
            print('Uploading {} failed due to:\n{}\n'.format(path, err))
            return False

    def move_file(self, relative_from_path, relative_to_path):
        """Move a file from relative_from_path to relative_to_path."""
        fr = util.dbpath(self.base_path + util.rpath(relative_from_path))
        to = util.dbpath(self.base_path + util.rpath(relative_to_path))
        self.dbx.files_move(fr, to, autorename=True)

    def download_file(self, relative_download_path, destination_path):
        """Download a file located at relative_download_path and
           save it at destination_path."""
        down = util.dbpath(self.base_path + util.rpath(relative_download_path))
        dest = destination_path

        # download file
        with open(dest, 'wb') as f:
            metadata, res = self.dbx.files_download(down)
            f.write(res.content)
