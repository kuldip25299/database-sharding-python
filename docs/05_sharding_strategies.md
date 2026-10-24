# Database Sharding Strategies

A database can be divided into smaller partitions in several ways. The strategy determines how records are assigned to shards, how queries locate data, and how difficult it is to add or remove database servers.

Choosing a sharding strategy is not just a hashing decision. It is a trade-off between query patterns, data distribution, operational complexity, and future growth.

In this document, we will compare three common approaches:

1. Range-based sharding
2. Modulo-based sharding
3. Consistent hashing

We will discuss all three conceptually, then implement modulo-based sharding and consistent hashing in Python in this repository.

## 1. Range-Based Sharding

Range-based sharding assigns records to shards according to ranges of a shard key.

For example, consider an application that stores customer records and uses `user_id` as the shard key.

| Shard | User ID range |
|---|---|
| Shard 1 | 1–1,000 |
| Shard 2 | 1,001–2,000 |
| Shard 3 | 2,001–3,000 |
| Shard 4 | 3,001–4,000 |

A record with `user_id = 1,500` belongs to Shard 2. A record with `user_id = 3,200` belongs to Shard 4.

The application or query router determines the appropriate shard by checking the key's range.

### Advantages

- Range queries can be efficient because related key values are stored together.
- The partitioning rules are straightforward to understand.
- Data can be distributed according to known ranges and access patterns.
- Specific ranges can be moved between shards when the partitioning scheme supports it.

### Disadvantages

- Sequential or time-based keys can create hot shards.
- Some ranges may contain significantly more records than others.
- A busy range can become a bottleneck even when other shards have spare capacity.
- Splitting ranges and moving existing records requires careful operational planning.

### Example: Time-Based Data

Suppose an application partitions orders by creation date:

- Shard 1: January orders
- Shard 2: February orders
- Shard 3: March orders

This can make monthly queries easier to target. However, if most writes are for the current month, the newest shard may receive most of the write traffic.

Range-based sharding is useful when range queries are important and the distribution of keys can be managed carefully.

## 2. Modulo-Based Sharding

Modulo-based sharding uses a hash of the shard key and the number of available shards to select a destination.

The basic formula is:

```python
shard_index = hash(shard_key) % number_of_shards
```

For example, with four shards:

```python
number_of_shards = 4

user_id = 101
shard_index = user_id % number_of_shards

print(shard_index)  # 1
```

In this simplified example, the user ID itself is used as the value being divided. The remainder identifies the shard index.

A real implementation may hash a string or another key type before calculating the remainder.

### How It Works

Suppose we have four shards:

```text
Shard 0
Shard 1
Shard 2
Shard 3
```

Using the key directly for illustration:

| User ID | Calculation | Shard |
|---|---|---|
| 100 | 100 % 4 = 0 | Shard 0 |
| 101 | 101 % 4 = 1 | Shard 1 |
| 102 | 102 % 4 = 2 | Shard 2 |
| 103 | 103 % 4 = 3 | Shard 3 |
| 104 | 104 % 4 = 0 | Shard 0 |
| 105 | 105 % 4 = 1 | Shard 1 |

Records are distributed across shards according to the remainder.

### Advantages

- The routing formula is simple.
- Routing is fast and deterministic when the same stable key and shard count are used.
- It is easy to implement and demonstrate.
- It can distribute records reasonably well when keys and workloads are suitable.

### Disadvantages

- Changing the shard count can change the destination for many existing keys.
- A poor shard key or uneven request distribution can still create hotspots.
- The routing logic depends on the shard count remaining consistent across application instances.
- Adding a shard can require substantial data movement.

### The Resharding Problem

Consider four shards and a user whose ID is `101`.

With four shards:

```text
101 % 4 = 1
```

The user maps to Shard 1.

Now suppose we increase the shard count to five:

```text
101 % 5 = 1
```

This particular key stays on Shard 1. But consider user ID `103`:

```text
103 % 4 = 3
103 % 5 = 3
```

That key also stays on Shard 3. Not every key moves when the shard count changes, but many keys will map to different destinations.

For example, user ID `100` moves:

```text
100 % 4 = 0
100 % 5 = 0
```

This key happens to stay on Shard 0 as well. To see a key that moves, consider user ID `102`:

```text
102 % 4 = 2
102 % 5 = 2
```

This key also stays. These examples illustrate that a few individual keys can remain in place; the important point is that modulo routing does not preserve existing assignments in general.

With a sufficiently large set of keys, changing the divisor from four to five typically remaps a substantial fraction of them. The application must account for where existing records actually live, not simply start routing all requests using the new formula.

**Important implementation detail:** Python's built-in `hash()` is randomized for certain types, including strings, between interpreter processes by default. Do not use it directly for persistent shard assignments that must remain stable across application restarts or servers. Use a stable hash function or a carefully defined integer-key scheme instead.

Modulo-based sharding is a good starting point because it is easy to understand and implement. Its main limitation is the cost of changing the shard count.

## 3. Consistent Hashing

Consistent hashing is designed to reduce how many keys need to be reassigned when the number of shards changes.

Instead of dividing keys by the current number of shards, consistent hashing maps both keys and shards onto a logical hash ring.

Each key and each shard receives a position on the ring. A key is assigned to the first shard encountered when moving clockwise from the key's position.

### How It Works

Imagine a circular hash space:

```text
                    Shard A
                       |
              .----------------.
           .-'                  '-.
         .'                        '.
        /                            \
       |                              |
       |          Hash ring           |
       |                              |
        \                            /
         '.                        .'
           '-.                  .-'
              '----------------'
                  |          |
               Shard C    Shard B
```

The diagram is conceptual. Actual positions are determined by hash values.

To route a key:

1. Hash the key to obtain a position on the ring.
2. Find the next shard position clockwise.
3. Route the key to that shard.
4. If the ring wraps around, continue from the beginning.

### What Happens When a Shard Is Added?

Suppose a new shard is introduced into the ring.

With consistent hashing, the new shard takes responsibility for the keys in the ring interval immediately preceding its position, up to the previous shard's position.

Most keys assigned to other intervals can keep their existing assignments.

This generally means fewer keys need to move than with ordinary modulo hashing when the shard count changes.

However, consistent hashing does **not** eliminate data migration. Records assigned to the new shard still need to be copied or moved, and the routing system must handle the transition safely.

### Virtual Nodes

A basic ring with one position per physical shard may produce an uneven distribution.

Virtual nodes improve this by assigning multiple positions on the ring to each physical shard.

For example:

```text
Physical Shard A
    ├── Virtual Node A1
    ├── Virtual Node A2
    ├── Virtual Node A3
    └── Virtual Node A4

Physical Shard B
    ├── Virtual Node B1
    ├── Virtual Node B2
    ├── Virtual Node B3
    └── Virtual Node B4
```

Each virtual node has its own position on the ring. Keys map to virtual nodes, which then map to their physical shard.

Virtual nodes generally improve distribution and make the system less sensitive to the placement of a single shard position.

They do not guarantee perfectly equal data sizes or request rates. Hot keys, uneven workloads, and shard capacity differences still need to be considered.

### Advantages

- Adding or removing a shard generally remaps fewer keys than ordinary modulo hashing.
- Virtual nodes can improve distribution across physical shards.
- The approach is useful for systems where the shard pool changes over time.
- It separates key placement from a simple division by the current shard count.

### Disadvantages

- Routing logic is more complex than modulo-based sharding.
- The ring and virtual-node assignments must remain consistent across application instances.
- Adding or removing shards still requires a migration strategy.
- Even distribution is not guaranteed, especially for skewed workloads or hot keys.

Consistent hashing is useful when reducing reassignment during topology changes is important enough to justify additional complexity.

## 4. Comparing the Strategies

| Consideration | Range-Based | Modulo-Based | Consistent Hashing |
|---|---|---|---|
| Assignment | Key ranges | Hash modulo shard count | Key position on a hash ring |
| Implementation complexity | Low to moderate | Low | Moderate |
| Range-query suitability | Often good | Usually requires multiple shards for ranges | Usually requires multiple shards for ranges |
| Distribution | Depends on range sizes and workload | Depends on keys and workload | Depends on ring placement, virtual nodes, and workload |
| Adding a shard | May require splitting ranges and moving data | Can remap many keys | Generally remaps a smaller portion of keys |
| Hotspot risk | High for skewed ranges | High for hot keys or uneven requests | High for hot keys or uneven requests |
| Best fit | Workloads that benefit from key ranges | Fixed or relatively stable shard counts | Systems that need more flexible shard membership |

No strategy solves every scaling problem. The right choice depends on how the application accesses data and how frequently the shard topology changes.

## 5. How to Choose a Strategy

Before selecting a strategy, answer these questions:

### Question 1: Which queries dominate the workload?

If most queries retrieve records by a range of values, range-based sharding may simplify routing for those queries.

If most queries retrieve one customer, account, or order by a stable identifier, hash-based sharding may be a better fit.

### Question 2: How predictable is the data distribution?

A strategy that evenly distributes keys may still perform poorly if a small number of keys generate most of the traffic.

Consider both:

- Data distribution: how much data each shard stores.
- Request distribution: how much traffic each shard receives.

They are related, but they are not the same.

### Question 3: How often will the shard count change?

If the shard count is relatively stable, modulo-based sharding may provide sufficient simplicity.

If shards will be added or removed regularly, consistent hashing can reduce the number of keys whose assignments change.

### Question 4: What is the cost of moving data?

Reducing remapping is useful, but the application must still preserve correct reads and writes during migration.

Consider how the system will locate existing records, copy data, handle concurrent updates, and switch routing without losing or duplicating data.

## 6. What We Will Implement in This Repository

This repository keeps the implementation focused on two hash-based strategies.

### Modulo-Based Sharding

We will implement:

- A fixed collection of in-memory shards.
- Deterministic routing based on a shard key.
- Record insertion and retrieval.
- A demonstration of how changing the shard count changes key assignments.
- A simple way to inspect the distribution of records.

### Consistent Hashing

We will implement:

- A hash ring.
- Shard placement on the ring.
- Key routing to the next shard clockwise.
- Virtual nodes to improve distribution.
- A comparison of key assignments before and after adding a shard.

The examples use in-memory Python dictionaries rather than a real database. This keeps the focus on routing and distribution without requiring database setup or infrastructure.

Range-based sharding is covered conceptually, but it will not have a separate implementation in this repository.

## 7. Key Takeaways

- Range-based sharding groups records by key ranges and can benefit range queries, but uneven ranges can create hotspots.
- Modulo-based sharding is simple and fast, but changing the shard count can remap many keys.
- Consistent hashing reduces the number of keys that typically need reassignment when shards change, but it does not eliminate data migration.
- Virtual nodes can improve distribution, but they cannot fix every workload imbalance.
- Shard key selection and request patterns matter as much as the routing algorithm.
- Every strategy introduces operational responsibilities around routing, data movement, and correctness.

Sharding is not just about distributing records across multiple servers. It is about deciding where data belongs, how requests find it, and how the system continues to behave correctly as it grows.

## Next Step

In the next document, we will focus on **modulo-based sharding** and build the concept step by step before implementing it in Python.

Next file: `docs/06_modulo_sharding.md`
