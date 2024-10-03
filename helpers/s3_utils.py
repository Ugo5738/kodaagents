import logging
import mimetypes
import os

import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from django.conf import settings

# Configure logging
logger = logging.getLogger(__name__)


def upload_logo_to_s3(
    local_file_path: str,
    bucket_name: str = None,
    s3_folder: str = "static/logos/",
    s3_file_name: str = None,
    # Remove ACL parameter
) -> str:
    """
    Uploads a local file to an AWS S3 bucket and returns its public URL.

    Parameters:
    - local_file_path (str): Path to the local file to upload.
    - bucket_name (str, optional): Name of the target S3 bucket. If None, uses settings.AWS_STORAGE_BUCKET_NAME.
    - s3_folder (str, optional): S3 folder path where the file will be uploaded. Defaults to 'static/logos/'.
    - s3_file_name (str, optional): Desired S3 file name. If None, uses the local file name.

    Returns:
    - str: Public URL of the uploaded file.

    Raises:
    - Exception with appropriate message if upload fails.
    """
    # Use bucket name from settings if not provided
    if not bucket_name:
        bucket_name = getattr(settings, "AWS_STORAGE_BUCKET_NAME", None)
        if not bucket_name:
            error_msg = "S3 bucket name must be provided either as a parameter or in settings.AWS_STORAGE_BUCKET_NAME."
            logger.error(error_msg)
            raise ValueError(error_msg)

    # Initialize S3 client using credentials from environment or IAM roles
    s3_client = boto3.client("s3")

    # Determine the S3 file name
    if not s3_file_name:
        s3_file_name = os.path.basename(local_file_path)

    # Ensure s3_folder ends with '/'
    if not s3_folder.endswith("/"):
        s3_folder += "/"

    # Full S3 key (path)
    s3_key = f"{s3_folder}{s3_file_name}"

    try:
        # Determine content type
        content_type, _ = mimetypes.guess_type(local_file_path)
        if not content_type:
            content_type = "application/octet-stream"  # Default fallback

        # Upload the file without ACL
        s3_client.upload_file(
            Filename=local_file_path,
            Bucket=bucket_name,
            Key=s3_key,
            ExtraArgs={"ContentType": content_type},
        )
        logger.info(f"Successfully uploaded {local_file_path} to s3://{bucket_name}/{s3_key}")

        # Get the bucket's region
        region = s3_client.get_bucket_location(Bucket=bucket_name)["LocationConstraint"]
        if region is None:
            region = "us-east-1"

        # Construct the public URL based on bucket policies
        if region == "us-east-1":
            url = f"https://{bucket_name}.s3.amazonaws.com/{s3_key}"
        else:
            url = f"https://{bucket_name}.s3-{region}.amazonaws.com/{s3_key}"

        logger.info(f"Logo URL: {url}")
        return url

    except FileNotFoundError:
        error_msg = f"The file {local_file_path} was not found."
        logger.error(error_msg)
        raise Exception(error_msg)
    except NoCredentialsError:
        error_msg = "AWS credentials not available."
        logger.error(error_msg)
        raise Exception(error_msg)
    except ClientError as e:
        error_msg = f"Failed to upload {local_file_path} to S3: {e}"
        logger.error(error_msg)
        raise Exception(error_msg)
