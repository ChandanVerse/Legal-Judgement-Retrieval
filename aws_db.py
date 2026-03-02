"""AWS DynamoDB + S3 storage for case text and PDFs"""
import boto3
from botocore.exceptions import ClientError
from pathlib import Path
import config


class AWSStorage:
    """AWS storage client compatible with MongoDB interface"""

    def __init__(self):
        self.dynamodb = boto3.resource(
            'dynamodb',
            region_name=config.AWS_REGION,
            aws_access_key_id=config.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=config.AWS_SECRET_ACCESS_KEY,
        )
        self.s3 = boto3.client(
            's3',
            region_name=config.AWS_REGION,
            aws_access_key_id=config.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=config.AWS_SECRET_ACCESS_KEY,
        )
        self.table = self.dynamodb.Table(config.DYNAMODB_TABLE)
        self.bucket = config.S3_BUCKET

    def upsert_case(self, case_id: str, filename: str, full_text: str, page_count: int):
        """Insert or update a case document in DynamoDB"""
        self.table.put_item(Item={
            'case_id': case_id,
            'filename': filename,
            'full_text': full_text,
            'page_count': page_count,
        })

    def get_case(self, case_id: str) -> dict | None:
        """Get full case document by ID from DynamoDB"""
        try:
            response = self.table.get_item(Key={'case_id': case_id})
            return response.get('Item')
        except ClientError:
            return None

    def store_pdf(self, case_id: str, pdf_path: Path) -> str:
        """Store PDF in S3 bucket"""
        key = f"pdfs/{case_id}.pdf"
        self.s3.upload_file(str(pdf_path), self.bucket, key)
        return key

    def get_pdf(self, case_id: str) -> tuple[bytes, str] | None:
        """Get PDF bytes and filename from S3"""
        key = f"pdfs/{case_id}.pdf"
        try:
            response = self.s3.get_object(Bucket=self.bucket, Key=key)
            return response['Body'].read(), f"{case_id}.pdf"
        except ClientError:
            return None

    def list_cases(self) -> list[dict]:
        """List all cases with basic info"""
        response = self.table.scan(
            ProjectionExpression='case_id, filename, page_count'
        )
        return response.get('Items', [])

    def count(self) -> int:
        """Count total cases in DynamoDB"""
        response = self.table.scan(Select='COUNT')
        return response['Count']

    def delete_all(self):
        """Clear all cases from DynamoDB (use with caution)"""
        response = self.table.scan()
        for item in response.get('Items', []):
            self.table.delete_item(Key={'case_id': item['case_id']})
        # Handle pagination for large tables
        while 'LastEvaluatedKey' in response:
            response = self.table.scan(
                ExclusiveStartKey=response['LastEvaluatedKey']
            )
            for item in response.get('Items', []):
                self.table.delete_item(Key={'case_id': item['case_id']})
