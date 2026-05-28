"""
Backblaze B2 Connectivity Diagnostic Script
Tests B2 configuration and connectivity step-by-step
"""
import boto3
from botocore.config import Config as BotoConfig
from botocore.exceptions import ClientError, NoCredentialsError
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

def print_header(title):
    """Print a formatted header"""
    print("\n" + "="*60)
    print(f"  {title}")
    print("="*60)

def test_credentials():
    """Test if B2 credentials are loaded"""
    print_header("Step 1: Checking B2 Credentials")
    
    b2_key_id = os.getenv('backblazekeyid')
    b2_app_key = os.getenv('backblazeapplicationkey')
    b2_bucket = os.getenv('backblazebucketname')
    b2_endpoint = os.getenv('backblazebucketendpoint')
    b2_region = os.getenv('backblazeregion')
    
    print(f"  B2 Key ID: {b2_key_id[:10]}... (length: {len(b2_key_id) if b2_key_id else 0})")
    print(f"  B2 App Key: {b2_app_key[:10] if b2_app_key else 'None'}... (length: {len(b2_app_key) if b2_app_key else 0})")
    print(f"  B2 Bucket: {b2_bucket}")
    print(f"  B2 Endpoint: {b2_endpoint}")
    print(f"  B2 Region: {b2_region}")
    
    if not all([b2_key_id, b2_app_key, b2_bucket, b2_endpoint]):
        print("\n  [FAIL] ERROR: Missing B2 credentials!")
        return None
    
    print("\n  [PASS] All credentials loaded from .env")
    return {
        'key_id': b2_key_id,
        'app_key': b2_app_key,
        'bucket': b2_bucket,
        'endpoint': b2_endpoint,
        'region': b2_region or 'us-east-005'
    }

def test_boto3_client(creds):
    """Test boto3 S3 client initialization"""
    print_header("Step 2: Initializing Boto3 S3 Client")
    
    try:
        print(f"  Creating client with endpoint: {creds['endpoint']}")
        print(f"  Region: {creds['region']}")
        
        client = boto3.client(
            's3',
            endpoint_url=creds['endpoint'],
            aws_access_key_id=creds['key_id'],
            aws_secret_access_key=creds['app_key'],
            region_name=creds['region'],
            config=BotoConfig(
                signature_version='s3v4',
                s3={'addressing_style': 'virtual'}
            )
        )
        
        print("\n  [PASS] Boto3 client created successfully")
        return client
        
    except Exception as e:
        print(f"\n  [FAIL] ERROR creating boto3 client: {type(e).__name__}")
        print(f"     {str(e)}")
        return None

def test_list_buckets(client):
    """Test listing buckets"""
    print_header("Step 3: Testing Bucket Access (List Buckets)")
    
    try:
        response = client.list_buckets()
        buckets = response.get('Buckets', [])
        
        print(f"  Found {len(buckets)} bucket(s):")
        for bucket in buckets:
            print(f"    - {bucket['Name']}")
        
        print("\n  [PASS] Successfully listed buckets")
        return True
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_msg = e.response['Error']['Message']
        print(f"\n  [FAIL] ERROR listing buckets: {error_code}")
        print(f"     {error_msg}")
        return False
    except Exception as e:
        print(f"\n  [FAIL] ERROR: {type(e).__name__}")
        print(f"     {str(e)}")
        return False

def test_bucket_exists(client, bucket_name):
    """Test if specific bucket exists and is accessible"""
    print_header(f"Step 4: Testing Access to Bucket '{bucket_name}'")
    
    try:
        client.head_bucket(Bucket=bucket_name)
        print(f"\n  [PASS] Bucket '{bucket_name}' exists and is accessible")
        return True
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == '404':
            print(f"\n  [FAIL] ERROR: Bucket '{bucket_name}' not found")
        elif error_code == '403':
            print(f"\n  [FAIL] ERROR: Access denied to bucket '{bucket_name}'")
        else:
            print(f"\n  [FAIL] ERROR: {error_code}")
            print(f"     {e.response['Error']['Message']}")
        return False
    except Exception as e:
        print(f"\n  [FAIL] ERROR: {type(e).__name__}")
        print(f"     {str(e)}")
        return False

def test_presigned_url(client, bucket_name):
    """Test presigned URL generation"""
    print_header("Step 5: Testing Presigned URL Generation")
    
    test_key = "test/diagnostic_file.txt"
    
    try:
        # Test upload URL
        print(f"  Generating presigned UPLOAD URL for: {test_key}")
        upload_url = client.generate_presigned_url(
            'put_object',
            Params={
                'Bucket': bucket_name,
                'Key': test_key,
                'ContentType': 'text/plain'
            },
            ExpiresIn=3600
        )
        
        print(f"  [PASS] Upload URL generated (length: {len(upload_url)})")
        print(f"     URL preview: {upload_url[:80]}...")
        
        # Test download URL
        print(f"\n  Generating presigned DOWNLOAD URL for: {test_key}")
        download_url = client.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': bucket_name,
                'Key': test_key
            },
            ExpiresIn=3600
        )
        
        print(f"  [PASS] Download URL generated (length: {len(download_url)})")
        print(f"     URL preview: {download_url[:80]}...")
        
        return True
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_msg = e.response['Error']['Message']
        print(f"\n  [FAIL] ERROR generating presigned URL: {error_code}")
        print(f"     {error_msg}")
        return False
    except Exception as e:
        print(f"\n  [FAIL] ERROR: {type(e).__name__}")
        print(f"     {str(e)}")
        return False

def test_actual_upload(client, bucket_name):
    """Test actual file upload"""
    print_header("Step 6: Testing Actual File Upload")
    
    test_key = "test/diagnostic_test.txt"
    test_content = b"This is a test file from B2 diagnostic script"
    
    try:
        print(f"  Uploading test file to: {test_key}")
        client.put_object(
            Bucket=bucket_name,
            Key=test_key,
            Body=test_content,
            ContentType='text/plain'
        )
        
        print(f"  [PASS] File uploaded successfully")
        
        # Try to download it back
        print(f"\n  Downloading test file...")
        response = client.get_object(Bucket=bucket_name, Key=test_key)
        downloaded_content = response['Body'].read()
        
        if downloaded_content == test_content:
            print(f"  [PASS] File downloaded and verified")
        else:
            print(f"  [WARN] File downloaded but content doesn't match")
        
        # Clean up
        print(f"\n  Cleaning up test file...")
        client.delete_object(Bucket=bucket_name, Key=test_key)
        print(f"  [PASS] Test file deleted")
        
        return True
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_msg = e.response['Error']['Message']
        print(f"\n  [FAIL] ERROR: {error_code}")
        print(f"     {error_msg}")
        return False
    except Exception as e:
        print(f"\n  [FAIL] ERROR: {type(e).__name__}")
        print(f"     {str(e)}")
        return False

def main():
    """Run all diagnostic tests"""
    print("\n" + "="*60)
    print("   Backblaze B2 Connectivity Diagnostic Tool")
    print("="*60)
    
    # Step 1: Check credentials
    creds = test_credentials()
    if not creds:
        print("\n[FAIL] Cannot proceed without valid credentials")
        return
    
    # Step 2: Initialize boto3 client
    client = test_boto3_client(creds)
    if not client:
        print("\n[FAIL] Cannot proceed without valid boto3 client")
        return
    
    # Step 3: List buckets
    list_success = test_list_buckets(client)
    
    # Step 4: Check specific bucket
    bucket_success = test_bucket_exists(client, creds['bucket'])
    if not bucket_success:
        print("\n[WARN] Skipping remaining tests due to bucket access failure")
        return
    
    # Step 5: Test presigned URLs
    presigned_success = test_presigned_url(client, creds['bucket'])
    
    # Step 6: Test actual upload/download
    upload_success = test_actual_upload(client, creds['bucket'])
    
    # Summary
    print_header("DIAGNOSTIC SUMMARY")
    print(f"  Credentials Loaded:      {'[PASS]' if creds else '[FAIL]'}")
    print(f"  Boto3 Client Init:       {'[PASS]' if client else '[FAIL]'}")
    print(f"  List Buckets:            {'[PASS]' if list_success else '[FAIL]'}")
    print(f"  Bucket Access:           {'[PASS]' if bucket_success else '[FAIL]'}")
    print(f"  Presigned URLs:          {'[PASS]' if presigned_success else '[FAIL]'}")
    print(f"  Upload/Download:         {'[PASS]' if upload_success else '[FAIL]'}")
    
    if all([creds, client, list_success, bucket_success, presigned_success, upload_success]):
        print("\n[PASS] ALL TESTS PASSED! B2 is configured correctly.")
    else:
        print("\n[WARN] Some tests failed. Check error messages above for details.")
    
    print("="*60 + "\n")

if __name__ == "__main__":
    main()
