"""
Saving uploaded files into UPLOAD_FOLDER.

Files are checked by their content (magic bytes), not only by the extension,
and saved under a random name so they can't overwrite each other.
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


def save_upload(file_storage, allowed=IMAGES):
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
    folder = current_app.config['UPLOAD_FOLDER']
    os.makedirs(folder, exist_ok=True)
    file_storage.save(os.path.join(folder, filename))
    return filename
