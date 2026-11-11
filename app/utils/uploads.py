"""
Saving uploaded files.

Files are checked by their content (magic bytes), not only by the extension,
and saved under a random name so they can't overwrite each other.

Two folders:
* UPLOAD_FOLDER (app/static/images): public pictures of hospitals and doctors.
* PRIVATE_UPLOAD_FOLDER (instance/uploads): patients' files. Not reachable as a
  static URL; served only by bookings.facility_file after an ownership check.
"""
import os
import uuid

from flask import current_app

# extension -> signature check on the first bytes of the file
_SIGNATURES = {
    'png': lambda h: h.startswith(b'\x89PNG\r\n\x1a\n'),
    'jpg': lambda h: h.startswith(b'\xff\xd8\xff'),
    'jpeg': lambda h: h.startswith(b'\xff\xd8\xff'),
    'gif': lambda h: h[:6] in (b'GIF87a', b'GIF89a'),
    'webp': lambda h: h[:4] == b'RIFF' and h[8:12] == b'WEBP',
    'pdf': lambda h: h.startswith(b'%PDF-'),
}
IMAGES = ('png', 'jpg', 'jpeg', 'gif', 'webp')
IMAGES_AND_PDF = IMAGES + ('pdf',)


class UploadError(Exception):
    """The uploaded file is not allowed. The message is shown to the user."""


def save_upload(file_storage, allowed=IMAGES, private=False):
    """
    Save an uploaded file and return its stored filename,
    or None if nothing was uploaded. Raises UploadError for a bad file.
    """
    if file_storage is None or not file_storage.filename:
        return None
    ext = file_storage.filename.rsplit('.', 1)[-1].lower() if '.' in file_storage.filename else ''
    if ext not in allowed:
        raise UploadError('Only these file types are allowed: ' + ', '.join(allowed))
    head = file_storage.stream.read(16)
    file_storage.stream.seek(0)
    if not _SIGNATURES[ext](head):
        raise UploadError('The file content does not match its type. Please upload a real '
                          + ('image' if allowed == IMAGES else 'image or PDF') + '.')

    filename = f'{uuid.uuid4().hex}.{"jpg" if ext == "jpeg" else ext}'
    folder = current_app.config['PRIVATE_UPLOAD_FOLDER' if private else 'UPLOAD_FOLDER']
    os.makedirs(folder, exist_ok=True)
    file_storage.save(os.path.join(folder, filename))
    return filename


def private_file_folder(filename):
    """Folder holding a patient file: the private folder, or the public one for files uploaded before it existed
    (`flask secure-uploads` moves those). None if the file is missing."""
    for key in ('PRIVATE_UPLOAD_FOLDER', 'UPLOAD_FOLDER'):
        folder = current_app.config[key]
        if os.path.isfile(os.path.join(folder, os.path.basename(filename))):
            return folder
    return None
