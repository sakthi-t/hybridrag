"""
Storage service for Backblaze B2 operations (S3-compatible API).
Handles file uploads, downloads, and deletion using presigned URLs.
"""
import boto3
from botocore.config import Config as BotoConfig
from botocore.exceptions import ClientError
from flask import current_app
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)


class StorageService:
    """Service for Backblaze B2 storage operations using S3-compatible API."""
    
    def __init__(self):
        self._s3_client = None
    
    def _get_client(self):
        """Get or create boto3 S3 client configured for Backblaze B2."""
        if self._s3_client is None:
            config = current_app.config
            
            self._s3_client = boto3.client(
                's3',
                endpoint_url=config.get('B2_ENDPOINT'),
                aws_access_key_id=config.get('B2_KEY_ID'),
                aws_secret_access_key=config.get('B2_APPLICATION_KEY'),
                region_name=config.get('B2_REGION'),
                config=BotoConfig(
                    signature_version='s3v4',
                    # Backblaze B2 requires path-style addressing
                    s3={'addressing_style': 'path'}
                )
            )
        
        return self._s3_client
    
    def generate_object_key(self, user_id, doc_id, filename):
        """
        Generate standard object key for file storage.
        
        Args:
            user_id: User ID
            doc_id: Document ID
            filename: Original filename
        
        Returns:
            Object key string in format: users/<user_id>/documents/<doc_id>/<filename>
        """
        return f"users/{user_id}/documents/{doc_id}/{filename}"
    
    def generate_image_object_key(self, user_id, doc_id, page_num, image_index):
        """
        Generate object key for extracted images.
        
Args:
            user_id: User ID
            doc_id: Document ID
            page_num: Page number
            image_index: Image index on the page
        
        Returns:
            Object key string
        """
        return f"users/{user_id}/documents/{doc_id}/images/page_{page_num}_img_{image_index}.png"
    
    def generate_presigned_upload_url(self, object_key, content_type='application/pdf', expires_in=3600):
        """
        Generate presigned URL for direct upload to B2.
        
        Args:
            object_key: S3 object key (path)
            content_type: MIME type of the file
            expires_in: URL expiration time in seconds (default 1 hour)
        
        Returns:
            Presigned URL string
        """
        try:
            client = self._get_client()
            bucket_name = current_app.config.get('B2_BUCKET_NAME')
            
            url = client.generate_presigned_url(
                'put_object',
                Params={
                    'Bucket': bucket_name,
                    'Key': object_key,
                    'ContentType': content_type
                },
                ExpiresIn=expires_in
            )
            
            logger.info(f"Generated presigned upload URL for: {object_key}")
            return url
            
        except ClientError as e:
            logger.error(f"Error generating presigned upload URL: {str(e)}")
            raise
    
    def generate_presigned_download_url(self, object_key, expires_in=3600):
        """
        Generate presigned URL for downloading from B2.
        
        Args:
            object_key: S3 object key (path)
            expires_in: URL expiration time in seconds (default 1 hour)
        
        Returns:
            Presigned URL string
        """
        try:
            client = self._get_client()
            bucket_name = current_app.config.get('B2_BUCKET_NAME')
            
            url = client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': bucket_name,
                    'Key': object_key
                },
                ExpiresIn=expires_in
            )
            
            logger.info(f"Generated presigned download URL for: {object_key}")
            return url
            
        except ClientError as e:
            logger.error(f"Error generating presigned download URL: {str(e)}")
            raise
    
    def upload_file(self, file_obj, object_key, content_type='application/pdf'):
        """
        Upload a file directly to B2 (alternative to presigned URL).
        
        Args:
            file_obj: File-like object or bytes
            object_key: S3 object key (path)
            content_type: MIME type of the file
        
        Returns:
            True if successful
        """
        try:
            client = self._get_client()
            bucket_name = current_app.config.get('B2_BUCKET_NAME')
            
            client.put_object(
                Bucket=bucket_name,
                Key=object_key,
                Body=file_obj,
                ContentType=content_type
            )
            
            logger.info(f"Uploaded file to: {object_key}")
            return True
            
        except ClientError as e:
            logger.error(f"Error uploading file: {str(e)}")
            raise
    
    def download_file(self, object_key):
        """
        Download a file from B2.
        
        Args:
            object_key: S3 object key (path)
        
        Returns:
            File bytes
        """
        try:
            client = self._get_client()
            bucket_name = current_app.config.get('B2_BUCKET_NAME')
            
            response = client.get_object(
                Bucket=bucket_name,
                Key=object_key
            )
            
            logger.info(f"Downloaded file from: {object_key}")
            return response['Body'].read()
            
        except ClientError as e:
            logger.error(f"Error downloading file: {str(e)}")
            raise
    
    def delete_object(self, object_key):
        """
        Delete an object from B2.
        
        Args:
            object_key: S3 object key (path)
        
        Returns:
            True if successful
        """
        try:
            client = self._get_client()
            bucket_name = current_app.config.get('B2_BUCKET_NAME')
            
            client.delete_object(
                Bucket=bucket_name,
                Key=object_key
            )
            
            logger.info(f"Deleted object: {object_key}")
            return True
            
        except ClientError as e:
            logger.error(f"Error deleting object: {str(e)}")
            raise
    
    def delete_objects_by_prefix(self, prefix):
        """
        Delete all objects with a given prefix (e.g., all files for a document).
        
        Args:
            prefix: Object key prefix to match
        
        Returns:
            Number of objects deleted
        """
        try:
            client = self._get_client()
            bucket_name = current_app.config.get('B2_BUCKET_NAME')
            
            total_deleted = 0
            continuation_token = None
            
            # Paginate through all objects with prefix
            while True:
                # Build list request with optional continuation token
                list_params = {
                    'Bucket': bucket_name,
                    'Prefix': prefix
                }
                if continuation_token:
                    list_params['ContinuationToken'] = continuation_token
                
                response = client.list_objects_v2(**list_params)
                
                if 'Contents' not in response:
                    if total_deleted == 0:
                        logger.info(f"No objects found with prefix: {prefix}")
                    break
                
                # Delete objects in this batch
                objects_to_delete = [{'Key': obj['Key']} for obj in response['Contents']]
                
                if objects_to_delete:
                    client.delete_objects(
                        Bucket=bucket_name,
                        Delete={'Objects': objects_to_delete}
                    )
                    total_deleted += len(objects_to_delete)
                
                # Check if there are more objects to list
                if not response.get('IsTruncated'):
                    break
                    
                continuation_token = response.get('NextContinuationToken')
            
            if total_deleted > 0:
                logger.info(f"Deleted {total_deleted} objects with prefix: {prefix}")
            
            return total_deleted
            
        except ClientError as e:
            logger.error(f"Error deleting objects by prefix: {str(e)}")
            raise
    
    def object_exists(self, object_key):
        """
        Check if an object exists in B2.
        
        Args:
            object_key: S3 object key (path)
        
        Returns:
            True if exists, False otherwise
        """
        try:
            client = self._get_client()
            bucket_name = current_app.config.get('B2_BUCKET_NAME')
            
            client.head_object(
                Bucket=bucket_name,
                Key=object_key
            )
            
            return True
            
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                return False
            logger.error(f"Error checking object existence: {str(e)}")
            raise


# Global storage service instance
storage_service = StorageService()
