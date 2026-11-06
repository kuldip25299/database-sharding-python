```python
"""
Example 06: Database Query Router

Demonstrates how an application routes database operations
to the correct shard.

Responsibilities:

1. DatabaseShard:
   Stores and retrieves records.

2. ShardRouter:
   Determines which shard should receive a request.

3. ShardedDatabase:
   Coordinates the router and database shards.

The example uses modulo hashing:

    shard_id = user_id % number_of_shards

All data is stored in memory. No external database or Redis
is required.
"""


class DatabaseShard:
    def __init__(self, shard_id):
        self.shard_id = shard_id
        self.users = {}

    def insert(self, user):
        """Insert a user into this shard."""

        user_id = user["user_id"]

        if user_id in self.users:
            raise ValueError(
                f"User {user_id} already exists in Shard {self.shard_id}"
            )

        self.users[user_id] = user

    def get(self, user_id):
        """Retrieve a user by ID."""

        return self.users.get(user_id)

    def get_all(self):
        """Return all users stored in this shard."""

        return list(self.users.values())

    def count(self):
        """Return the number of users in this shard."""

        return len(self.users)


class ShardRouter:
    def __init__(self, number_of_shards):
        if number_of_shards <= 0:
            raise ValueError("Number of shards must be greater than zero")

        self.number_of_shards = number_of_shards

    def get_shard_id(self, user_id):
        """
        Determine the destination shard using modulo hashing.

        The same user ID always maps to the same shard as long
        as the shard count and routing configuration remain unchanged.
        """

        return int(user_id) % self.number_of_shards

    def get_shard_ids(self):
        """Return all configured shard IDs."""

        return list(range(self.number_of_shards))


class ShardedDatabase:
    def __init__(self, number_of_shards):
        self.router = ShardRouter(number_of_shards)

        self.shards = {
            shard_id: DatabaseShard(shard_id)
            for shard_id in self.router.get_shard_ids()
        }

    def insert_user(self, user):
        """Route a write operation to the correct shard."""

        user_id = user["user_id"]

        shard_id = self.router.get_shard_id(user_id)

        print(
            f"[ROUTER] INSERT user {user_id} -> Shard {shard_id}"
        )

        self.shards[shard_id].insert(user)

    def get_user(self, user_id):
        """Route a targeted read operation to one shard."""

        shard_id = self.router.get_shard_id(user_id)

        print(
            f"[ROUTER] GET user {user_id} -> Shard {shard_id}"
        )

        return self.shards[shard_id].get(user_id)

    def get_users_by_city(self, city):
        """
        Find users by city.

        City is not the shard key in this example.

        Therefore, the router cannot identify one specific shard.
        It must query every shard and combine the results.
        """

        print(
            f"\n[ROUTER] Searching all shards for city: {city}"
        )

        results = []

        for shard_id, shard in self.shards.items():
            print(f"[ROUTER] Querying Shard {shard_id}")

            shard_results = [
                user
                for user in shard.get_all()
                if user["city"].lower() == city.lower()
            ]

            results.extend(shard_results)

        return results

    def get_all_users(self):
        """
        Retrieve all users using a scatter-gather operation.

        Every shard is queried and the results are combined.
        """

        print("\n[ROUTER] Retrieving users from all shards")

        results = []

        for shard_id, shard in self.shards.items():
            print(f"[ROUTER] Querying Shard {shard_id}")

            results.extend(shard.get_all())

        return results

    def print_shard_distribution(self):
        """Display the number of records in each shard."""

        print("\nShard Distribution")
        print("-" * 50)

        for shard_id, shard in self.shards.items():
            print(
                f"Shard {shard_id}: "
                f"{shard.count()} users"
            )

        print("-" * 50)


def generate_sample_users():
    """Generate sample users for the demonstration."""

    return [
        {
            "user_id": 101,
            "name": "Alice",
            "city": "Pune",
        },
        {
            "user_id": 102,
            "name": "Bob",
            "city": "Mumbai",
        },
        {
            "user_id": 103,
            "name": "Charlie",
            "city": "Pune",
        },
        {
            "user_id": 104,
            "name": "David",
            "city": "Delhi",
        },
        {
            "user_id": 105,
            "name": "Emma",
            "city": "Mumbai",
        },
        {
            "user_id": 106,
            "name": "Frank",
            "city": "Pune",
        },
        {
            "user_id": 107,
            "name": "Grace",
            "city": "Bangalore",
        },
        {
            "user_id": 108,
            "name": "Henry",
            "city": "Delhi",
        },
        {
            "user_id": 109,
            "name": "Ivy",
            "city": "Mumbai",
        },
        {
            "user_id": 110,
            "name": "Jack",
            "city": "Bangalore",
        },
    ]


def main():
    print("=" * 60)
    print("DATABASE QUERY ROUTER")
    print("=" * 60)

    # --------------------------------------------------
    # 1. Initialize the sharded database
    # --------------------------------------------------

    database = ShardedDatabase(number_of_shards=4)

    # --------------------------------------------------
    # 2. Insert users
    # --------------------------------------------------

    print("\n1. Inserting users")

    users = generate_sample_users()

    for user in users:
        database.insert_user(user)

    database.print_shard_distribution()

    # --------------------------------------------------
    # 3. Targeted query using the shard key
    # --------------------------------------------------

    print("\n2. Targeted query using user_id")

    user = database.get_user(105)

    print(f"Query result: {user}")

    # Only one shard is accessed because user_id is
    # available for routing.

    # --------------------------------------------------
    # 4. Query for a non-existing user
    # --------------------------------------------------

    print("\n3. Query for a non-existing user")

    user = database.get_user(999)

    print(f"Query result: {user}")

    # The router still knows which shard to query,
    # even if the requested record does not exist.

    # --------------------------------------------------
    # 5. Query without the shard key
    # --------------------------------------------------

    print("\n4. Query users by city")

    pune_users = database.get_users_by_city("Pune")

    print("\nUsers found in Pune:")

    for user in pune_users:
        print(user)

    print(f"Total Pune users: {len(pune_users)}")

    # City is not the shard key, so every shard must
    # be checked in this implementation.

    # --------------------------------------------------
    # 6. Retrieve all users
    # --------------------------------------------------

    print("\n5. Retrieve all users")

    all_users = database.get_all_users()

    for user in all_users:
        print(user)

    print(f"\nTotal users: {len(all_users)}")

    # --------------------------------------------------
    # 7. Final distribution
    # --------------------------------------------------

    print("\n6. Final shard distribution")

    database.print_shard_distribution()

    print("\n" + "=" * 60)
    print("QUERY ROUTER DEMONSTRATION COMPLETED")
    print("=" * 60)


if __name__ == "__main__":
    main()
```
