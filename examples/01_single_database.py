```python
"""
Example 01: Single Database Simulation

Demonstrates how an application stores and retrieves records
using a single database before introducing database sharding.

This example uses an in-memory Python dictionary instead of
a real database so the core concept stays easy to understand.
"""


class SingleDatabase:
    def __init__(self):
        self.users = {}

    def insert_user(self, user_id, name, email):
        """Insert a new user into the database."""

        if user_id in self.users:
            raise ValueError(f"User {user_id} already exists")

        self.users[user_id] = {
            "user_id": user_id,
            "name": name,
            "email": email,
        }

    def get_user(self, user_id):
        """Retrieve a user using their ID."""

        return self.users.get(user_id)

    def update_user(self, user_id, **updates):
        """Update an existing user's fields."""

        if user_id not in self.users:
            return False

        self.users[user_id].update(updates)
        return True

    def delete_user(self, user_id):
        """Delete a user from the database."""

        if user_id not in self.users:
            return False

        del self.users[user_id]
        return True

    def get_all_users(self):
        """Return all users stored in the database."""

        return list(self.users.values())

    def get_users_by_name(self, name):
        """Find users by name."""

        return [
            user
            for user in self.users.values()
            if user["name"].lower() == name.lower()
        ]

    def count_users(self):
        """Return the total number of users."""

        return len(self.users)


def main():
    print("=" * 60)
    print("SINGLE DATABASE SIMULATION")
    print("=" * 60)

    # Create one database instance.
    database = SingleDatabase()

    # Insert sample users.
    print("\n1. Inserting users")

    sample_users = [
        (101, "Alice", "alice@example.com"),
        (102, "Bob", "bob@example.com"),
        (103, "Charlie", "charlie@example.com"),
        (104, "David", "david@example.com"),
        (105, "Alice", "alice2@example.com"),
    ]

    for user_id, name, email in sample_users:
        database.insert_user(user_id, name, email)
        print(f"Inserted user: {user_id} - {name}")

    # Retrieve one user.
    print("\n2. Retrieving a user")

    user = database.get_user(102)
    print(f"User found: {user}")

    # Update an existing user.
    print("\n3. Updating a user")

    updated = database.update_user(
        102,
        email="bob.new@example.com",
    )

    if updated:
        print(f"Updated user: {database.get_user(102)}")

    # Query users by name.
    print("\n4. Finding users by name")

    alice_users = database.get_users_by_name("Alice")

    for user in alice_users:
        print(user)

    # Retrieve all users.
    print("\n5. Retrieving all users")

    for user in database.get_all_users():
        print(user)

    # Show total records.
    print("\n6. Database statistics")

    print(f"Total users: {database.count_users()}")

    # Delete a user.
    print("\n7. Deleting a user")

    deleted = database.delete_user(104)
    print(f"User 104 deleted: {deleted}")

    print(f"Total users after deletion: {database.count_users()}")

    print("\n" + "=" * 60)
    print("FINAL DATABASE STATE")
    print("=" * 60)

    for user in database.get_all_users():
        print(user)


if __name__ == "__main__":
    main()
```
