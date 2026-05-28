import logging
import boto3
from botocore.config import Config as BotoConfig
from botocore.exceptions import ClientError
from app.config import get_settings

logger = logging.getLogger(__name__)


class StorageService:
    def __init__(self):
        self._s3_client = None

    def _get_client(self):
        if self._s3_client is None:
            settings = get_settings()
            self._s3_client = boto3.client(
                "s3",
                endpoint_url=settings.b2_bucket_endpoint,
                aws_access_key_id=settings.b2_key_id,
                aws_secret_access_key=settings.b2_application_key,
                region_name=settings.b2_region,
                config=BotoConfig(
                    signature_version="s3v4",
                    s3={"addressing_style": "path"},
                ),
            )
        return self._s3_client

    def generate_object_key(self, user_id, doc_id, filename):
        return f"users/{user_id}/documents/{doc_id}/{filename}"

    def generate_image_object_key(self, user_id, doc_id, page_num, image_index):
        return f"users/{user_id}/documents/{doc_id}/images/page_{page_num}_img_{image_index}.png"

    def generate_presigned_upload_url(self, object_key, content_type="application/pdf", expires_in=3600):
        try:
            client = self._get_client()
            url = client.generate_presigned_url(
                "put_object",
                Params={
                    "Bucket": get_settings().b2_bucket_name,
                    "Key": object_key,
                    "ContentType": content_type,
                },
                ExpiresIn=expires_in,
            )
            logger.info(f"Generated presigned upload URL for: {object_key}")
            return url
        except ClientError as e:
            logger.error(f"Error generating presigned upload URL: {e}")
            raise

    def generate_presigned_download_url(self, object_key, expires_in=3600):
        try:
            client = self._get_client()
            url = client.generate_presigned_url(
                "get_object",
                Params={
                    "Bucket": get_settings().b2_bucket_name,
                    "Key": object_key,
                },
                ExpiresIn=expires_in,
            )
            logger.info(f"Generated presigned download URL for: {object_key}")
            return url
        except ClientError as e:
            logger.error(f"Error generating presigned download URL: {e}")
            raise

    def upload_file(self, file_obj, object_key, content_type="application/pdf"):
        try:
            client = self._get_client()
            client.put_object(
                Bucket=get_settings().b2_bucket_name,
                Key=object_key,
                Body=file_obj,
                ContentType=content_type,
            )
            logger.info(f"Uploaded file to: {object_key}")
            return True
        except ClientError as e:
            logger.error(f"Error uploading file: {e}")
            raise

    def download_file(self, object_key):
        try:
            client = self._get_client()
            response = client.get_object(
                Bucket=get_settings().b2_bucket_name,
                Key=object_key,
            )
            logger.info(f"Downloaded file from: {object_key}")
            return response["Body"].read()
        except ClientError as e:
            logger.error(f"Error downloading file: {e}")
            raise

    def delete_object(self, object_key):
        try:
            client = self._get_client()
            client.delete_object(
                Bucket=get_settings().b2_bucket_name,
                Key=object_key,
            )
            logger.info(f"Deleted object: {object_key}")
            return True
        except ClientError as e:
            logger.error(f"Error deleting object: {e}")
            raise

    def delete_objects_by_prefix(self, prefix):
        try:
            client = self._get_client()
            bucket_name = get_settings().b2_bucket_name
            total_deleted = 0
            continuation_token = None

            while True:
                list_params = {"Bucket": bucket_name, "Prefix": prefix}
                if continuation_token:
                    list_params["ContinuationToken"] = continuation_token

                response = client.list_objects_v2(**list_params)
                if "Contents" not in response:
                    break

                objects_to_delete = [{"Key": obj["Key"]} for obj in response["Contents"]]
                if objects_to_delete:
                    client.delete_objects(
                        Bucket=bucket_name,
                        Delete={"Objects": objects_to_delete},
                    )
                    total_deleted += len(objects_to_delete)

                if not response.get("IsTruncated"):
                    break
                continuation_token = response.get("NextContinuationToken")

            if total_deleted > 0:
                logger.info(f"Deleted {total_deleted} objects with prefix: {prefix}")
            return total_deleted
        except ClientError as e:
            logger.error(f"Error deleting objects by prefix: {e}")
            raise

    def object_exists(self, object_key):
        try:
            client = self._get_client()
            client.head_object(
                Bucket=get_settings().b2_bucket_name,
                Key=object_key,
            )
            return True
        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                return False
            raise


storage_service = StorageService()
