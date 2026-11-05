```python
"""
Example 04: Shard Key Distribution

Demonstrates how different shard keys affect data distribution
across database shards.

We compare three shard keys:

1. user_id       - High-cardinality numeric identifier.
2. region        - Low-cardinality geographic value.
3. account_type  - Low-cardinality business attribute.

The same modulo-based routing formula is used for each strategy:

    shard_id = hash(shard_key) % number_of_shards

For string keys, Python's built-in hash() is randomized between
processes by default. Therefore, this example uses a stable hash
function so that results remain reproducible across runs.

This is an educational simulation using in-memory dictionaries.
"""


import hashlib
from collections import Counter, defaultdict


class ShardKeyDistribution:
    def __init__(self, number_of_shards):
        if number_of_shards <= 0:
            raise ValueError("Number of shards must be greater than zero")

        self.number_of_shards = number_of_shards
        self.shards = {
            shard_id: {}
            for shard_id in range(number_of_shards)
        }

    def stable_hash(self, value):
        """
        Generate a deterministic hash for a shard key.

        hashlib.sha256() produces the same hash for the same input,
        unlike Python's built-in hash() for strings.
        """

        value = str(value).encode("utf-8")
        digest = hashlib.sha256(value).hexdigest()

        return int(digest, 16)

    def get_shard_id(self, shard_key):
        """Calculate the shard for a given shard key."""

        if isinstance(shard_key, int):
            hash_value = shard_key
        else:
            hash_value = self.stable_hash(shard_key)

        return hash_value % self.number_of_shards

    def distribute_records(self, records, shard_key_field):
        """
        Distribute records using the selected shard key.

        Existing shard contents are cleared so the same instance
        can be reused for comparing different shard keys.
        """

        self.shards = {
            shard_id: {}
            for shard_id in range(self.number_of_shards)
        }

        for record in records:
            shard_key = record[shard_key_field]
            shard_id = self.get_shard_id(shard_key)

            record_id = record["user_id"]

            self.shards[shard_id][record_id] = record

    def get_distribution(self):
        """Return the number of records in each shard."""

        return {
            shard_id: len(records)
            for shard_id, records in self.shards.items()
        }

    def get_total_records(self):
        """Return the total number of stored records."""

        return sum(
            len(records)
            for records in self.shards.values()
        )

    def print_distribution(self, shard_key_field):
        """Print record counts and percentages per shard."""

        distribution = self.get_distribution()
        total_records = self.get_total_records()

        print(f"\nShard key: {shard_key_field}")
        print("-" * 55)

        for shard_id, count in distribution.items():
            percentage = (
                (count / total_records) * 100
                if total_records
                else 0
            )

            print(
                f"Shard {shard_id}: "
                f"{count:3} records "
                f"({percentage:5.1f}%)"
            )

        print("-" * 55)

        print(f"Total records: {total_records}")

        if total_records:
            average = total_records / self.number_of_shards
            print(f"Average records per shard: {average:.2f}")

        return distribution


def generate_sample_users():
    """
    Generate sample users with realistic differences in
    shard key cardinality.

    The dataset intentionally contains:
    - Unique user IDs.
    - A small set of regions.
    - A small set of account types.
    """

    regions = [
        "Pune",
        "Mumbai",
        "Delhi",
        "Bangalore",
    ]

    account_types = [
        "free",
        "premium",
    ]

    users = []

    for user_id in range(1, 101):
        users.append({
            "user_id": user_id,
            "name": f"User {user_id}",
            "region": regions[(user_id - 1) % len(regions)],
            "account_type": account_types[(user_id - 1) % 2],
        })

    return users


def print_key_cardinality(records):
    """Show the number of unique values for each candidate key."""

    fields = [
        "user_id",
        "region",
        "account_type",
    ]

    print("\nShard Key Cardinality")
    print("-" * 55)

    for field in fields:
        unique_values = {
            record[field]
            for record in records
        }

        print(
            f"{field:15} "
            f"Unique values: {len(unique_values)}"
        )

    print("-" * 55)


def calculate_distribution_quality(distribution):
    """
    Calculate the percentage difference between the largest
    and smallest shard.

    This is a simple distribution indicator, not a complete
    measure of shard workload or performance.
    """

    counts = list(distribution.values())

    if not counts:
        return 0

    total = sum(counts)

    if total == 0:
        return 0

    average = total / len(counts)

    if average == 0:
        return 0

    difference = max(counts) - min(counts)

    return (difference / average) * 100


def main():
    print("=" * 60)
    print("SHARD KEY DISTRIBUTION")
    print("=" * 60)

    number_of_shards = 4

    users = generate_sample_users()

    print(f"\nTotal users: {len(users)}")
    print(f"Number of shards: {number_of_shards}")

    # --------------------------------------------------
    # 1. Understand candidate shard keys
    # --------------------------------------------------

    print_key_cardinality(users)

    # --------------------------------------------------
    # 2. Compare user_id distribution
    # --------------------------------------------------

    database = ShardKeyDistribution(number_of_shards)

    print("\n1. Distribution using user_id")

    database.distribute_records(users, "user_id")

    user_id_distribution = database.print_distribution(
        "user_id"
    )

    # --------------------------------------------------
    # 3. Compare region distribution
    # --------------------------------------------------

    print("\n2. Distribution using region")

    database.distribute_records(users, "region")

    region_distribution = database.print_distribution(
        "region"
    )

    # --------------------------------------------------
    # 4. Compare account_type distribution
    # --------------------------------------------------

    print("\n3. Distribution using account_type")

    database.distribute_records(users, "account_type")

    account_type_distribution = database.print_distribution(
        "account_type"
    )

    # --------------------------------------------------
    # 5. Compare distribution quality
    # --------------------------------------------------

    print("\n4. Distribution Comparison")
    print("-" * 55)

    comparisons = {
        "user_id": user_id_distribution,
        "region": region_distribution,
        "account_type": account_type_distribution,
    }

    for key_name, distribution in comparisons.items():
        difference = calculate_distribution_quality(
            distribution
        )

        print(
            f"{key_name:15} "
            f"Max-min difference: {difference:.1f}%"
        )

    print("-" * 55)

    # --------------------------------------------------
    # 6. Demonstrate a low-cardinality key
    # --------------------------------------------------

    print("\n5. Inspecting account_type placement")

    database.distribute_records(users, "account_type")

    for shard_id, records in database.shards.items():
        account_types = Counter(
            record["account_type"]
            for record in records.values()
        )

        print(
            f"Shard {shard_id}: "
            f"{dict(account_types)}"
        )

    # --------------------------------------------------
    # 7. Final observations
    # --------------------------------------------------

    print("\n6. Observations")

    print(
        "- user_id has high cardinality and distributes "
        "these sample records evenly."
    )

    print(
        "- region has only a few distinct values, so records "
        "can be concentrated on a small number of shards."
    )

    print(
        "- account_type has only two distinct values, which "
        "can create severe shard concentration."
    )

    print(
        "- Even record distribution does not guarantee "
        "even request traffic."
    )

    print("\n" + "=" * 60)
    print("SHARD KEY DISTRIBUTION COMPLETED")
    print("=" * 60)


if __name__ == "__main__":
    main()
```
