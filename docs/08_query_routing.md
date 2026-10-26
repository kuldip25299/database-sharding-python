# Query Routing in a Sharded Database

Database sharding distributes records across multiple shards, but this creates an important question:

**When a request arrives, how does the application know which shard contains the required data?**

Query routing is the process of determining which shard or shards should handle a database request.

Without an effective routing strategy, an application may need to query every shard to find a single record. As the number of shards grows, this can increase latency, consume resources, and make the system harder to scale.

In this document, we will explore how query routing works, compare targeted and scatter-gather queries, and examine the trade-offs involved in designing a shard router.

## 1. The Problem: Finding a Record Across Multiple Shards

Imagine an application that stores user records across four database shards.

```text
                    Application
                         |
                         v
                    User Request
                         |
             +-----------+-----------+
             |           |           |
             v           v           v
          Shard 0     Shard 1     Shard 2     Shard 3
```

A request arrives to retrieve user `105`.

If the application knows that `user_id` is the shard key, it can calculate the destination using the configured routing strategy.

For modulo-based sharding with four shards:

```python
shard_index = 105 % 4
```

The result is `1`, so the application routes the request to Shard 1.

The application does not need to query every shard.

However, consider a different request:

```sql
SELECT *
FROM users
WHERE email = 'customer@example.com';
```

If `email` is not the shard key and there is no separate lookup mechanism, the application may not know which shard contains the user.

This is where query routing becomes an important part of the system design.

## 2. What Is Query Routing?

Query routing determines the destination for a database operation based on information such as:

- The shard key included in the request.
- The selected sharding strategy.
- The current mapping between keys and shards.
- Additional routing metadata, if the system uses it.

A simplified routing flow looks like this:

```text
Incoming Request
       |
       v
Extract Shard Key
       |
       v
Apply Routing Strategy
       |
       v
Determine Target Shard
       |
       v
Execute Query on Shard
       |
       v
Return Result
```

For example, an application using modulo sharding can calculate the destination directly from the shard key.

An application using consistent hashing must find the next shard clockwise from the key's position on the configured hash ring.

The routing strategy differs, but the goal is the same: direct the request to the appropriate shard.

## 3. Targeted Queries

A targeted query can identify the shard or shards that need to process a request without searching the entire cluster.

Consider this request:

```text
Get user with user_id = 105
```

If `user_id` is the shard key and the routing configuration is available, the application can determine the destination directly.

```text
Request: Get user 105
          |
          v
Calculate destination
          |
          v
       Shard 1
          |
          v
Return user record
```

### Why Targeted Queries Matter

Targeted queries can reduce:

- The number of database servers contacted.
- Unnecessary database work.
- Network traffic between the application and shards.
- Query latency, depending on the workload and infrastructure.

They also make resource usage more predictable because the application knows which shard should handle the request.

### Example: Customer Orders

Suppose orders are sharded using `customer_id`.

A request for all orders belonging to customer `5001` can be routed directly if the application knows the customer's shard.

However, a request for all orders created during a particular month may require multiple shards if the date is not part of the routing scheme.

**The effectiveness of targeted routing depends heavily on choosing a shard key that matches common access patterns.**

## 4. Scatter-Gather Queries

Sometimes a request does not contain enough information to identify a single shard.

For example:

```sql
SELECT *
FROM users
WHERE account_status = 'active';
```

If `account_status` is not the shard key and there is no index or lookup service that identifies the relevant shards, the application may need to send the query to every shard.

This is known as a scatter-gather query.

### How It Works

```text
                  Incoming Query
                        |
                        v
                   Query Router
                        |
          +-------------+-------------+
          |             |             |
          v             v             v
       Shard 0       Shard 1       Shard 2       Shard 3
          |             |             |             |
          +-------------+-------------+
                        |
                        v
                 Combine Results
                        |
                        v
                   Return Data
```

Each shard processes the query independently. The application or query coordinator then combines the results.

For example, if each shard returns a list of active users, the coordinator may concatenate those lists before returning the response.

For aggregation queries, it may need to merge partial counts, sums, or other results correctly.

### Advantages

- Supports queries that cannot be routed to a single shard.
- Allows searches across distributed datasets.
- Can execute independent shard-level operations concurrently.

### Disadvantages

- More database servers must process the request.
- The request may consume significantly more resources.
- Overall latency depends on the slowest required shard and the coordination work.
- Combining, sorting, or aggregating results can be expensive.
- Pagination and ordering require additional care.

A scatter-gather query is not automatically wrong. Some reporting and analytical workloads require it. The concern is using it frequently for latency-sensitive requests when targeted routing is possible.

## 5. The Slowest-Shard Problem

Suppose a scatter-gather query is sent to four shards concurrently.

Their response times are:

| Shard | Response time |
|---|---:|
| Shard 0 | 20 ms |
| Shard 1 | 25 ms |
| Shard 2 | 18 ms |
| Shard 3 | 120 ms |

The router cannot finish collecting all four responses until Shard 3 returns, assuming all responses are required.

The shard-level portion of the request therefore takes at least 120 ms, before accounting for coordination and result merging.

This is an important distributed-systems trade-off: parallel requests can reduce the time compared with executing every query sequentially, but the overall response may still be dominated by a slow shard.

The same principle applies when a request fans out to many services or database partitions.

## 6. Routing with Different Sharding Strategies

The routing mechanism depends on the sharding strategy.

### Modulo-Based Routing

For a fixed shard count, routing can use:

```python
shard_index = stable_hash(shard_key) % number_of_shards
```

The same key must produce the same hash result, and all application instances must use compatible routing configuration.

When the shard count changes, many keys may receive different assignments. The application must coordinate routing updates with data migration.

### Consistent-Hashing Routing

With consistent hashing, the router:

1. Hashes the shard key.
2. Finds the key's position on the ring.
3. Finds the next virtual-node position clockwise.
4. Resolves that virtual node to its physical shard.
5. Routes the request to that shard.

The ring configuration must be consistent across application instances.

Consistent hashing reduces reassignment when shard membership changes, but it does not eliminate the need to migrate records or coordinate routing changes.

### Lookup-Based Routing

Some systems maintain a mapping between a key and its owning shard.

For example:

```text
customer_id -> shard_id
```

The router looks up the mapping before executing the request.

This approach can support more flexible placement, but it introduces additional concerns:

- Where the mapping is stored.
- How it is cached.
- How stale mappings are detected.
- How routing changes are coordinated.
- How the lookup service itself is kept available and scalable.

A lookup-based approach is useful when direct calculation is insufficient, but it adds another component that must be maintained correctly.

## 7. What Happens When the Shard Key Is Missing?

Consider an application that shards user records by `user_id`.

A request arrives to find a user by email:

```text
Find user where email = customer@example.com
```

The application has several possible approaches.

### Option 1: Search Every Shard

The application queries each shard and combines the results.

This is simple conceptually, but can become expensive when performed frequently.

### Option 2: Maintain a Lookup Mapping

The application maintains an index such as:

```text
email -> user_id
```

It uses the lookup to retrieve the user's ID, then routes to the correct shard.

The mapping must remain consistent with the underlying records, including during updates and migrations.

### Option 3: Change the Data Model or Sharding Strategy

If email-based lookups dominate the workload, it may be worth reconsidering the shard key or maintaining a separate index designed for those queries.

There is no universal answer. The decision depends on query frequency, consistency requirements, write patterns, and operational cost.

The key principle is that **a shard key optimizes some access patterns, but it does not automatically optimize every possible query**.

## 8. Query Routing During Data Rebalancing

Routing becomes more complicated when records move between shards.

Suppose a record originally belongs to Shard 1, but a rebalancing operation moves it to Shard 3.

During migration, the system must avoid situations where:

- Reads are sent to a shard that no longer has the current record.
- Writes are applied to one copy but not another.
- Different application instances use conflicting routing information.
- A partially completed migration makes records temporarily inaccessible.

A production system needs a migration protocol that defines when the new shard becomes authoritative and how concurrent reads and writes are handled.

Possible designs include carefully coordinated routing updates, temporary forwarding, dual-write or change-capture mechanisms, and explicit migration states. Each approach has its own consistency and failure-handling trade-offs.

For this educational repository, we will simulate routing decisions rather than implement a production migration protocol.

## 9. Practical Design Guidelines

When designing query routing for a sharded application, consider the following guidelines.

### Design Around Common Queries

Identify the operations the application performs most often. Choose a shard key that allows these operations to reach the appropriate shard whenever possible.

### Avoid Unnecessary Fan-Out

Do not query every shard when the shard key already identifies the destination.

### Make Routing Configuration Consistent

All application instances must agree on the shard count, hash algorithm, ring configuration, or lookup mapping they use.

### Treat Cross-Shard Queries as a Separate Concern

Queries involving multiple shards may require result merging, ordering, aggregation, pagination, or additional coordination.

### Plan for Topology Changes

Adding a shard changes routing and may require data migration. The router must not assume that changing the shard configuration is sufficient to relocate existing records.

### Measure Real Workloads

Track how frequently requests target one shard versus multiple shards, as well as shard-level latency and resource utilization. This helps identify when routing decisions are contributing to performance problems.

## 10. What We Will Implement in This Repository

The upcoming example, `examples/06_query_router.py`, will demonstrate a basic query router using in-memory shards.

The implementation will focus on:

1. Creating a collection of shards.
2. Determining a destination from a shard key.
3. Routing record insertion and retrieval.
4. Showing the difference between a targeted lookup and searching multiple shards.
5. Keeping routing logic separate from the operation that accesses a shard.

The example will use a simple routing strategy that is consistent with the earlier modulo-sharding implementation.

It will not implement a real SQL query planner, distributed transaction coordinator, persistent routing directory, or production migration protocol.

## 11. Key Takeaways

- Query routing determines which shard or shards should process a request.
- Targeted queries avoid unnecessary work by routing directly to the relevant shard.
- Scatter-gather queries search multiple shards and require result coordination.
- A scatter-gather request can be delayed by its slowest required shard.
- Queries that do not include the shard key may need a lookup mechanism or a multi-shard search.
- Routing configuration must remain consistent across application instances.
- Data migration and routing changes must be coordinated to preserve access to existing records.

Sharding distributes data, but query routing determines whether the application can use that distribution efficiently.

A well-designed shard router minimizes unnecessary database work while keeping routing behavior predictable as the system grows.

## Next Step

Next, we will examine data rebalancing: what happens when the distribution of data becomes uneven or the application needs to add or remove shards.

Next file: `docs/09_data_rebalancing.md`
