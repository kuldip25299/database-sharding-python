# The Business Problem: Why Database Sharding?

## 1. The Problem Starts with Growth

Imagine we are building a platform where users can create accounts, upload content, place orders, and access their data.

Initially, the application runs on a single database server. Every user record, order, and transaction is stored in the same database.

At first, this architecture is simple and works well.

- The application connects to one database.
- Reads and writes are easy to manage.
- Database transactions stay within one database.
- Backups and schema changes are relatively straightforward.

As the application grows, however, the database may become a bottleneck.

More users generate more requests. More transactions require more writes. The database needs additional memory, CPU, storage, and disk I/O to keep up.

The application might still have enough application servers to handle incoming traffic, but the database can become the limiting factor.

**The business problem is simple: how do we keep the application responsive as its data volume and workload grow beyond what one database server can handle economically or practically?**

## 2. What Happens When One Database Becomes a Bottleneck?

Consider a growing e-commerce platform.

The database stores users, products, orders, payments, and order history. During a major sale, thousands of customers browse products and place orders at the same time.

Several problems can appear:

### 2.1 Increased query latency

As the workload increases, queries may take longer because of CPU contention, disk I/O, memory pressure, inefficient query plans, or lock contention.

A query that was previously fast may become noticeably slower under peak load.

### 2.2 Write contention

Multiple requests may update the same tables or related records concurrently. Index maintenance, locking, and transaction processing can become increasingly expensive.

Adding more application servers does not automatically increase the write capacity of a single database.

### 2.3 Storage growth

The database keeps accumulating user records, orders, transaction history, and indexes.

Eventually, storage capacity, maintenance operations, backups, and recovery times may become harder to manage within the existing setup.

### 2.4 Vertical scaling becomes expensive

One option is to move the database to a machine with more CPU, memory, and faster storage.

This is called **vertical scaling**.

It is often the right first step. Better hardware, suitable indexes, query optimization, connection pooling, caching, and read replicas may solve the problem without sharding.

But vertical scaling has practical limits. Larger database instances can become expensive, and a workload may eventually exceed the capacity of the available machine sizes.

At that point, the team needs to evaluate other options.

## 3. Why Not Just Add More Application Servers?

Adding application servers helps distribute application-level work across multiple machines.

For example:

```text
                 Incoming Requests
                         |
                 Load Balancer
                  /     |     \
                 /      |      \
            App #1    App #2    App #3
                 \      |      /
                  \     |     /
                    Database
```

The application tier can scale horizontally, but all three application servers still send database requests to the same database.

If the database is the bottleneck, adding more application servers may increase the number of concurrent database requests without increasing the database's capacity.

The architecture needs to address the component that is actually limiting throughput.

This is why scaling decisions should follow measurements rather than assumptions.

Before introducing sharding, investigate:

- Query execution plans and slow queries.
- Missing or inefficient indexes.
- CPU, memory, storage, and disk I/O utilization.
- Lock waits and transaction duration.
- Connection pool saturation.
- Whether read replicas or caching can reduce primary-database load.
- Whether the workload is constrained by reads, writes, storage, or a particular hot table.

Sharding is not a substitute for fixing inefficient queries or a poorly designed schema.

## 4. What Is Database Sharding?

Database sharding is a form of horizontal partitioning in which records are distributed across multiple independent database instances, commonly called **shards**.

Instead of storing every record in one database, we divide the dataset into smaller partitions and assign each partition to a different shard.

For example, imagine a user platform with three database shards.

```text
                   Application
                        |
                    Shard Router
                   /     |     \
                  /      |      \
             Shard 1  Shard 2  Shard 3
             Users    Users    Users
             A - H    I - P    Q - Z
```

This diagram illustrates range-based partitioning by username. It is only one possible strategy, and it can produce uneven workloads if some ranges contain more data or receive more traffic.

With a suitable partitioning strategy, each shard stores only part of the total dataset. Reads and writes can be directed to the shard responsible for the relevant record.

This can distribute storage and database workload across multiple machines.

However, sharding introduces a new responsibility: the application or a database routing layer must know where each record belongs.

## 5. How Sharding Changes the Architecture

Consider two approaches.

### Approach A: One database

```text
Application
     |
     v
Database
  - All users
  - All orders
  - All transactions
```

The database owns the complete dataset. The architecture is straightforward, but its capacity is tied to the resources and configuration of that database system.

### Approach B: Multiple shards

```text
Application
     |
     v
Shard Router
     |
     +------> Shard 1
     |        Users 1, 4, 7
     |
     +------> Shard 2
     |        Users 2, 5, 8
     |
     +------> Shard 3
              Users 3, 6, 9
```

Here, the example illustrates records assigned by a partitioning rule rather than by their numeric sequence.

The router determines the target shard from a partitioning rule or metadata. Each shard owns a subset of the data.

This architecture can provide more aggregate storage and capacity, but only when data placement and the workload allow the work to be distributed effectively.

A request that touches one shard can be relatively straightforward. A request that needs records from every shard may require additional network calls and result aggregation.

## 6. What Problems Does Sharding Solve?

When the workload and shard key are appropriate, sharding can help with:

- **Storage capacity:** Spread a large dataset across multiple database instances.
- **Write throughput:** Distribute writes across shards instead of directing every write to one database.
- **Read workload:** Distribute reads when requests can be routed to individual shards.
- **Resource isolation:** Reduce competition between records assigned to different shards.
- **Incremental capacity growth:** Add shards as the dataset or workload grows, subject to the chosen sharding strategy and migration process.

These benefits are not automatic.

For example, if most requests target one shard, that shard can remain overloaded while other shards sit relatively idle. This is known as a hotspot.

Likewise, adding a shard does not guarantee a proportional increase in throughput. The result depends on query patterns, shard key distribution, replication, coordination overhead, and the database technology.

## 7. What New Problems Does Sharding Introduce?

Sharding spreads data across multiple databases, but it also makes the system harder to operate.

### 7.1 Choosing the shard key

The shard key determines how records are assigned to shards.

A poor choice can produce uneven data distribution or concentrate most requests on a small subset of shards.

Changing the shard key later can be difficult because data may need to be redistributed.

### 7.2 Routing queries

The application must determine which shard contains the required record.

If a request includes the shard key, the router may be able to contact one shard directly.

If it does not, the system may need to query multiple shards and combine their results.

### 7.3 Rebalancing data

When a shard is added, removed, or becomes overloaded, some records may need to move.

The system must keep track of where records belong while handling reads and writes during migration.

### 7.4 Cross-shard operations

Operations that span multiple shards are more complicated.

Examples include joining records stored on different shards, enforcing uniqueness across the entire dataset, and coordinating transactions that update multiple shards.

The guarantees available depend on the database technology and architecture.

### 7.5 Operational complexity

Instead of managing one database instance, the team may need to manage many.

Monitoring, backups, migrations, schema changes, capacity planning, and incident response all become more involved.

**Sharding trades a single database's capacity constraints for the complexity of distributing data and coordinating operations.**

That trade-off needs to be justified by the workload.

## 8. When Should We Consider Sharding?

Sharding is worth evaluating when measurements show that a single database is becoming a sustained bottleneck and simpler solutions are insufficient or uneconomical.

A sensible evaluation sequence is:

1. Measure database performance under representative workloads.
2. Fix slow queries, missing indexes, and inefficient transaction patterns.
3. Optimize connection management and reduce unnecessary database requests.
4. Evaluate caching and read replicas when the workload permits them.
5. Scale the database vertically if it remains a cost-effective option.
6. Consider sharding when storage, write capacity, resource limits, or workload isolation still justify distributing the data.

Not every application needs sharding.

For a small application with moderate traffic, a well-configured single database may be cheaper, easier to maintain, and more reliable operationally than a sharded system.

The objective is not to introduce the most complex architecture possible. It is to choose an architecture that meets the application's actual requirements.

## 9. What We Will Build in This Repository

We will use Python to simulate the main ideas behind sharding without requiring a database server.

The implementation will progress through these steps:

1. Start with a single in-memory database containing all records.
2. Demonstrate a basic sharding approach and its limitations.
3. Assign keys to shards using modulo hashing.
4. Measure how records are distributed across shards.
5. Implement consistent hashing and compare key redistribution.
6. Build a simple query router that directs requests to the correct shard.
7. Simulate data rebalancing when the shard layout changes.
8. Demonstrate a query that needs data from multiple shards.

The examples will focus on understanding data placement, routing, and redistribution. They will not claim to implement database durability, replication, distributed transactions, or safe online migrations.

## 10. Key Takeaways

- A single database can become a bottleneck even when the application tier scales horizontally.
- Query optimization, indexing, caching, read replicas, and vertical scaling should be evaluated before introducing sharding.
- Sharding distributes records across multiple database instances and can increase aggregate capacity.
- The shard key and routing strategy strongly influence how well the workload is distributed.
- Cross-shard operations, rebalancing, and operations become more complicated as data is distributed.
- Sharding is a trade-off, not a default requirement for every growing application.

In the next document, we will define database sharding more precisely and distinguish it from related concepts such as table partitioning and replication.
