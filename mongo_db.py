"""MongoDB Atlas client for storing full case text and PDFs"""
import certifi
from pymongo import MongoClient
from gridfs import GridFS
from pathlib import Path
import config


class MongoDB:
    def __init__(self):
        # Connect with certifi CA bundle for proper SSL on Windows
        self.client = MongoClient(
            config.MONGO_URI,
            tlsCAFile=certifi.where(),
            serverSelectionTimeoutMS=30000,
            connectTimeoutMS=30000,
        )
        self.db = self.client[config.MONGO_DB_NAME]
        self.cases = self.db["cases"]
        self.fs = GridFS(self.db)

    def upsert_case(self, case_id: str, filename: str, full_text: str, page_count: int):
        """Insert or update a case document"""
        self.cases.update_one(
            {"case_id": case_id},
            {"$set": {
                "case_id": case_id,
                "filename": filename,
                "full_text": full_text,
                "page_count": page_count,
            }},
            upsert=True
        )

    def get_case(self, case_id: str) -> dict | None:
        """Get full case document by ID"""
        return self.cases.find_one({"case_id": case_id})

    def delete_all(self):
        """Clear all cases"""
        self.cases.delete_many({})

    def count(self) -> int:
        """Count total cases"""
        return self.cases.count_documents({})

    def store_pdf(self, case_id: str, pdf_path: Path) -> str:
        """Store PDF in GridFS, returns file_id"""
        # Delete existing PDF for this case if any
        existing = self.fs.find_one({"case_id": case_id})
        if existing:
            self.fs.delete(existing._id)

        with open(pdf_path, "rb") as f:
            file_id = self.fs.put(
                f,
                filename=pdf_path.name,
                case_id=case_id,
            )
        return str(file_id)

    def get_pdf(self, case_id: str) -> tuple[bytes, str] | None:
        """Get PDF bytes and filename by case_id"""
        grid_out = self.fs.find_one({"case_id": case_id})
        if grid_out:
            return grid_out.read(), grid_out.filename
        return None

    def list_cases(self) -> list[dict]:
        """List all cases with basic info"""
        return list(self.cases.find(
            {},
            {"case_id": 1, "filename": 1, "page_count": 1, "_id": 0}
        ))

    def migrate_pdfs(self, pdf_dir: Path) -> int:
        """Migrate PDFs from directory to GridFS based on existing cases"""
        count = 0
        for case_doc in self.cases.find():
            case_id = case_doc["case_id"]
            filename = case_doc.get("filename", f"{case_id}.pdf")
            pdf_path = pdf_dir / filename

            if pdf_path.exists():
                # Check if already in GridFS
                if not self.fs.find_one({"case_id": case_id}):
                    self.store_pdf(case_id, pdf_path)
                    count += 1
                    print(f"Migrated: {case_id}")
        return count
