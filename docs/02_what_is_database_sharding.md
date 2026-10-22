# What Is Database Sharding?

## 1. Introduction

Database sharding is a technique for distributing a dataset across multiple database instances.

Instead of storing every record in one database, we divide the data into smaller partitions and assign each partition to a different database server, called a **shard**.

Each shard stores and manages only a subset of the overall dataset.

The application uses a partitioning rule or routing layer to determine which shard is responsible for a particular record.

For example, imagine an application with 12 million user records. Instead of storing every user in one database, we distribute the records across three shards.

```text
                    Application
                         |
                     Shard Router
                         |
              +----------+----------+
              |          |          |
              v          v          v
          Shard 1     Shard 2     Shard 3
          4M users    4M users    4M users
```

This is a conceptual example. Equal record counts do not necessarily mean equal storage usage or traffic.

The objective is to distribute data and workload so that a single database does not have to handle everything.

## 2. How Does Sharding Work?

A sharded application needs a rule for deciding where each record belongs.

That rule usually depends on a field called the **shard key**.

Suppose we store users with the following IDs:

```text
user_101
user_102
user_103
user_104
user_105
user_106
```

We could distribute these users using a deterministic hashing function.

For example:

```text
shard_index = hash(user_id) % number_of_shards
```

If there are three shards, the calculated shard index determines which shard receives a particular user.

The exact assignments depend on the hashing function and the number of shards. The important point is that the application can calculate the destination consistently.

A simplified request flow looks like this:

```text
Request: Read user_104
          |
          v
Extract shard key: user_104
          |
          v
Calculate destination shard
          |
          v
Send request to that shard
          |
          v
Return the user record
```

This is called **shard routing**.

In this repository, we will implement routing with Python and in-memory dictionaries. The examples will demonstrate the placement logic without requiring a real database.

## 3. Sharding vs. Partitioning

The terms *partitioning* and *sharding* are related, but they are not always used to mean the same thing.

### Partitioning

Partitioning divides a dataset into smaller logical or physical pieces.

For example, a database table containing orders could be partitioned by month:

```text
Orders
  |
  +-- January orders
  +-- February orders
  +-- March orders
  +-- April orders
```

The partitions may still belong to the same database instance and be managed by the same database engine.

Partitioning can improve query performance, simplify data retention, and make large tables easier to manage when the database can prune irrelevant partitions.

### Sharding

Sharding distributes partitions of a dataset across separate database instances.

```text
Application
     |
     v
Shard Router
     |
     +------> Database Instance 1
     |
     +------> Database Instance 2
     |
     +------> Database Instance 3
```

Each instance manages its assigned portion of the dataset.

Sharding can distribute storage and workload across machines, but it also introduces routing, coordination, and operational complexity.

A useful distinction is:

- **Partitioning** describes how data is divided.
- **Sharding** commonly describes distributing those partitions across separate database instances.

Some database products use the terminology differently, and a database can combine table partitioning with sharding.

## 4. Sharding vs. Replication

Sharding and replication solve different problems.

### Replication

Replication maintains copies of data on multiple database instances.

For example:

```text
                 Primary Database
                        |
                 Replication Stream
                   /          \
                  v            v
              Replica 1     Replica 2
```

Depending on the replication architecture, replicas may help serve read traffic, provide redundancy, or support recovery after a failure.

Replication does not necessarily distribute ownership of the dataset. Each replica may contain a copy of the same data.

### Sharding

Sharding divides data across database instances.

```text
             Complete User Dataset
                      |
             +--------+--------+
             |        |        |
             v        v        v
          Shard 1  Shard 2  Shard 3
          Users A  Users B  Users C
```

Each shard contains a different subset of the records.

### Can a system use both?

Yes. A production system may shard its dataset and replicate each shard.

```text
                  Shard Router
                       |
             +---------+---------+
             |                   |
             v                   v
          Shard A              Shard B
             |                   |
        +----+----+         +----+----+
        |         |         |         |
        v         v         v         v
      Primary  Replica    Primary  Replica
```

The diagram illustrates two logical shards, each with a primary and a replica. Actual deployment topologies vary by database technology.

Sharding distributes the dataset. Replication maintains additional copies of data. Combining them can address both capacity and availability requirements, but replication lag, failover, and consistency still need to be handled.

## 5. Common Sharding Strategies

There are several ways to decide which shard receives a record.

### 5.1 Range-based sharding

Records are assigned based on ranges of a key.

For example:

```text
Shard 1: user_id 1 - 1,000,000
Shard 2: user_id 1,000,001 - 2,000,000
Shard 3: user_id 2,000,001 - 3,000,000
```

Range-based sharding can be useful when queries frequently access ranges of keys.

The downside is that some ranges may grow faster or receive more traffic than others. Sequential IDs can also concentrate new writes on the newest range.

### 5.2 Modulo-based sharding

A hash of the shard key is mapped to a shard using the remainder operator.

```text
shard_index = stable_hash(key) % shard_count
```

This is simple to implement and can distribute keys reasonably well when the key distribution and hash function are suitable.

However, changing the shard count can change the destination for many existing keys.

We will explore this problem in `06_modulo_sharding.md`.

### 5.3 Consistent hashing

Consistent hashing maps keys and shard identifiers onto a logical hash ring.

A key is assigned to the next shard position according to the ring's routing rule. When a shard is added or removed, only a portion of keys generally need to move.

Virtual nodes can improve distribution by representing each physical shard at multiple positions on the ring.

Consistent hashing reduces redistribution in many configurations, but it does not guarantee perfectly balanced storage or traffic.

We will implement this strategy later and compare its key movement with modulo hashing.

## 6. What Makes a Good Shard Key?

Choosing a shard key is one of the most important decisions in a sharded system.

A good shard key should support the application's query patterns and distribute the workload appropriately.

Consider three possible choices for an e-commerce platform:

| Candidate key | Potential benefit | Potential problem |
|---|---|---|
| `user_id` | User-related requests can often route directly to one shard | Queries spanning many users may require multiple shards |
| `region` | Can place regional data together and support regional access patterns | Some regions may receive much more traffic than others |
| `created_at` | Range queries and time-based retention can be straightforward | New writes may concentrate on the latest range |

There is no universally best shard key.

The correct choice depends on:

- Which fields appear in common read and write requests.
- How evenly records and traffic are distributed.
- Whether the system needs uniqueness across the complete dataset.
- Which queries must access records from different users or tenants.
- How data will be moved when capacity changes.

We will examine shard key selection in detail in `04_shard_key_selection.md`.

## 7. What Happens When a New Shard Is Added?

Sharding introduces an important scaling question: how does the system redistribute data when the number of shards changes?

Suppose an application has three shards and adds a fourth.

With simple modulo-based sharding, the routing formula changes from:

```text
shard_index = stable_hash(key) % 3
```

to:

```text
shard_index = stable_hash(key) % 4
```

For many keys, the result will be different. Records may need to move to their newly calculated destinations.

Consistent hashing generally limits movement to keys associated with the changed part of the ring, rather than recalculating every key against a new shard count.

The amount of data moved depends on the strategy, ring configuration, and shard membership changes.

This is why adding a database server is not always as simple as connecting it to the application.

The system must also manage data placement, routing changes, and migration safely.

## 8. What Sharding Does Not Automatically Solve

Sharding can increase aggregate capacity, but it does not remove every database problem.

It does not automatically fix:

- Slow queries caused by poor indexes or inefficient SQL.
- Hotspots caused by uneven key or traffic distribution.
- Queries that need to scan data across every shard.
- Transactions that update records on multiple shards.
- Global uniqueness constraints that span shards.
- Replication, failover, or recovery requirements.
- Data movement and consistency challenges during rebalancing.

Some workloads also do not partition naturally. If nearly every request requires data from every shard, the coordination and network costs may outweigh the benefits.

The design needs to follow the workload rather than assuming that distributing the data will make every operation faster.

## 9. What We Will Implement

This repository will build a small sharding simulator using Python's standard library.

We will implement:

1. A single in-memory store as the baseline.
2. A basic sharded representation.
3. Modulo hashing for deterministic shard selection.
4. Key distribution measurements.
5. Consistent hashing with virtual nodes.
6. A query router for locating records.
7. A simplified data rebalancing simulation.
8. A cross-shard read example.

The simulator will make it possible to inspect where keys are assigned and measure how assignments change when the shard layout changes.

It will not behave like a production database. It will not provide durable storage, replication, distributed transactions, or safe online migrations.

## 10. Key Takeaways

- Database sharding distributes subsets of a dataset across separate database instances.
- A shard key determines how records are assigned and influences query routing.
- Partitioning divides data; sharding commonly distributes those partitions across database instances.
- Replication maintains copies of data, while sharding distributes different portions of the dataset.
- Modulo hashing is simple but can cause substantial key redistribution when the shard count changes.
- Consistent hashing can reduce key movement, although workload balance still needs to be measured.
- Sharding adds architectural and operational complexity, so it should be introduced when the workload justifies it.

In the next document, we will compare vertical scaling with horizontal scaling and examine why adding resources to one database differs from distributing data across multiple database instances.
