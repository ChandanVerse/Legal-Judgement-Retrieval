"""Clear all data from Endee and MongoDB."""

from endee_db import EndeeDB


def main():
    # Connect to Endee
    endee = EndeeDB()
    endee.connect()

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

    # Show Endee stats
    endee_stats = endee.stats()
    vector_count = endee_stats.get("vector_count", 0) if isinstance(endee_stats, dict) else 0
    print(f"Endee vectors: {vector_count}")

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
        endee.delete_all()
        print(f"  Endee: {vector_count} vectors deleted")

    if mongo and case_count > 0:
        mongo.delete_all()
        print(f"  MongoDB: {case_count} cases deleted")

    print("\nDone.")


if __name__ == "__main__":
    main()
