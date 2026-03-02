"""Clear all data from Pinecone and MongoDB."""

from pinecone_db import PineconeDB


def main():
    # Connect to Pinecone
    pinecone = PineconeDB()
    pinecone.connect()

    # Try MongoDB (may fail if cluster is paused)
    mongo = None
    case_count = 0
    try:
        from mongo_db import MongoDB
        mongo = MongoDB()
        case_count = mongo.count()
        print(f"MongoDB cases: {case_count}")
    except Exception as e:
        print(f"MongoDB: Connection failed ({type(e).__name__})")
        print("  (Cluster may be paused - check MongoDB Atlas)")

    # Show Pinecone stats
    pinecone_stats = pinecone.stats()
    vector_count = pinecone_stats.total_vector_count
    print(f"Pinecone vectors: {vector_count}")

    if vector_count == 0 and case_count == 0:
        print("\nDatabases are already empty.")
        return

    # Confirm
    confirm = input(f"\nDelete all data? (yes/no): ")
    if confirm.lower() != "yes":
        print("Cancelled.")
        return

    # Clear databases
    print("\nClearing databases...")

    if vector_count > 0:
        pinecone.delete_all()
        print(f"  Pinecone: {vector_count} vectors deleted")

    if mongo and case_count > 0:
        mongo.delete_all()
        print(f"  MongoDB: {case_count} cases deleted")

    print("\nDone.")


if __name__ == "__main__":
    main()
