```python
"""
Example 02: Naive Database Sharding

Demonstrates how records can be distributed across multiple
database shards instead of storing everything in one database.

Each shard is represented by an in-memory Python dictionary.

This is intentionally a simple implementation. The next example
will introduce modulo hashing for shard selection.
"""


class DatabaseShard:
    def __init__(self, shard_id):
        self.shard_id = shard_id
        self.users = {}

    def insert_user(self, user):
        """Insert a user into this shard."""

        user_id = user["user_id"]

        if user_id in self.users:
            raise ValueError(
                f"User {user_id} already exists in Shard {self.shard_id}"
            )

        self.users[user_id] = user

    def get_user(self, user_id):
        """Retrieve a user from this shard."""

        return self.users.get(user_id)

    def get_all_users(self):
        """Return all users stored in this shard."""

        return list(self.users.values())

    def count_users(self):
        """Return the number of users in this shard."""

        return len(self.users)


class NaiveShardingDatabase:
    def __init__(self, number_of_shards):
        if number_of_shards <= 0:
            raise ValueError("Number of shards must be greater than zero")

        self.number_of_shards = number_of_shards

        self.shards = {
            shard_id: DatabaseShard(shard_id)
            for shard_id in range(number_of_shards)
        }

    def get_shard_id(self, user_id):
        """
        Simple routing rule:

        Convert user_id to an integer and use modulo to select
        a shard.

        This is a basic demonstration of shard routing.
        """

        return int(user_id) % self.number_of_shards

    def insert_user(self, user):
        """Route a user to the appropriate shard."""

        user_id = user["user_id"]
        shard_id = self.get_shard_id(user_id)

        self.shards[shard_id].insert_user(user)

        print(
            f"Inserted user {user_id} into Shard {shard_id}"
        )

    def get_user(self, user_id):
        """Find the correct shard and retrieve the user."""

        shard_id = self.get_shard_id(user_id)

        print(
            f"Routing user {user_id} to Shard {shard_id}"
        )

        return self.shards[shard_id].get_user(user_id)

    def get_all_users(self):
        """
        Retrieve users from every shard.

        This is a simple scatter-gather operation:
        query all shards and combine their results.
        """

        users = []

        for shard in self.shards.values():
            users.extend(shard.get_all_users())

        return users

    def print_shard_distribution(self):
        """Display how records are distributed across shards."""

        print("\nShard Distribution")
        print("-" * 40)

        for shard_id, shard in self.shards.items():
            user_ids = list(shard.users.keys())

            print(
                f"Shard {shard_id}: "
                f"{shard.count_users()} users | "
                f"User IDs: {user_ids}"
            )

        print("-" * 40)


def main():
    print("=" * 60)
    print("NAIVE DATABASE SHARDING")
    print("=" * 60)

    # Create a database with four shards.
    database = NaiveShardingDatabase(number_of_shards=4)

    # Sample users.
    sample_users = [
        {"user_id": 101, "name": "Alice", "email": "alice@example.com"},
        {"user_id": 102, "name": "Bob", "email": "bob@example.com"},
        {"user_id": 103, "name": "Charlie", "email": "charlie@example.com"},
        {"user_id": 104, "name": "David", "email": "david@example.com"},
        {"user_id": 105, "name": "Emma", "email": "emma@example.com"},
        {"user_id": 106, "name": "Frank", "email": "frank@example.com"},
        {"user_id": 107, "name": "Grace", "email": "grace@example.com"},
        {"user_id": 108, "name": "Henry", "email": "henry@example.com"},
        {"user_id": 109, "name": "Ivy", "email": "ivy@example.com"},
        {"user_id": 110, "name": "Jack", "email": "jack@example.com"},
    ]

    # Insert users.
    print("\n1. Inserting users")

    for user in sample_users:
        database.insert_user(user)

    # Display record distribution.
    print("\n2. Checking shard distribution")

    database.print_shard_distribution()

    # Retrieve one user.
    print("\n3. Retrieving a user")

    user = database.get_user(105)
    print(f"Retrieved user: {user}")

    # Retrieve a user that does not exist.
    print("\n4. Retrieving a non-existing user")

    user = database.get_user(999)
    print(f"Retrieved user: {user}")

    # Retrieve all users across all shards.
    print("\n5. Retrieving all users across shards")

    all_users = database.get_all_users()

    for user in all_users:
        print(user)

    print(f"\nTotal users across all shards: {len(all_users)}")

    print("\n" + "=" * 60)
    print("NAIVE SHARDING COMPLETED")
    print("=" * 60)


if __name__ == "__main__":
    main()
```
