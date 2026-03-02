"""Migrate data from MongoDB to AWS DynamoDB + S3

Run this script locally before deploying to EC2.
Requires: MongoDB connection (existing) + AWS credentials (new)
"""
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from mongo_db import MongoDB
from aws_db import AWSStorage
import config


def migrate():
    print("=" * 50)
    print("MongoDB -> AWS Migration Script")
    print("=" * 50)

    # Initialize clients
    print("\nConnecting to MongoDB...")
    mongo = MongoDB()
    mongo_count = mongo.count()
    print(f"  Found {mongo_count} cases in MongoDB")

    print("\nConnecting to AWS...")
    aws = AWSStorage()
    print(f"  DynamoDB table: {config.DYNAMODB_TABLE}")
    print(f"  S3 bucket: {config.S3_BUCKET}")

    # Migrate cases to DynamoDB
    print("\n[1/2] Migrating cases to DynamoDB...")
    cases = list(mongo.cases.find())
    migrated = 0
    for case in cases:
        try:
            aws.upsert_case(
                case_id=case['case_id'],
                filename=case.get('filename', ''),
                full_text=case.get('full_text', ''),
                page_count=case.get('page_count', 0)
            )
            migrated += 1
            print(f"  ✓ {case['case_id']}")
        except Exception as e:
            print(f"  ✗ {case['case_id']}: {e}")

    print(f"\n  Migrated {migrated}/{len(cases)} cases to DynamoDB")

    # Migrate PDFs from local directory to S3
    pdf_dir = Path(__file__).parent.parent.parent / "data" / "dataset_pdfs"
    if pdf_dir.exists():
        print(f"\n[2/2] Uploading PDFs to S3 from {pdf_dir}...")
        pdfs = list(pdf_dir.glob("*.pdf"))
        uploaded = 0
        for pdf in pdfs:
            case_id = pdf.stem.replace(" ", "_")[:50]
            try:
                aws.store_pdf(case_id, pdf)
                uploaded += 1
                print(f"  ✓ {pdf.name}")
            except Exception as e:
                print(f"  ✗ {pdf.name}: {e}")
        print(f"\n  Uploaded {uploaded}/{len(pdfs)} PDFs to S3")
    else:
        print(f"\n[2/2] PDF directory not found: {pdf_dir}")
        print("  Skipping PDF upload (you can upload manually later)")

    # Verify
    print("\n" + "=" * 50)
    print("Verification")
    print("=" * 50)
    aws_count = aws.count()
    print(f"  Cases in DynamoDB: {aws_count}")
    print(f"  Cases in MongoDB:  {mongo_count}")

    if aws_count == mongo_count:
        print("\n✓ Migration complete! All cases transferred.")
    else:
        print(f"\n⚠ Warning: Count mismatch ({aws_count} vs {mongo_count})")

    print("\nNext steps:")
    print("  1. Update api_server.py to use aws_db instead of mongo_db")
    print("  2. Deploy to EC2 using deploy/scripts/deploy.sh")


if __name__ == "__main__":
    migrate()
