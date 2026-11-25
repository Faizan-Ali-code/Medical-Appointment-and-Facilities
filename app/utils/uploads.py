"""Pictures of hospitals and doctors, stored in UPLOAD_FOLDER under a random file name."""
import os
import uuid

from flask import current_app

IMAGE_EXTENSIONS = ('png', 'jpg', 'jpeg', 'gif', 'webp')


def save_image(file_storage):
    """Save an uploaded picture and return its stored file name."""
    extension = file_storage.filename.rsplit('.', 1)[-1].lower()
    filename = f'{uuid.uuid4().hex}.{extension}'
    folder = current_app.config['UPLOAD_FOLDER']
    os.makedirs(folder, exist_ok=True)
    file_storage.save(os.path.join(folder, filename))
    return filename


def delete_image(filename):
    """Remove a stored picture (a missing file is fine)."""
    if filename:
        path = os.path.join(current_app.config['UPLOAD_FOLDER'], os.path.basename(filename))
        if os.path.isfile(path):
            os.remove(path)
