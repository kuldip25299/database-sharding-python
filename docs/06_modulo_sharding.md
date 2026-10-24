# Modulo-Based Database Sharding

Modulo-based sharding is one of the simplest ways to distribute records across multiple database shards.

Instead of storing every record in a single database, the application calculates which shard should store each record using a shard key and the number of available shards.

This approach is easy to implement and provides predictable routing. However, changing the number of shards can cause many records to map to different destinations.

In this document, we will understand how modulo sharding works, implement its routing logic conceptually, and examine the trade-offs before building the Python example.

## 1. The Problem: Where Should a Record Be Stored?

Imagine an application with millions of users.

Initially, all user records are stored in one database:

```text
Application
     |
     v
Database
     |
     ├── User 101
     ├── User 102
     ├── User 103
     ├── User 104
     └── ...
```

As the application grows, the database may become a bottleneck because of increasing storage requirements, write traffic, query load, or resource contention.

We decide to split the records across four database shards:

```text
                    Application
                         |
                         v
                    Shard Router
                         |
             +-----------+-----------+
             |           |           |
             v           v           v
          Shard 0     Shard 1     Shard 2     Shard 3
```

The next question is straightforward:

**How does the application determine which shard owns a particular user record?**

Modulo-based sharding provides a simple answer.

## 2. Understanding the Modulo Operation

The modulo operator `%` returns the remainder after division.

For example:

```python
print(100 % 4)  # 0
print(101 % 4)  # 1
print(102 % 4)  # 2
print(103 % 4)  # 3
print(104 % 4)  # 0
```

When the divisor is four, the remainder is always one of these values:

```text
0, 1, 2, 3
```

We can use those values as shard indexes.

For a simplified integer-key example:

```python
shard_index = user_id % number_of_shards
```

If we have four shards and the user ID is `102`:

```python
shard_index = 102 % 4

print(shard_index)  # 2
```

The record is assigned to Shard 2.

This example uses the integer user ID directly. If the shard key is a string or another type, the application needs a stable hashing function to convert it into a suitable numeric value.

## 3. Routing Records Across Four Shards

Suppose we have four shards:

```text
Shard 0
Shard 1
Shard 2
Shard 3
```

We can calculate the destination for several user IDs.

| User ID | Calculation | Destination |
|---|---|---|
| 100 | 100 % 4 = 0 | Shard 0 |
| 101 | 101 % 4 = 1 | Shard 1 |
| 102 | 102 % 4 = 2 | Shard 2 |
| 103 | 103 % 4 = 3 | Shard 3 |
| 104 | 104 % 4 = 0 | Shard 0 |
| 105 | 105 % 4 = 1 | Shard 1 |
| 106 | 106 % 4 = 2 | Shard 2 |
| 107 | 107 % 4 = 3 | Shard 3 |

The routing calculation does not need to scan every shard. It computes the destination directly from the key.

That is one of the main benefits of hash-based sharding: the application can determine where a record belongs without checking every database.

## 4. Why the Shard Key Matters

The shard key is the value used to determine the destination shard.

For example, a user service might use:

```text
user_id
```

An order service might use:

```text
customer_id
```

A multi-tenant application might use:

```text
tenant_id
```

The choice affects more than distribution. It also affects how the application retrieves records.

Suppose an order is stored using `customer_id` as the shard key:

```text
customer_id = 5001
```

The application can calculate the destination shard when it needs to retrieve that customer's orders.

However, a query that searches for an order using only `order_id` may not know which shard contains the record unless the system has another way to locate it.

A good shard key should therefore consider:

- Whether its values distribute records reasonably evenly.
- Whether common queries contain the shard key.
- Whether the key remains stable over the record's lifetime.
- Whether a small number of keys could receive disproportionate traffic.

A simple routing formula cannot compensate for a poor shard key.

## 5. The Main Trade-Off: Changing the Number of Shards

Modulo sharding works well when the shard count is fixed.

The difficulty appears when the application needs additional capacity.

Suppose we initially have four shards:

```python
number_of_shards = 4
```

A record with user ID `105` maps to:

```python
105 % 4  # 1
```

It belongs to Shard 1.

Now we increase the shard count to five:

```python
number_of_shards = 5
```

The same record maps to:

```python
105 % 5  # 0
```

It now maps to Shard 0.

The routing calculation has changed even though the user ID has not changed.

This creates an important operational problem: the existing record is still stored on Shard 1, but the new routing formula directs the application to Shard 0.

If the application immediately switches to the new formula without migrating records or maintaining a compatible routing mechanism, it may fail to find existing data.

### How Much Data Moves?

When changing from \(N\) shards to \(M\) shards, ordinary modulo routing uses a different divisor.

For many key distributions, a substantial portion of keys will receive different assignments. The exact number depends on the old and new shard counts and the keys involved.

For example, compare assignments under four and five shards:

| User ID | With 4 shards | With 5 shards | Assignment changed? |
|---|---|---|---|
| 100 | Shard 0 | Shard 0 | No |
| 101 | Shard 1 | Shard 1 | No |
| 102 | Shard 2 | Shard 2 | No |
| 103 | Shard 3 | Shard 3 | No |
| 104 | Shard 0 | Shard 4 | Yes |
| 105 | Shard 1 | Shard 0 | Yes |
| 106 | Shard 2 | Shard 1 | Yes |
| 107 | Shard 3 | Shard 2 | Yes |
| 108 | Shard 0 | Shard 3 | Yes |
| 109 | Shard 1 | Shard 4 | Yes |

This example illustrates a general limitation: adding a shard does not simply assign new records to the new shard. Existing records can also receive different destinations.

In a real system, the application must coordinate data migration and routing changes carefully.

## 6. Distribution Is Not the Same as Balanced Traffic

Modulo routing can distribute keys across shards, but it does not guarantee equal storage or traffic.

Consider two situations.

### Situation A: Evenly Distributed Records

```text
Shard 0: 25,000 records
Shard 1: 25,000 records
Shard 2: 25,000 records
Shard 3: 25,000 records
```

This looks balanced by record count.

### Situation B: Uneven Request Traffic

```text
Shard 0: 20% of requests
Shard 1: 15% of requests
Shard 2: 60% of requests
Shard 3:  5% of requests
```

Even if record counts are similar, Shard 2 may become a bottleneck because it receives most of the requests.

This can happen when some records are accessed much more frequently than others.

It is important to evaluate both:

- **Data distribution:** how much data each shard stores.
- **Request distribution:** how much traffic each shard processes.

If one key receives unusually high traffic, adding more shards alone may not solve the hotspot.

## 7. A Note About Hash Functions

For integer IDs, a simple example can use the ID directly:

```python
shard_index = user_id % number_of_shards
```

For string keys, the application needs a hash function:

```python
shard_index = stable_hash(user_id) % number_of_shards
```

The hash function must produce consistent results across application instances and restarts.

Avoid using Python's built-in `hash()` for persistent string-key routing. Python may randomize string hash values between processes, which can cause different application instances to calculate different shard assignments.

A production implementation should define the hash algorithm, key encoding, and routing configuration consistently across all clients.

Even with a stable hash function, changing the shard count still changes modulo assignments.

## 8. When Is Modulo Sharding a Good Choice?

Modulo sharding can be a reasonable choice when:

- The shard count is expected to remain relatively stable.
- The shard key has suitable distribution characteristics.
- Queries can route directly using the shard key.
- The team values simple and predictable routing.
- The system has a planned process for future resharding.

It becomes less attractive when shards are added and removed frequently and moving large amounts of existing data is expensive.

In those cases, consistent hashing is worth considering because it generally reduces the number of keys that need reassignment when shard membership changes.

It still requires a safe migration process.

## 9. What We Will Implement in Python

In the next example, we will create a small in-memory simulation of modulo-based sharding.

The implementation will demonstrate:

1. Creating multiple shards.
2. Calculating a destination from a shard key.
3. Storing records in the selected shard.
4. Retrieving records using the same routing logic.
5. Inspecting how records are distributed.
6. Comparing assignments when the shard count changes.

Each shard will be represented by a Python dictionary. This lets us study the routing algorithm without setting up a database server.

The simulation is for learning purposes. It will not implement production data migration, replication, failover, or distributed transactions.

## 10. Key Takeaways

- Modulo-based sharding maps a key to a shard using a remainder calculation.
- It provides simple, direct routing when all application instances use the same key and shard configuration.
- The shard key affects data distribution and query efficiency.
- Changing the shard count can remap many existing keys.
- A routing change must be coordinated with data migration to avoid losing access to existing records.
- Even distribution of keys does not guarantee even request traffic.
- Stable hashing is essential when the same key must map consistently across processes.

Modulo sharding is a useful starting point for understanding database partitioning. Its simplicity makes it easy to implement, but its resharding behavior is an important limitation to understand before using it in a growing system.

## Next Step

Next, we will implement the routing logic in Python and observe how records are assigned to shards.

Next file: `examples/03_modulo_sharding.py`
