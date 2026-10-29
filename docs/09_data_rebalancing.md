# Data Rebalancing in a Sharded Database

Database sharding distributes records across multiple shards, but the distribution does not always remain balanced as an application grows.

Some shards may accumulate more records than others. Some may receive more requests. New shards may need to be added to increase capacity, or existing shards may need to be removed.

**Data rebalancing is the process of changing data ownership across shards to improve distribution or accommodate changes in the shard topology.**

The challenge is not simply moving records. The application must continue to read and write the correct data while ownership changes.

This document explains why rebalancing is necessary, how different sharding strategies affect it, and what must be considered when implementing a safe migration.

## 1. Why Does Data Rebalancing Become Necessary?

Imagine an application that initially distributes customer records across four shards.

```text
Shard 0: 25,000 records
Shard 1: 25,000 records
Shard 2: 25,000 records
Shard 3: 25,000 records
```

The distribution appears balanced.

As the application grows, the distribution changes:

```text
Shard 0: 30,000 records
Shard 1: 28,000 records
Shard 2: 95,000 records
Shard 3: 32,000 records
```

Shard 2 now stores significantly more records than the others.

This can happen because of uneven key distribution, changes in workload, tenant growth, or how records are assigned to shards.

The system may need to move some records from Shard 2 to other shards.

However, record count alone does not tell the whole story. A shard with fewer records can still become a bottleneck if its records receive more requests or require more expensive queries.

A useful rebalancing decision should consider both storage and workload.

## 2. Common Reasons for Rebalancing

### 2.1 Adding a New Shard

The application may need more storage or processing capacity.

For example:

```text
Before:

Shard 0
Shard 1
Shard 2
Shard 3

After:

Shard 0
Shard 1
Shard 2
Shard 3
Shard 4
```

Adding a shard changes the available destinations. Depending on the routing strategy, existing keys may receive new assignments.

The system must decide which records should move and how to update routing safely.

### 2.2 Removing a Shard

A shard may need to be removed because of infrastructure changes, capacity consolidation, or replacement.

Its records must be transferred or otherwise made accessible before the shard can be retired safely.

### 2.3 Uneven Data Distribution

Some shards may store much more data than others.

If one shard approaches its storage or resource limits while others have spare capacity, moving part of its data may help restore balance.

### 2.4 Uneven Request Distribution

A shard may receive a disproportionate amount of traffic even when the number of records is balanced.

For example:

```text
Shard 0: 20% of requests
Shard 1: 15% of requests
Shard 2: 60% of requests
Shard 3:  5% of requests
```

Moving data can help if the workload can be redistributed, but it will not necessarily solve a hot-key problem. If most requests target a single key, moving that key to another shard may simply move the bottleneck.

The solution depends on the workload and the application's access patterns.

## 3. How the Sharding Strategy Affects Rebalancing

The routing algorithm influences how much data may need to move when shard membership changes.

### Modulo-Based Sharding

Modulo sharding commonly uses a calculation such as:

```python
shard_index = stable_hash(shard_key) % number_of_shards
```

Suppose a system changes from four shards to five.

The divisor changes, so many existing keys may map to different shard indexes. Some keys keep their assignments, but the system cannot assume that the existing data distribution still matches the new routing formula.

A migration plan must account for records that remain on their old shards while the new formula points elsewhere.

Modulo sharding is easy to understand and implement, but changing the shard count can create substantial redistribution work.

### Consistent Hashing

Consistent hashing maps keys and shards onto a shared hash ring.

When a shard is added, it generally takes ownership of a portion of the ring. Keys in that interval are reassigned, while keys in other intervals can retain their assignments.

This usually reduces the number of keys that need reassignment compared with ordinary modulo hashing.

However, consistent hashing does not eliminate migration. Records whose ownership changes still need to be transferred or made available through a safe routing mechanism.

### Range-Based Sharding

Range-based sharding assigns records according to ranges of key values.

Rebalancing may involve splitting a range, moving part of a range to another shard, or adjusting range boundaries.

This can be useful when range-based queries matter, but sequential keys or uneven ranges may create hotspots.

The important point is that no routing strategy removes the need to plan for data movement.

## 4. Rebalancing Is More Than Changing a Routing Formula

Consider a record currently stored on Shard 1.

The application changes its routing configuration, and the record now maps to Shard 3.

If the record has not been copied or moved, a read routed to Shard 3 may not find it.

```text
Before routing change:

Request
   |
   v
Shard 1  ---> Record exists


After routing change, before migration:

Request
   |
   v
Shard 3  ---> Record not found
              
Shard 1  ---> Record still exists
```

The routing calculation may be correct according to the new configuration, but the data has not caught up.

This is why **changing the routing algorithm and migrating existing records are separate operations that must be coordinated**.

A safe rebalancing process needs to define:

- Which shard currently owns each record.
- Which shard will own it after migration.
- How reads behave while the record is moving.
- How concurrent writes are handled.
- When routing changes become authoritative.
- When the old copy can be removed safely.

## 5. A Simplified Rebalancing Workflow

A production migration can be complex, but the core workflow can be understood through a series of steps.

### Step 1: Identify the Imbalance

Measure data size, request rates, latency, and resource utilization across the shards.

Determine whether the issue is storage imbalance, request imbalance, or a specific hot key.

### Step 2: Calculate the New Ownership

Determine which keys or key ranges should move to which destination shards.

The calculation depends on the selected sharding strategy and the desired distribution.

### Step 3: Copy the Required Data

Copy the affected records to their destination shards.

For a live system, the migration process must account for records being updated while the copy is in progress.

### Step 4: Keep Changes Consistent

If a record changes after the initial copy, the destination must receive the appropriate update before it becomes authoritative.

Possible techniques include change-data capture, write forwarding, temporary dual writes, or a carefully coordinated write pause. Each technique has different consistency and operational trade-offs.

### Step 5: Update Routing

Once the destination has the required data and the migration protocol's conditions are satisfied, update the routing configuration or ownership metadata.

The system must avoid incompatible routing decisions across application instances.

### Step 6: Verify and Clean Up

Verify that the destination has the expected records and that reads and writes behave correctly.

Remove old copies only when the migration process guarantees that they are no longer required for correctness or recovery.

This workflow is conceptual. A production implementation must define failure recovery, retries, idempotency, concurrency handling, and consistency guarantees for every stage.

## 6. Online and Offline Rebalancing

Rebalancing can be performed in different ways depending on how much downtime the application can tolerate.

### Offline Rebalancing

The application temporarily stops relevant writes or takes the affected data out of service while records are moved.

Advantages:

- Easier to reason about because the data may not be changing during migration.
- Fewer concurrent-write scenarios to manage.
- Can be appropriate for small systems or maintenance windows.

Disadvantages:

- May require downtime or reduced availability.
- The migration duration depends on the volume of data.
- Not suitable for every application.

### Online Rebalancing

The application continues serving requests while data is copied and ownership changes.

Advantages:

- Can reduce user-visible downtime.
- Better suited to systems that must remain available during maintenance.
- Allows migration to be performed incrementally.

Disadvantages:

- Concurrent reads and writes make migration more complex.
- Routing changes require careful coordination.
- The system must handle retries, partial failures, and temporary duplicate copies.
- Migration traffic can compete with normal application traffic for resources.

Online migration is not automatically safer or more available. Its correctness depends on the migration protocol and how the application handles concurrent operations.

## 7. The Cost of Rebalancing

Moving records consumes resources that the application also needs for normal operations.

The cost can include:

- Network bandwidth for transferring records.
- CPU and memory used to read, serialize, and write data.
- Disk I/O on source and destination shards.
- Additional latency for queries competing with migration work.
- Temporary storage for duplicate copies.
- Engineering effort to handle failure and recovery.

For example, moving a large dataset while normal traffic is high may overload both the source and destination shards.

A practical migration strategy may therefore move records in batches, limit migration throughput, and monitor shard health throughout the operation.

The goal is not merely to finish the migration quickly. It is to complete it without compromising normal application behavior.

## 8. Why Consistent Hashing Helps but Does Not Solve Everything

Consistent hashing reduces the number of keys whose assignments typically change when shard membership changes.

This can reduce the amount of data that needs to move.

However, the following problems remain:

- Records must still be copied or transferred to their new owners.
- Concurrent updates must be handled correctly.
- Application instances must agree on the routing configuration.
- A shard may still receive disproportionate traffic.
- The migration may fail partway through and require recovery.

Consistent hashing improves the reassignment behavior of the routing algorithm. It is not a complete data migration system.

This distinction matters when evaluating sharding approaches for production applications.

## 9. How We Will Demonstrate Rebalancing in This Repository

This repository uses in-memory Python dictionaries to represent shards.

The upcoming example, `examples/07_data_rebalancing.py`, will demonstrate the basic idea without requiring a real database.

The example will focus on:

1. Creating a collection of in-memory shards.
2. Distributing sample records using a defined routing strategy.
3. Comparing record assignments before and after a topology change.
4. Showing which records would need to move.
5. Verifying the resulting distribution.

The example will help illustrate the difference between calculating a new destination and physically moving a record.

It will not implement production online migration, concurrent-write coordination, replication, or distributed transactions.

Those concerns require additional mechanisms beyond a simple in-memory demonstration.

## 10. Practical Guidelines

Before implementing rebalancing in a production system, consider these guidelines.

- **Measure before moving data.** Determine whether the bottleneck comes from storage, request volume, or a hot key.
- **Plan for routing consistency.** Application instances must agree on ownership during and after migration.
- **Account for concurrent writes.** Copying a record once is insufficient if it can change before ownership switches.
- **Control migration load.** Data movement should not overwhelm normal traffic.
- **Make recovery explicit.** Decide how to resume or roll back an interrupted migration.
- **Verify before deleting old data.** A partially completed migration must not cause records to become inaccessible.
- **Treat topology changes as operational events.** Monitor progress, shard health, and application errors during the transition.

## 11. Key Takeaways

- Data rebalancing redistributes ownership to accommodate growth or correct imbalances.
- Adding or removing shards can change record assignments.
- Modulo sharding may require reassignment of many keys when the shard count changes.
- Consistent hashing typically reduces the number of keys that need reassignment.
- Changing routing configuration does not move data automatically.
- Online migration must handle concurrent updates and partial failures.
- Rebalancing consumes resources and can affect application latency.
- Data distribution and request distribution should both be measured.

A sharded system must be designed not only for its current topology, but also for how it will evolve.

The routing strategy determines which records should belong to which shards. The rebalancing process ensures that the actual data catches up with those ownership decisions without compromising correctness.

## Next Step

Next, we will examine cross-shard queries and transactions, including why operations spanning multiple shards require additional coordination.

Next file: `docs/10_cross_shard_queries_and_transactions.md`
