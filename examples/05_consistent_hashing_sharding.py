```python
"""
Example 05: Consistent Hashing for Database Sharding

Demonstrates:
1. Creating a consistent hashing ring.
2. Placing physical shards on the ring using virtual nodes.
3. Routing records to the next available node clockwise.
4. Adding a new shard.
5. Measuring how many records move after adding a shard.
6. Comparing record movement with modulo hashing.

All shards are represented by in-memory dictionaries.

No external database or Redis is required.
"""

import hashlib
from bisect import bisect_left


class ConsistentHashingDatabase:
    def __init__(self, virtual_nodes=100):
        if virtual_nodes <= 0:
            raise ValueError("Virtual nodes must be greater than zero")

        self.virtual_nodes = virtual_nodes

        # Maps hash positions to physical shard IDs.
        self.ring = {}

        # Sorted hash positions for efficient lookup.
        self.sorted_keys = []

        # Stores records by physical shard ID.
        self.shards = {}

    @staticmethod
    def hash_value(value):
        """
        Generate a stable hash using SHA-256.

        A deterministic hash is important because the same key
        must always map to the same position on the ring.
        """

        value = str(value).encode("utf-8")
        digest = hashlib.sha256(value).hexdigest()

        return int(digest, 16)

    def add_shard(self, shard_id):
        """
        Add a physical shard to the hash ring.

        Each physical shard receives multiple virtual nodes.
        """

        if shard_id in self.shards:
            raise ValueError(f"Shard {shard_id} already exists")

        self.shards[shard_id] = {}

        for replica in range(self.virtual_nodes):
            virtual_node = f"{shard_id}:vn:{replica}"
            position = self.hash_value(virtual_node)

            if position in self.ring:
                raise ValueError("Hash collision detected")

            self.ring[position] = shard_id

        self.sorted_keys = sorted(self.ring.keys())

    def remove_shard(self, shard_id):
        """Remove a physical shard and its virtual nodes."""

        if shard_id not in self.shards:
            raise ValueError(f"Shard {shard_id} does not exist")

        positions_to_remove = [
            position
            for position, owner in self.ring.items()
            if owner == shard_id
        ]

        for position in positions_to_remove:
            del self.ring[position]

        del self.shards[shard_id]

        self.sorted_keys = sorted(self.ring.keys())

    def get_shard_id(self, record_key):
        """
        Find the first virtual node clockwise from the record's
        hash position.

        If the hash position is beyond the last ring position,
        wrap around to the first position.
        """

        if not self.sorted_keys:
            raise RuntimeError("No shards available")

        position = self.hash_value(record_key)

        index = bisect_left(self.sorted_keys, position)

        if index == len(self.sorted_keys):
            index = 0

        ring_position = self.sorted_keys[index]

        return self.ring[ring_position]

    def insert(self, record_key, data):
        """Route and insert a record into its assigned shard."""

        shard_id = self.get_shard_id(record_key)

        self.shards[shard_id][record_key] = data

    def get(self, record_key):
        """Route and retrieve a record from its assigned shard."""

        shard_id = self.get_shard_id(record_key)

        return self.shards[shard_id].get(record_key)

    def get_all_records(self):
        """Collect all records from every shard."""

        records = {}

        for shard_records in self.shards.values():
            records.update(shard_records)

        return records

    def get_record_mapping(self):
        """Return the current shard assignment for every record."""

        mapping = {}

        for shard_id, records in self.shards.items():
            for record_key in records:
                mapping[record_key] = shard_id

        return mapping

    def print_distribution(self):
        """Display record counts for every physical shard."""

        print("\nShard Distribution")
        print("-" * 55)

        for shard_id, records in sorted(self.shards.items()):
            print(
                f"Shard {shard_id}: "
                f"{len(records)} records"
            )

        print("-" * 55)


def calculate_modulo_mapping(record_keys, number_of_shards):
    """
    Calculate record placement using modulo hashing.

    This function is used only for comparing redistribution.
    """

    return {
        key: int(key) % number_of_shards
        for key in record_keys
    }


def count_moved_records(old_mapping, new_mapping):
    """Count records whose shard assignment changed."""

    return sum(
        1
        for key, old_shard in old_mapping.items()
        if new_mapping.get(key) != old_shard
    )


def main():
    print("=" * 65)
    print("CONSISTENT HASHING FOR DATABASE SHARDING")
    print("=" * 65)

    # --------------------------------------------------
    # 1. Create a database with three physical shards
    # --------------------------------------------------

    database = ConsistentHashingDatabase(
        virtual_nodes=100
    )

    initial_shards = [
        "shard-1",
        "shard-2",
        "shard-3",
    ]

    print("\n1. Creating initial shards")

    for shard_id in initial_shards:
        database.add_shard(shard_id)
        print(f"Added {shard_id}")

    # --------------------------------------------------
    # 2. Insert sample records
    # --------------------------------------------------

    print("\n2. Inserting records")

    total_records = 1000

    for user_id in range(1, total_records + 1):
        database.insert(
            user_id,
            {
                "user_id": user_id,
                "name": f"User {user_id}",
            },
        )

    database.print_distribution()

    # --------------------------------------------------
    # 3. Save original record mapping
    # --------------------------------------------------

    print("\n3. Saving original record placement")

    old_mapping = database.get_record_mapping()

    print(f"Total mapped records: {len(old_mapping)}")

    # --------------------------------------------------
    # 4. Retrieve sample records
    # --------------------------------------------------

    print("\n4. Retrieving sample records")

    for user_id in [101, 250, 500, 750, 999]:
        shard_id = database.get_shard_id(user_id)
        record = database.get(user_id)

        print(
            f"User {user_id} -> {shard_id} | "
            f"Found: {record is not None}"
        )

    # --------------------------------------------------
    # 5. Add a new physical shard
    # --------------------------------------------------

    print("\n5. Adding a new shard")

    database.add_shard("shard-4")

    print("Added shard-4")

    # --------------------------------------------------
    # 6. Calculate new record placement
    # --------------------------------------------------

    print("\n6. Measuring record redistribution")

    new_mapping = {
        user_id: database.get_shard_id(user_id)
        for user_id in old_mapping
    }

    moved_records = count_moved_records(
        old_mapping,
        new_mapping,
    )

    movement_percentage = (
        moved_records / total_records
    ) * 100

    print(f"Total records: {total_records}")
    print(f"Records moved: {moved_records}")
    print(f"Records unchanged: {total_records - moved_records}")
    print(f"Movement percentage: {movement_percentage:.2f}%")

    # --------------------------------------------------
    # 7. Compare with modulo hashing
    # --------------------------------------------------

    print("\n7. Comparing with modulo hashing")

    old_modulo_mapping = calculate_modulo_mapping(
        range(1, total_records + 1),
        3,
    )

    new_modulo_mapping = calculate_modulo_mapping(
        range(1, total_records + 1),
        4,
    )

    modulo_moved = count_moved_records(
        old_modulo_mapping,
        new_modulo_mapping,
    )

    modulo_percentage = (
        modulo_moved / total_records
    ) * 100

    print(f"Modulo records moved: {modulo_moved}")
    print(f"Modulo movement percentage: {modulo_percentage:.2f}%")

    print(
        f"Consistent hashing records moved: {moved_records}"
    )

    print(
        f"Consistent hashing movement percentage: "
        f"{movement_percentage:.2f}%"
    )

    # --------------------------------------------------
    # 8. Inspect final shard distribution
    # --------------------------------------------------

    print("\n8. Final shard distribution")

    database.print_distribution()

    # --------------------------------------------------
    # 9. Verify that all records are still available
    # --------------------------------------------------

    print("\n9. Verifying stored records")

    all_records = database.get_all_records()

    missing_records = [
        user_id
        for user_id in range(1, total_records + 1)
        if user_id not in all_records
    ]

    print(f"Total records after adding shard: {len(all_records)}")
    print(f"Missing records: {len(missing_records)}")

    if missing_records:
        print(f"Missing record IDs: {missing_records[:10]}")
    else:
        print("All records are still present.")

    print("\n" + "=" * 65)
    print("CONSISTENT HASHING DEMONSTRATION COMPLETED")
    print("=" * 65)


if __name__ == "__main__":
    main()
```
