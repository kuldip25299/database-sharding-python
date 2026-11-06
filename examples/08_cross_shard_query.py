```python
"""
Example 08: Cross-Shard Queries

Demonstrates how an application handles queries that require
data from multiple database shards.

This example uses user_id as the shard key:

    shard_id = user_id % number_of_shards

It demonstrates:

1. Targeted queries using the shard key.
2. Scatter-gather queries across all shards.
3. Aggregation of results from multiple shards.
4. Global sorting across shard results.
5. Pagination after combining results.

All shards are represented by in-memory dictionaries.

No external database or Redis is required.
"""


class DatabaseShard:
    def __init__(self, shard_id):
        self.shard_id = shard_id
        self.orders = {}

    def insert_order(self, order):
        """Insert an order into this shard."""

        order_id = order["order_id"]

        if order_id in self.orders:
            raise ValueError(
                f"Order {order_id} already exists in Shard {self.shard_id}"
            )

        self.orders[order_id] = order

    def get_orders_by_user(self, user_id):
        """Return orders belonging to a specific user."""

        return [
            order
            for order in self.orders.values()
            if order["user_id"] == user_id
        ]

    def get_all_orders(self):
        """Return all orders stored in this shard."""

        return list(self.orders.values())

    def get_total_sales(self):
        """Calculate total sales for this shard."""

        return sum(
            order["amount"]
            for order in self.orders.values()
        )


class ShardRouter:
    def __init__(self, number_of_shards):
        if number_of_shards <= 0:
            raise ValueError("Number of shards must be greater than zero")

        self.number_of_shards = number_of_shards

    def get_shard_id(self, user_id):
        """Route a user to their assigned shard."""

        return int(user_id) % self.number_of_shards


class ShardedOrderDatabase:
    def __init__(self, number_of_shards):
        self.router = ShardRouter(number_of_shards)

        self.shards = {
            shard_id: DatabaseShard(shard_id)
            for shard_id in range(number_of_shards)
        }

    def insert_order(self, order):
        """Route an order using its user's ID."""

        user_id = order["user_id"]

        shard_id = self.router.get_shard_id(user_id)

        self.shards[shard_id].insert_order(order)

        print(
            f"Inserted Order {order['order_id']} "
            f"for User {user_id} -> Shard {shard_id}"
        )

    def get_orders_by_user(self, user_id):
        """
        Targeted query.

        Since user_id is the shard key, only one shard
        needs to be queried.
        """

        shard_id = self.router.get_shard_id(user_id)

        print(
            f"\n[ROUTER] User {user_id} -> Shard {shard_id}"
        )

        return self.shards[shard_id].get_orders_by_user(user_id)

    def get_all_orders(self):
        """
        Scatter-gather query.

        Every shard is queried and its results are combined.
        """

        print("\n[ROUTER] Starting scatter-gather query")

        all_orders = []

        for shard_id, shard in self.shards.items():
            print(f"[ROUTER] Querying Shard {shard_id}")

            shard_orders = shard.get_all_orders()

            all_orders.extend(shard_orders)

        print(
            f"[ROUTER] Combined {len(all_orders)} orders"
        )

        return all_orders

    def get_total_sales(self):
        """
        Aggregate total sales across all shards.

        Each shard calculates its local total.
        The application combines those totals.
        """

        print("\n[ROUTER] Calculating total sales")

        total_sales = 0

        for shard_id, shard in self.shards.items():
            shard_total = shard.get_total_sales()

            print(
                f"Shard {shard_id} sales: "
                f"₹{shard_total:.2f}"
            )

            total_sales += shard_total

        return total_sales

    def get_top_orders(self, limit=5):
        """
        Return the highest-value orders across all shards.

        Each shard's results are combined before global sorting.
        """

        if limit < 0:
            raise ValueError("Limit cannot be negative")

        all_orders = self.get_all_orders()

        sorted_orders = sorted(
            all_orders,
            key=lambda order: order["amount"],
            reverse=True,
        )

        return sorted_orders[:limit]

    def get_paginated_orders(self, page=1, page_size=5):
        """
        Perform global pagination.

        For this educational example, all records are collected
        and sorted before applying pagination.

        This is simple but can become expensive for large datasets.
        """

        if page < 1:
            raise ValueError("Page must be greater than or equal to 1")

        if page_size <= 0:
            raise ValueError("Page size must be greater than zero")

        all_orders = self.get_all_orders()

        sorted_orders = sorted(
            all_orders,
            key=lambda order: order["order_id"],
        )

        start = (page - 1) * page_size
        end = start + page_size

        return {
            "page": page,
            "page_size": page_size,
            "total_records": len(sorted_orders),
            "total_pages": (
                (len(sorted_orders) + page_size - 1) // page_size
            ),
            "orders": sorted_orders[start:end],
        }

    def print_distribution(self):
        """Display the number of orders stored in each shard."""

        print("\nOrder Distribution")
        print("-" * 50)

        for shard_id, shard in self.shards.items():
            print(
                f"Shard {shard_id}: "
                f"{len(shard.orders)} orders"
            )

        print("-" * 50)


def generate_sample_orders():
    """Generate sample e-commerce orders."""

    return [
        {
            "order_id": 1001,
            "user_id": 101,
            "product": "Laptop",
            "amount": 65000,
        },
        {
            "order_id": 1002,
            "user_id": 102,
            "product": "Mobile",
            "amount": 25000,
        },
        {
            "order_id": 1003,
            "user_id": 103,
            "product": "Headphones",
            "amount": 3000,
        },
        {
            "order_id": 1004,
            "user_id": 104,
            "product": "Monitor",
            "amount": 12000,
        },
        {
            "order_id": 1005,
            "user_id": 101,
            "product": "Keyboard",
            "amount": 2000,
        },
        {
            "order_id": 1006,
            "user_id": 105,
            "product": "Camera",
            "amount": 45000,
        },
        {
            "order_id": 1007,
            "user_id": 106,
            "product": "Mouse",
            "amount": 1500,
        },
        {
            "order_id": 1008,
            "user_id": 102,
            "product": "Tablet",
            "amount": 18000,
        },
        {
            "order_id": 1009,
            "user_id": 107,
            "product": "Smartwatch",
            "amount": 8000,
        },
        {
            "order_id": 1010,
            "user_id": 108,
            "product": "Television",
            "amount": 55000,
        },
        {
            "order_id": 1011,
            "user_id": 109,
            "product": "Speaker",
            "amount": 6000,
        },
        {
            "order_id": 1012,
            "user_id": 110,
            "product": "Gaming Console",
            "amount": 42000,
        },
    ]


def main():
    print("=" * 65)
    print("CROSS-SHARD QUERY DEMONSTRATION")
    print("=" * 65)

    # --------------------------------------------------
    # 1. Create a database with four shards
    # --------------------------------------------------

    database = ShardedOrderDatabase(
        number_of_shards=4
    )

    # --------------------------------------------------
    # 2. Insert sample orders
    # --------------------------------------------------

    print("\n1. Inserting orders")

    orders = generate_sample_orders()

    for order in orders:
        database.insert_order(order)

    database.print_distribution()

    # --------------------------------------------------
    # 3. Targeted query
    # --------------------------------------------------

    print("\n2. Getting orders for one user")

    user_orders = database.get_orders_by_user(101)

    for order in user_orders:
        print(order)

    print(f"Orders found: {len(user_orders)}")

    # --------------------------------------------------
    # 4. Scatter-gather query
    # --------------------------------------------------

    print("\n3. Getting all orders across shards")

    all_orders = database.get_all_orders()

    for order in all_orders:
        print(order)

    print(f"Total orders: {len(all_orders)}")

    # --------------------------------------------------
    # 5. Aggregate data across shards
    # --------------------------------------------------

    print("\n4. Calculating total sales")

    total_sales = database.get_total_sales()

    print(f"\nTotal sales across all shards: ₹{total_sales:.2f}")

    # --------------------------------------------------
    # 6. Global sorting
    # --------------------------------------------------

    print("\n5. Top five highest-value orders")

    top_orders = database.get_top_orders(limit=5)

    for order in top_orders:
        print(
            f"Order {order['order_id']} | "
            f"Product: {order['product']} | "
            f"Amount: ₹{order['amount']}"
        )

    # --------------------------------------------------
    # 7. Global pagination
    # --------------------------------------------------

    print("\n6. Paginated orders")

    result = database.get_paginated_orders(
        page=1,
        page_size=5,
    )

    print(f"Page: {result['page']}")
    print(f"Page size: {result['page_size']}")
    print(f"Total records: {result['total_records']}")
    print(f"Total pages: {result['total_pages']}")

    print("\nOrders on this page:")

    for order in result["orders"]:
        print(
            f"Order {order['order_id']} | "
            f"User {order['user_id']} | "
            f"₹{order['amount']}"
        )

    # --------------------------------------------------
    # 8. Second page
    # --------------------------------------------------

    print("\n7. Second page")

    result = database.get_paginated_orders(
        page=2,
        page_size=5,
    )

    for order in result["orders"]:
        print(
            f"Order {order['order_id']} | "
            f"User {order['user_id']} | "
            f"₹{order['amount']}"
        )

    # --------------------------------------------------
    # 9. Final summary
    # --------------------------------------------------

    print("\n" + "=" * 65)
    print("CROSS-SHARD QUERY DEMONSTRATION COMPLETED")
    print("=" * 65)


if __name__ == "__main__":
    main()
```
