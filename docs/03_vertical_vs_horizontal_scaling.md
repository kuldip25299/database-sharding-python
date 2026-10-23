# Vertical Scaling vs. Horizontal Scaling

## 1. The Scaling Problem

As an application grows, its database must handle more requests, store more records, and process more concurrent transactions.

Suppose an e-commerce application starts with 10,000 users and grows to 5 million users. Its database workload may increase significantly as users browse products, place orders, and check transaction history.

The database may eventually run into limits involving:

- CPU utilization and query execution time.
- Memory pressure and database caching.
- Storage capacity and disk I/O.
- Concurrent writes, locks, and transaction processing.
- Connection limits and workload contention.

When this happens, we need to decide how to increase database capacity.

There are two broad approaches:

1. **Vertical scaling:** Give the existing database server more resources.
2. **Horizontal scaling:** Distribute the workload or data across multiple machines.

Both approaches have a place in system design. The right choice depends on the workload, the database technology, the budget, and the complexity the team is willing to operate.

## 2. What Is Vertical Scaling?

Vertical scaling, also called scaling up, means increasing the resources available to an existing database server.

For example, a database might move from a machine with 4 CPU cores and 16 GB of RAM to one with 16 CPU cores and 64 GB of RAM.

The database still operates as one logical database instance. Its tables, queries, and application connection model do not necessarily need to change.

### Architecture

```text
          Application
               |
               v
       +----------------+
       |    Database    |
       |                |
       | More CPU       |
       | More RAM       |
       | Faster Storage |
       +----------------+
```

The application continues connecting to the same database endpoint.

### Example

Imagine an application whose database has started experiencing high query latency because its working set no longer fits comfortably in memory.

Moving to a server with more RAM may improve caching and reduce disk reads.

Similarly, faster storage may help a workload limited by disk I/O, while additional CPU capacity may help queries that are genuinely CPU-bound.

The important point is that the new resources must address the actual bottleneck.

Adding CPU cores will not necessarily solve a query dominated by disk latency, poor indexing, or lock contention.

### Advantages

- Relatively straightforward to implement.
- Minimal application-level architectural changes.
- Existing transactions and joins can remain within the same database.
- Simpler operational management than a multi-shard system.
- Often the best first step when the database is under-provisioned.

### Limitations

- Larger database instances generally cost more.
- Available machine sizes and hardware resources have practical limits.
- A single database instance can remain a capacity or availability bottleneck.
- Upgrading hardware may require downtime or a migration, depending on the database and deployment.
- More hardware does not fix inefficient queries or poor data access patterns.

Vertical scaling is not a bad architecture. For many applications, it remains the simplest and most cost-effective choice.

## 3. What Is Horizontal Scaling?

Horizontal scaling, also called scaling out, means adding more machines and distributing work among them.

At the database layer, the details matter: adding read replicas distributes read traffic, while sharding distributes different portions of the dataset across database instances.

These approaches are not interchangeable.

### Horizontal scaling with read replicas

A primary database handles writes, while replicas can serve eligible reads.

```text
                  Application
                       |
                +------+------+
                |             |
              Writes         Reads
                |             |
                v             v
             Primary       Replicas
             Database     /        \
                         Replica 1  Replica 2
```

This can reduce read pressure on the primary, but it does not automatically distribute write ownership or divide the complete dataset into independent partitions.

Replicas may also lag behind the primary, so the application must account for consistency requirements.

### Horizontal scaling with sharding

Sharding distributes different subsets of the data across multiple database instances.

```text
                   Application
                        |
                   Shard Router
                  /      |      \
                 v       v       v
              Shard A  Shard B  Shard C
              Users    Users    Users
              1, 4, 7  2, 5, 8  3, 6, 9
```

The example shows a possible assignment of user records. The actual distribution depends on the shard key and routing strategy.

A request for a particular user can be routed to the shard that owns that user's record.

When the data and workload are distributed appropriately, each shard handles only a portion of the overall database workload.

### Advantages

- Can distribute storage across multiple machines.
- Can distribute writes when the workload is partitioned effectively.
- Can provide more aggregate database capacity.
- Allows capacity to grow by adding database instances, subject to the architecture.
- Can isolate workloads or tenants when the partitioning strategy supports it.

### Limitations

- Requires a strategy for assigning records to shards.
- Adds routing and data placement complexity.
- Can create hotspots if the shard key or traffic distribution is poor.
- Makes cross-shard joins, transactions, and global constraints more difficult.
- Requires a plan for data migration and rebalancing.
- Adds operational work across multiple database instances.

Horizontal scaling can address limits that vertical scaling cannot, but it introduces coordination problems that do not exist in the same form in a single-database architecture.

## 4. Vertical Scaling vs. Horizontal Scaling

| Consideration | Vertical scaling | Horizontal scaling with sharding |
|---|---|---|
| Basic approach | Increase resources on a database server | Distribute data across database instances |
| Data layout | Dataset remains in one database instance | Dataset is divided across shards |
| Application changes | Often limited | Usually requires routing and shard-aware access |
| Joins | Can remain within one database | Cross-shard joins may require coordination |
| Transactions | Managed by the database instance | Cross-shard transactions may require distributed coordination |
| Storage capacity | Limited by the chosen server and database configuration | Can grow across multiple instances |
| Write capacity | Still depends on the capacity of the database instance | Can increase when writes are distributed effectively |
| Operational complexity | Generally lower | Generally higher |
| Scaling cost | Larger instances can become expensive | More instances add infrastructure and operational costs |
| Rebalancing | Usually not a shard-placement problem | May require moving records between shards |

This comparison focuses on sharding rather than every form of horizontal scaling. Read replicas are another horizontal scaling technique, but they solve a different problem.

## 5. Why Adding More Application Servers Is Not Enough

Consider an application that runs on three application servers.

```text
                Load Balancer
                 /    |    \
                v     v     v
              App 1 App 2 App 3
                 \    |    /
                  \   |   /
                   Database
```

The application tier is distributed, but all servers still access the same database.

If the database is already saturated, adding application servers can increase concurrency without increasing the database's ability to process requests.

This can make the bottleneck worse.

The first step is to establish where the limit exists. It might be the application, the database, a particular query, a connection pool, or an external dependency.

Scaling the wrong component adds cost without solving the underlying problem.

## 6. When Should We Choose Vertical Scaling?

Vertical scaling is often the better choice when:

- The database is not close to its practical capacity limits.
- The workload benefits from a larger memory cache or faster storage.
- Most operations require joins or transactions across related tables.
- The application needs simple operational management.
- A database upgrade is less expensive than operating a sharded architecture.
- The existing database technology supports a straightforward scaling path.

For example, an order-management application may rely heavily on transactions that update orders, payments, inventory, and account balances together.

Keeping those operations within one database can make correctness easier to reason about.

If a larger database instance meets the workload requirements at an acceptable cost, sharding may introduce complexity without providing enough benefit.

## 7. When Should We Consider Sharding?

Sharding becomes worth evaluating when the workload cannot be handled economically or practically by one database instance, even after reasonable optimization.

Typical situations include:

### 7.1 Storage growth

The dataset is too large for the available database configuration, or storage and maintenance costs have become difficult to manage.

### 7.2 Write throughput limits

The database's write workload remains the bottleneck, and adding read replicas does not solve it.

If writes can be partitioned across independent shards, the workload may be distributed.

### 7.3 Workload isolation

Different groups of users or tenants generate enough load that assigning them to separate shards helps isolate resource usage.

This only works if the distribution avoids concentrating too much load on a few shards.

### 7.4 Capacity growth beyond one instance

The application needs additional aggregate storage or processing capacity that cannot be provided by a suitable single database instance.

Before committing to sharding, the team should estimate the cost of routing, migration, monitoring, backups, and recovery across multiple instances.

## 8. A Practical Decision Process

Use the following sequence when a database starts struggling.

```text
Database performance problem
             |
             v
Measure the actual bottleneck
             |
             v
Optimize queries, indexes,
connections, and transactions
             |
             v
Is read traffic the main problem?
          /       \
        Yes        No
         |          |
         v          v
Evaluate read   Evaluate CPU, memory,
replicas and    storage, write load,
caching         and contention
         |          |
         +----+-----+
              |
              v
Can vertical scaling meet
the requirements economically?
          /       \
        Yes        No
         |          |
         v          v
Scale up and    Evaluate sharding
re-measure      and other architectural
                options
```

This is a simplified decision process. Real systems may use several techniques together.

For example, an application might use caching, read replicas, and sharding at the same time. The architecture should follow the workload and the guarantees the application needs.

## 9. How We Will Demonstrate These Concepts in Python

Our repository uses in-memory Python dictionaries to demonstrate data placement and routing.

We will not simulate real hardware upgrades or claim that Python execution time predicts database performance.

Instead, we will model the structural difference between one data store and several shards.

### Example 1: Single database

All records are stored in one dictionary.

```python
users = {
    101: {"name": "Asha"},
    102: {"name": "Ravi"},
    103: {"name": "Neha"},
}
```

Every lookup uses the same data store.

### Example 2: Multiple shards

Records are assigned to separate dictionaries.

```python
shards = {
    "shard_1": {},
    "shard_2": {},
    "shard_3": {},
}
```

A routing function determines which dictionary owns a given key.

This does not prove that three shards will be faster than one. In-memory dictionaries do not reproduce database I/O, transaction processing, network latency, or lock contention.

The purpose is to make the partitioning and routing logic easy to understand before adding more complexity.

Later, we will compare modulo hashing and consistent hashing by measuring how many keys change their assigned shard when the shard count changes.

## 10. Key Takeaways

- Vertical scaling increases the resources available to a database instance.
- Horizontal scaling distributes work across multiple machines, but read replicas and sharding solve different problems.
- Adding application servers does not increase database capacity when the database remains the bottleneck.
- A larger database is often simpler than sharding and should not be dismissed prematurely.
- Sharding is useful when storage or workload requirements justify distributing data across database instances.
- Sharding introduces new challenges involving shard keys, query routing, data movement, and cross-shard operations.
- Measure the bottleneck and evaluate simpler solutions before committing to a distributed data architecture.

In the next document, we will examine **shard key selection** and why the choice of key can determine whether a sharded system distributes its workload evenly or creates hotspots.
