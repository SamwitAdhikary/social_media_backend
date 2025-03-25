from storages.backends.s3boto3 import S3Boto3Storage
from django.conf import settings
from django.core.files.base import ContentFile

def upload_file_to_s3(file, folder, filename=None):
    """
    Uploads a file to AWS S3 and returns the saved file path and URL.

    :param file: A file-like object (e.g., InMemoryUploadedFile).
    :param folder: The folder (prefix) on S3 where the file sholud be stored.
    :param filename: Optional custom filename. If not provided, uses file.name.
    :return: (saved_file_path, file_url)
    """

    # Create an S3 storage instance
    storage = S3Boto3Storage(bucket_name=settings.AWS_STORAGE_BUCKET_NAME)

    # Use provided filename or default to the original file name
    filename = filename or file.name

    # Build the full file path
    file_path = f"{folder}/{filename}"

    # Read the file content and wrap it in a ContentFile
    content_file = ContentFile(file.read())

    # Save the file to S3
    saved_file_path = storage.save(file_path, content_file)

    # Retrieve the URL for the saved file
    file_url = storage.url(saved_file_path)

    return saved_file_path, file_url