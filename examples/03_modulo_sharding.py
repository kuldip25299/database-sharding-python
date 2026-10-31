```python
"""
Example 03: Modulo-Based Database Sharding

Demonstrates:
1. Distributing records using modulo hashing.
2. Routing read and write operations to the correct shard.
3. Checking record distribution.
4. Understanding the impact of increasing the shard count.

Formula:

    shard_id = shard_key % number_of_shards

Each shard is represented by an in-memory dictionary.
No external database or Redis is required.
"""


class ModuloShardingDatabase:
    def __init__(self, number_of_shards):
        if number_of_shards <= 0:
            raise ValueError("Number of shards must be greater than zero")

        self.number_of_shards = number_of_shards

        self.shards = {
            shard_id: {}
            for shard_id in range(number_of_shards)
        }

    def get_shard_id(self, shard_key):
        """Calculate the shard using modulo hashing."""

        return int(shard_key) % self.number_of_shards

    def insert(self, shard_key, data):
        """Insert a record into its assigned shard."""

        shard_id = self.get_shard_id(shard_key)

        if shard_key in self.shards[shard_id]:
            raise ValueError(f"Record {shard_key} already exists")

        self.shards[shard_id][shard_key] = data

        print(
            f"Inserted record {shard_key} into Shard {shard_id}"
        )

    def get(self, shard_key):
        """Retrieve a record using its shard key."""

        shard_id = self.get_shard_id(shard_key)

        print(
            f"Routing record {shard_key} to Shard {shard_id}"
        )

        return self.shards[shard_id].get(shard_key)

    def delete(self, shard_key):
        """Delete a record from its assigned shard."""

        shard_id = self.get_shard_id(shard_key)

        if shard_key not in self.shards[shard_id]:
            return False

        del self.shards[shard_id][shard_key]
        return True

    def get_all_records(self):
        """Collect records from all shards."""

        records = {}

        for shard in self.shards.values():
            records.update(shard)

        return records

    def print_distribution(self):
        """Display the records assigned to each shard."""

        print("\nCurrent Shard Distribution")
        print("-" * 50)

        for shard_id, records in self.shards.items():
            keys = list(records.keys())

            print(
                f"Shard {shard_id}: "
                f"{len(records)} records | "
                f"Keys: {keys}"
            )

        print("-" * 50)


def calculate_new_shard_mapping(record_keys, number_of_shards):
    """
    Calculate where existing records would be routed
    if the shard count changed.

    This only calculates the new destination.
    It does not move any actual records.
    """

    mapping = {}

    for key in record_keys:
        new_shard_id = key % number_of_shards
        mapping[key] = new_shard_id

    return mapping


def main():
    print("=" * 60)
    print("MODULO-BASED DATABASE SHARDING")
    print("=" * 60)

    # --------------------------------------------------
    # 1. Create database with four shards
    # --------------------------------------------------

    database = ModuloShardingDatabase(number_of_shards=4)

    # --------------------------------------------------
    # 2. Insert sample records
    # --------------------------------------------------

    print("\n1. Inserting records")

    sample_records = [
        (101, {"name": "Alice", "city": "Pune"}),
        (102, {"name": "Bob", "city": "Mumbai"}),
        (103, {"name": "Charlie", "city": "Delhi"}),
        (104, {"name": "David", "city": "Bangalore"}),
        (105, {"name": "Emma", "city": "Pune"}),
        (106, {"name": "Frank", "city": "Mumbai"}),
        (107, {"name": "Grace", "city": "Delhi"}),
        (108, {"name": "Henry", "city": "Bangalore"}),
        (109, {"name": "Ivy", "city": "Pune"}),
        (110, {"name": "Jack", "city": "Mumbai"}),
        (111, {"name": "Kate", "city": "Delhi"}),
        (112, {"name": "Leo", "city": "Bangalore"}),
    ]

    for key, data in sample_records:
        database.insert(key, data)

    # --------------------------------------------------
    # 3. Inspect distribution
    # --------------------------------------------------

    print("\n2. Checking distribution")

    database.print_distribution()

    # --------------------------------------------------
    # 4. Retrieve records
    # --------------------------------------------------

    print("\n3. Retrieving records")

    record = database.get(105)
    print(f"Record 105: {record}")

    record = database.get(110)
    print(f"Record 110: {record}")

    # --------------------------------------------------
    # 5. Delete a record
    # --------------------------------------------------

    print("\n4. Deleting a record")

    deleted = database.delete(108)
    print(f"Record 108 deleted: {deleted}")

    database.print_distribution()

    # --------------------------------------------------
    # 6. Demonstrate shard count change
    # --------------------------------------------------

    print("\n5. Demonstrating shard count change")

    existing_keys = list(database.get_all_records().keys())

    old_shard_count = 4
    new_shard_count = 5

    print(
        f"\nExisting shard count: {old_shard_count}"
    )
    print(
        f"New shard count: {new_shard_count}"
    )

    print("\nRecord placement before shard count change:")

    for key in existing_keys:
        old_shard_id = key % old_shard_count
        print(f"Record {key} -> Shard {old_shard_id}")

    new_mapping = calculate_new_shard_mapping(
        existing_keys,
        new_shard_count,
    )

    print("\nRecord placement after shard count change:")

    for key, new_shard_id in new_mapping.items():
        old_shard_id = key % old_shard_count

        moved = old_shard_id != new_shard_id

        print(
            f"Record {key}: "
            f"Shard {old_shard_id} -> Shard {new_shard_id} "
            f"| Moved: {moved}"
        )

    moved_count = sum(
        1
        for key, new_shard_id in new_mapping.items()
        if key % old_shard_count != new_shard_id
    )

    print(
        f"\nRecords requiring relocation: "
        f"{moved_count}/{len(existing_keys)}"
    )

    # --------------------------------------------------
    # 7. Final database state
    # --------------------------------------------------

    print("\n6. Final database state")

    database.print_distribution()

    print(
        f"Total records: {len(database.get_all_records())}"
    )

    print("\n" + "=" * 60)
    print("MODULO SHARDING DEMONSTRATION COMPLETED")
    print("=" * 60)


if __name__ == "__main__":
    main()
```
