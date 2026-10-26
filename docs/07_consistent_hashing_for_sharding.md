# Consistent Hashing for Database Sharding

Consistent hashing is a sharding strategy designed to reduce how much data needs to be reassigned when database shards are added or removed.

In the previous document, we explored modulo-based sharding. It provides simple routing, but changing the number of shards can change the destination of many existing records.

Consistent hashing approaches this problem differently. Instead of dividing a key's hash by the current number of shards, it maps both keys and shards onto a shared hash ring.

This document explains how the ring works, how virtual nodes improve distribution, and what trade-offs remain when using consistent hashing.

## 1. The Problem with Modulo-Based Sharding

Suppose an application distributes customer records across four shards using:

```python
shard_index = user_id % number_of_shards
```

With four shards, a user with ID `105` maps to:

```python
105 % 4  # 1
```

The record belongs to Shard 1.

Now suppose the application adds a fifth shard:

```python
105 % 5  # 0
```

The same user now maps to Shard 0.

The existing record has not moved automatically. Only the routing calculation has changed.

In a real database, changing the routing formula without migrating the affected records or maintaining compatible routing metadata can make existing records inaccessible through the new route.

As the dataset grows, moving large amounts of data between shards can become an expensive operation.

**The goal of consistent hashing is to minimize unnecessary reassignment when the set of shards changes.**

## 2. What Is Consistent Hashing?

Consistent hashing maps two things into the same logical hash space:

- Data keys, such as customer IDs or order IDs.
- Shard identifiers, representing the available shards.

The hash space is treated as a circular structure called a *hash ring*.

For example, imagine a ring containing three shards:

```text
                    Shard A
                       |
                .--------------.
             .-'                '-.
           .'                      '.
          /                          \
         |                            |
         |          HASH RING         |
         |                            |
          \                          /
           '.                      .'
             '-.                .-'
                '--------------'
                  |          |
               Shard C    Shard B
```

This is a conceptual illustration. In an implementation, the ring consists of numeric hash positions rather than physical points on a circle.

Both keys and shards are assigned positions by a hash function. The position determines which shard owns a key.

## 3. How the Hash Ring Works

Consistent hashing uses the following routing process.

1. Hash the shard identifiers and place their positions on the ring.
2. Hash the data key to obtain its position.
3. Starting at the key's position, move clockwise around the ring.
4. Assign the key to the first shard position encountered.
5. If no shard exists later in the numeric range, wrap around to the first shard on the ring.

For example, imagine these positions on a simplified ring:

| Item | Hash position |
|---|---:|
| Shard A | 10 |
| Shard B | 40 |
| Shard C | 75 |
| Customer 101 | 25 |
| Customer 202 | 55 |
| Customer 303 | 90 |

Using clockwise routing:

| Customer | Key position | Next shard clockwise | Destination |
|---|---:|---|---|
| 101 | 25 | 40 | Shard B |
| 202 | 55 | 75 | Shard C |
| 303 | 90 | Wrap around to 10 | Shard A |

These positions are illustrative, not the output of a specific hash function.

The important detail is that a key's destination depends on the ordered shard positions around the ring, rather than a remainder calculated using the total number of shards.

## 4. What Happens When a Shard Is Added?

Suppose the ring initially contains Shards A, B, and C.

A new Shard D is added at a position between Shards A and B when moving clockwise.

Before the addition, keys in that interval belong to Shard B because it is the next shard clockwise.

After the addition, those keys belong to Shard D.

Keys in other intervals generally keep their existing assignments.

Conceptually:

```text
Before:

Key position ---------> Shard B

After adding Shard D:

Key position ---------> Shard D ---------> Shard B
```

Only the keys in the interval taken over by the new shard need to change owners as a result of that addition.

This is the central advantage of consistent hashing.

With ordinary modulo sharding, changing the divisor can remap a large fraction of keys. With consistent hashing, adding one shard typically affects only the portion of the ring assigned to that shard's new position.

The exact amount of data moved depends on the ring layout and key distribution.

**Important:** consistent hashing changes the assignment rule; it does not physically move records by itself. A database system still needs a migration process to copy records, handle concurrent writes, and safely update routing.

## 5. What Happens When a Shard Is Removed?

Now suppose Shard B is removed from the ring.

The keys previously assigned to Shard B are reassigned to the next available shard clockwise from their positions.

Other keys can retain their existing assignments.

This behavior is useful when a shard needs to be retired, replaced, or removed from the cluster.

However, removing a shard is not just a routing change. The system must ensure that records are safely transferred or remain accessible before the old shard is taken offline.

If a shard fails unexpectedly, the application also needs a recovery strategy. Consistent hashing alone does not provide replication, failover, or data durability.

## 6. The Distribution Problem with Basic Consistent Hashing

Consistent hashing reduces reassignment, but a basic ring can distribute data unevenly.

Imagine three physical shards, each assigned only one position on the ring:

```text
Shard A owns: 10% of the ring
Shard B owns: 65% of the ring
Shard C owns: 25% of the ring
```

If key hashes are reasonably uniform, the amount of data assigned to each shard will tend to reflect the size of its ring interval. In this example, Shard B may receive significantly more keys.

This can create uneven storage usage and request load.

The problem becomes more noticeable when the cluster contains only a small number of shards.

A solution is to assign each physical shard multiple positions on the ring.

These positions are called **virtual nodes**.

## 7. Virtual Nodes

A virtual node, often called a *vnode*, is a logical position on the hash ring that maps back to a physical shard.

Instead of giving each physical shard one position, we give each shard several positions.

For example:

```text
Physical Shard A
    ├── Virtual node A1
    ├── Virtual node A2
    ├── Virtual node A3
    └── Virtual node A4

Physical Shard B
    ├── Virtual node B1
    ├── Virtual node B2
    ├── Virtual node B3
    └── Virtual node B4

Physical Shard C
    ├── Virtual node C1
    ├── Virtual node C2
    ├── Virtual node C3
    └── Virtual node C4
```

Each virtual node receives its own hash position. When a key maps to a virtual node, the application routes it to the corresponding physical shard.

This spreads each physical shard's ownership across multiple intervals rather than one large interval.

### Why Virtual Nodes Help

Virtual nodes provide several benefits:

- They generally improve the distribution of keys across physical shards.
- They reduce dependence on a single shard position.
- They allow a shard's share of the ring to be adjusted by changing its number of virtual nodes.
- They can make rebalancing more flexible when shards have different capacities.

However, virtual nodes do not guarantee perfectly balanced data or traffic. The outcome still depends on the hash function, ring layout, key distribution, and workload.

Adding more virtual nodes also increases the amount of ring metadata the application must maintain.

For this repository, we will use a configurable number of virtual nodes per shard in the Python implementation.

## 8. Choosing the Shard Key Still Matters

Consistent hashing does not remove the need to choose a suitable shard key.

Consider a user service that routes records using `user_id`.

```text
user_id -> hash(user_id) -> ring position -> physical shard
```

This is useful when requests commonly retrieve a user by ID.

However, suppose a query asks for every user in a particular region:

```sql
SELECT *
FROM users
WHERE region = 'west';
```

If `region` is not the shard key, the query may need to search multiple shards.

Consistent hashing determines where a key belongs. It does not automatically make every query efficient.

When choosing a shard key, consider:

- Whether its values have sufficient variety.
- Whether common queries can route using that key.
- Whether records or requests are likely to be concentrated around a few keys.
- Whether the key remains stable throughout the record's lifetime.

A well-designed routing algorithm cannot compensate for every problem caused by a poor shard key.

## 9. Modulo Sharding vs. Consistent Hashing

| Consideration | Modulo Sharding | Consistent Hashing |
|---|---|---|
| Routing method | Hash modulo shard count | First shard clockwise from key position |
| Basic implementation | Simple | More involved |
| Adding a shard | Can remap many keys | Usually remaps keys in the affected ring interval |
| Removing a shard | Can remap many keys | Usually remaps keys previously owned by the removed shard |
| Distribution | Depends on keys and workload | Depends on ring positions, virtual nodes, and workload |
| Metadata | Shard count and hash configuration | Ring positions and their physical shard mappings |
| Migration required | Yes, when assignments change and records must move | Yes, when ownership changes and records must move |

Neither approach eliminates the need to monitor shard utilization, handle hot keys, or manage data movement.

Modulo sharding can be sufficient when the shard count is stable and simplicity is the priority. Consistent hashing becomes attractive when shards change more frequently and minimizing reassignment is important.

## 10. How We Will Implement It in Python

The upcoming example, `examples/05_consistent_hashing_sharding.py`, will simulate consistent hashing without requiring a real database.

The implementation will include:

1. A stable hash function for keys and virtual-node identifiers.
2. A hash ring represented by sorted numeric positions.
3. A mapping from virtual nodes to physical shards.
4. Routing a key to the first shard clockwise.
5. Adding a shard and comparing assignments before and after.
6. Using multiple virtual nodes to improve distribution.

Each physical shard will be represented using an in-memory Python dictionary.

The example will focus on **key placement and reassignment**, not production data migration, replication, failover, or distributed transactions.

To keep the results reproducible, the implementation will use a deterministic hash function rather than Python's built-in `hash()` for persistent routing decisions.

## 11. Production Considerations

Before using consistent hashing in a real database-backed application, consider the following.

### Consistent Ring Configuration

Every application instance responsible for routing must use a compatible view of the ring. Different ring configurations can send the same key to different shards.

### Safe Data Migration

When ownership changes, the system needs to transfer records safely. It must account for writes that happen during the migration and avoid losing updates or making records inaccessible.

### Replication and Failure Handling

Consistent hashing assigns keys to shards; it does not automatically create redundant copies. Replication and recovery need separate mechanisms.

### Hot Keys and Uneven Traffic

A key receiving an unusually large volume of requests can still overwhelm its destination shard. Virtual nodes improve distribution but do not eliminate hot-key problems.

### Monitoring and Rebalancing

The system should track data size, request rate, latency, and resource utilization per shard. Rebalancing should be based on observed workload, not only the number of keys.

## 12. Key Takeaways

- Consistent hashing maps keys and shards onto a shared logical ring.
- Each key is assigned to the first shard encountered clockwise from its hash position.
- Adding or removing a shard generally affects only part of the ring instead of changing assignments across the entire key space.
- Virtual nodes give each physical shard multiple positions and can improve distribution.
- Consistent hashing does not guarantee equal traffic or remove hot-key problems.
- It does not perform data migration, replication, or failover by itself.
- Shard key selection and query patterns remain important.
- The main benefit is reducing unnecessary key reassignment as shard membership changes.

Consistent hashing is not simply a more complicated hash function. It is a different way to organize ownership so that a changing set of shards can accommodate growth with less disruption.

## Next Step

Next, we will examine how an application determines the correct shard for each request and why routing logic should be separated from business logic.

Next file: `docs/08_query_routing.md`
