```python
"""
Example 07: Database Shard Rebalancing

Demonstrates how records are redistributed when the number
of database shards changes.

Workflow:

1. Create a database with three shards.
2. Insert sample records using modulo hashing.
3. Record the original shard distribution.
4. Add a fourth shard.
5. Calculate the new destination for every record.
6. Move records to their new shards.
7. Verify that no records are lost or duplicated.

Routing formula:

    shard_id = record_id % number_of_shards

This example uses in-memory dictionaries.
No external database or Redis is required.

Note:
This is a simplified offline migration simulation. A production
migration must also handle concurrent reads and writes.
"""


class ShardedDatabase:
    def __init__(self, number_of_shards):
        if number_of_shards <= 0:
            raise ValueError("Number of shards must be greater than zero")

        self.number_of_shards = number_of_shards

        self.shards = {
            shard_id: {}
            for shard_id in range(number_of_shards)
        }

    def get_shard_id(self, record_id):
        """Calculate the destination shard using modulo hashing."""

        return int(record_id) % self.number_of_shards

    def insert(self, record):
        """Insert a record into its assigned shard."""

        record_id = record["id"]
        shard_id = self.get_shard_id(record_id)

        if record_id in self.shards[shard_id]:
            raise ValueError(f"Record {record_id} already exists")

        self.shards[shard_id][record_id] = record

    def get(self, record_id):
        """Retrieve a record from its assigned shard."""

        shard_id = self.get_shard_id(record_id)

        return self.shards[shard_id].get(record_id)

    def get_all_records(self):
        """Collect records from all shards."""

        records = {}

        for shard_records in self.shards.values():
            records.update(shard_records)

        return records

    def count_records(self):
        """Return the total number of records."""

        return sum(
            len(records)
            for records in self.shards.values()
        )

    def print_distribution(self, title):
        """Display record distribution across shards."""

        print(f"\n{title}")
        print("-" * 60)

        for shard_id, records in sorted(self.shards.items()):
            record_ids = sorted(records.keys())

            print(
                f"Shard {shard_id}: "
                f"{len(records)} records | "
                f"IDs: {record_ids}"
            )

        print("-" * 60)

        print(f"Total records: {self.count_records()}")


def rebalance_shards(database, new_shard_count):
    """
    Rebalance records after changing the shard count.

    This function:

    1. Collects all existing records.
    2. Creates the new shard layout.
    3. Calculates the destination of each record.
    4. Inserts each record into its new shard.
    5. Replaces the old shard layout.

    The operation is performed as a single in-memory
    migration for educational purposes.
    """

    if new_shard_count <= 0:
        raise ValueError("New shard count must be greater than zero")

    if new_shard_count == database.number_of_shards:
        print("\nShard count is unchanged. No migration required.")
        return {
            "moved": 0,
            "unchanged": database.count_records(),
            "total": database.count_records(),
        }

    print("\nStarting shard rebalancing")
    print("-" * 60)

    old_shard_count = database.number_of_shards

    # Collect all records before changing the shard layout.
    existing_records = database.get_all_records()

    # Create a new shard layout.
    new_shards = {
        shard_id: {}
        for shard_id in range(new_shard_count)
    }

    moved_records = 0
    unchanged_records = 0

    # Redistribute records using the new shard count.
    for record_id, record in existing_records.items():

        old_shard_id = record_id % old_shard_count
        new_shard_id = record_id % new_shard_count

        new_shards[new_shard_id][record_id] = record

        if old_shard_id != new_shard_id:
            moved_records += 1

            print(
                f"Record {record_id}: "
                f"Shard {old_shard_id} -> Shard {new_shard_id}"
            )
        else:
            unchanged_records += 1

    # Replace the old shard layout only after building
    # the complete new layout.
    database.shards = new_shards
    database.number_of_shards = new_shard_count

    print("-" * 60)
    print("Rebalancing completed.")

    return {
        "moved": moved_records,
        "unchanged": unchanged_records,
        "total": len(existing_records),
    }


def verify_records(database, original_records):
    """
    Verify that all original records still exist
    after rebalancing.
    """

    current_records = database.get_all_records()

    missing_records = (
        set(original_records.keys())
        - set(current_records.keys())
    )

    unexpected_records = (
        set(current_records.keys())
        - set(original_records.keys())
    )

    changed_records = [
        record_id
        for record_id, original_record in original_records.items()
        if current_records.get(record_id) != original_record
    ]

    print("\nMigration Verification")
    print("-" * 60)

    print(f"Original records: {len(original_records)}")
    print(f"Current records: {len(current_records)}")
    print(f"Missing records: {len(missing_records)}")
    print(f"Unexpected records: {len(unexpected_records)}")
    print(f"Changed records: {len(changed_records)}")

    if (
        not missing_records
        and not unexpected_records
        and not changed_records
    ):
        print("Verification successful: all records are intact.")
        return True

    print("Verification failed.")

    if missing_records:
        print(f"Missing IDs: {sorted(missing_records)}")

    if unexpected_records:
        print(f"Unexpected IDs: {sorted(unexpected_records)}")

    if changed_records:
        print(f"Changed IDs: {sorted(changed_records)}")

    return False


def main():
    print("=" * 65)
    print("DATABASE SHARD REBALANCING")
    print("=" * 65)

    # --------------------------------------------------
    # 1. Create initial database with three shards
    # --------------------------------------------------

    initial_shard_count = 3

    database = ShardedDatabase(
        number_of_shards=initial_shard_count
    )

    print(f"\nInitial shard count: {initial_shard_count}")

    # --------------------------------------------------
    # 2. Insert sample records
    # --------------------------------------------------

    print("\n1. Inserting records")

    for record_id in range(1, 21):
        database.insert({
            "id": record_id,
            "name": f"User {record_id}",
            "email": f"user{record_id}@example.com",
        })

    database.print_distribution(
        "Distribution Before Rebalancing"
    )

    # Keep a copy for migration verification.
    original_records = database.get_all_records().copy()

    # --------------------------------------------------
    # 3. Add a new shard through rebalancing
    # --------------------------------------------------

    new_shard_count = 4

    print("\n2. Changing shard count")
    print(f"Old shard count: {initial_shard_count}")
    print(f"New shard count: {new_shard_count}")

    migration_result = rebalance_shards(
        database,
        new_shard_count,
    )

    # --------------------------------------------------
    # 4. Inspect the new distribution
    # --------------------------------------------------

    print("\n3. Distribution after rebalancing")

    database.print_distribution(
        "Distribution After Rebalancing"
    )

    # --------------------------------------------------
    # 5. Display migration statistics
    # --------------------------------------------------

    print("\n4. Migration Statistics")
    print("-" * 60)

    print(f"Total records: {migration_result['total']}")
    print(f"Moved records: {migration_result['moved']}")
    print(f"Unchanged records: {migration_result['unchanged']}")

    if migration_result["total"]:
        movement_percentage = (
            migration_result["moved"]
            / migration_result["total"]
        ) * 100

        print(
            f"Movement percentage: "
            f"{movement_percentage:.2f}%"
        )

    # --------------------------------------------------
    # 6. Verify migrated records
    # --------------------------------------------------

    print("\n5. Verifying migrated records")

    verification_success = verify_records(
        database,
        original_records,
    )

    # --------------------------------------------------
    # 7. Test reads after migration
    # --------------------------------------------------

    print("\n6. Testing reads after migration")

    for record_id in [1, 5, 10, 15, 20]:
        record = database.get(record_id)

        shard_id = database.get_shard_id(record_id)

        print(
            f"Record {record_id} -> Shard {shard_id} | "
            f"Found: {record is not None}"
        )

    # --------------------------------------------------
    # 8. Final result
    # --------------------------------------------------

    print("\n" + "=" * 65)

    if verification_success:
        print("REBALANCING COMPLETED SUCCESSFULLY")
    else:
        print("REBALANCING VERIFICATION FAILED")

    print("=" * 65)


if __name__ == "__main__":
    main()
```
