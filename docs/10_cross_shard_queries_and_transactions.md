# Cross-Shard Queries and Transactions

Database sharding improves scalability by distributing records across multiple shards. However, this distribution introduces a challenge: some operations need data from more than one shard.

A request that accesses a single shard can often be executed directly. A request that spans multiple shards may require coordination, result merging, or transaction management.

These operations are known as cross-shard queries and cross-shard transactions.

Understanding their trade-offs is important because sharding can improve scalability while making some application operations more complicated.

## 1. The Problem: Data Is Distributed

Imagine an e-commerce application that stores customer and order records across three shards.

```text
Shard 0
    ├── Customer 101
    ├── Order 5001
    └── Order 5002

Shard 1
    ├── Customer 202
    ├── Order 6001
    └── Order 6002

Shard 2
    ├── Customer 303
    ├── Order 7001
    └── Order 7002
```

This is a simplified illustration. In a real system, the actual placement depends on the shard key and routing strategy.

Suppose the application needs to retrieve all orders belonging to Customer 101.

If the orders are sharded using `customer_id`, the application can calculate the appropriate shard and retrieve the customer's orders directly.

Now consider a different requirement:

> Find the total value of all orders placed across every customer.

If orders are distributed across all three shards, the application may need to query each shard and combine the partial results.

This is a cross-shard query.

The operation is possible, but it requires additional work compared with a query that targets a single shard.

## 2. Single-Shard Queries vs. Cross-Shard Queries

### Single-Shard Query

A request contains enough information to identify the destination shard.

```text
Request
   |
   v
Query Router
   |
   v
Shard 1
   |
   v
Return Result
```

For example:

```sql
SELECT *
FROM orders
WHERE customer_id = 202;
```

If `customer_id` is the shard key, the application can route the request to the relevant shard.

### Cross-Shard Query

A request needs information distributed across multiple shards.

```text
                  Request
                     |
                     v
                Query Router
                     |
          +----------+----------+
          |          |          |
          v          v          v
       Shard 0    Shard 1    Shard 2
          |          |          |
          +----------+----------+
                     |
                     v
              Merge Results
                     |
                     v
                Return Result
```

For example:

```sql
SELECT *
FROM orders
WHERE status = 'pending';
```

If `status` is not the shard key and no routing index identifies the relevant shards, the application may need to search every shard.

The exact behavior depends on the database architecture and query-routing layer. The SQL statement alone does not guarantee that a query will be targeted or distributed.

## 3. Why Cross-Shard Queries Are More Expensive

A cross-shard query may introduce several costs.

### More Network Requests

The application or query coordinator must communicate with multiple database servers.

### More Database Work

Each shard must execute its part of the query, potentially competing with normal traffic.

### Result Merging

The application must combine partial results into the required response.

For example, merging may involve:

- Concatenating records.
- Sorting records from multiple shards.
- Combining partial aggregate results.
- Removing duplicates when the query semantics require it.

### Latency Coordination

If the query requires results from every shard, its completion time can be dominated by the slowest required response, plus coordination and merging overhead.

Parallel execution can help, but it does not eliminate this dependency.

### More Failure Scenarios

A shard may be unavailable or may time out while the other shards respond successfully.

The application must decide whether to fail the request, retry, return a partial result where acceptable, or use another recovery mechanism.

For operations that require a complete and consistent result, silently ignoring a failed shard can produce incorrect answers.

## 4. Cross-Shard Aggregations

Aggregations are a common reason to query multiple shards.

Suppose an application wants to calculate the total number of orders across three shards.

Each shard calculates a local count:

```text
Shard 0: 120 orders
Shard 1: 180 orders
Shard 2: 150 orders
```

The application combines the partial results:

```text
Total orders = 120 + 180 + 150 = 450
```

This works because counts can be combined by addition.

However, not every aggregate can be merged by applying the same operation to local results.

### Average

Suppose the shards return:

```text
Shard 0:
    Total order value = 1,000
    Number of orders = 10

Shard 1:
    Total order value = 9,000
    Number of orders = 90
```

Averaging the two shard averages equally would be incorrect because the shards contain different numbers of orders.

Instead, calculate the global average using the combined totals:

\[
\text{Average} =
\frac{\sum \text{Local Totals}}
{\sum \text{Local Counts}}
\]

For this example:

\[
\text{Average} = \frac{1000 + 9000}{10 + 90} = 100
\]

This illustrates why distributed aggregation requires understanding the mathematical properties of the operation.

Counts and sums can often be combined directly. Averages require sufficient information, such as each shard's sum and count. Other operations, such as exact distinct counts and percentiles, may require more expensive merging or specialized algorithms.

## 5. Sorting and Pagination Across Shards

Consider a request to retrieve the ten most recent orders across all shards.

Each shard may return its own ten most recent orders, but those local results do not necessarily represent the ten most recent orders globally.

The application must compare timestamps across the results and merge them into the correct global order.

Pagination introduces additional complexity.

For example, the application cannot always retrieve page two by simply requesting the second page independently from every shard and concatenating the results. It needs a consistent global ordering and a strategy for determining which records belong to the requested page.

A production design must also consider concurrent inserts, deletes, and updates between page requests.

This is one reason why queries aligned with the shard key and access patterns can be significantly easier to scale.

## 6. What Is a Cross-Shard Transaction?

A transaction groups operations that must satisfy a defined set of consistency guarantees.

Consider a simple money transfer between two accounts:

```text
Account A balance: 1,000
Account B balance: 500

Transfer: 200
```

The transfer should perform two operations:

1. Deduct 200 from Account A.
2. Add 200 to Account B.

After a successful transfer:

```text
Account A balance: 800
Account B balance: 700
```

The total balance remains 1,500.

Now suppose Account A is stored on Shard 0 and Account B is stored on Shard 1.

```text
              Transfer Request
                     |
                     v
               Transaction Logic
                 /         \
                v           v
             Shard 0      Shard 1
            Deduct 200    Add 200
```

The operation now spans two shards.

If the deduction succeeds but the credit fails, the system must prevent or recover from an inconsistent outcome.

A transaction confined to one database shard can often use that database's native transaction mechanism. Coordinating an atomic transaction across independently managed shards requires additional support.

## 7. Why Cross-Shard Transactions Are Difficult

Several failure scenarios must be considered.

### Partial Failure

One shard commits its operation while another shard fails.

### Network Timeout

The coordinator may not know whether a remote operation succeeded or whether the response was simply lost.

### Concurrent Updates

Other transactions may modify the same records while the cross-shard operation is in progress.

### Coordinator Failure

The service coordinating the transaction may fail after some participants have prepared or committed their operations.

### Locking and Contention

A transaction spanning multiple shards may hold resources for longer while it waits for other participants.

These concerns make distributed transactions more complex than a transaction executed entirely within one database.

## 8. Distributed Transactions and Two-Phase Commit

One established approach for coordinating atomic transactions across multiple participants is **two-phase commit (2PC)**, when supported by the database systems and transaction coordinator involved.

At a high level, it has two phases.

### Phase 1: Prepare

The coordinator asks each participant whether it can commit the transaction.

Each participant performs the necessary checks and prepares its changes. A participant that votes to commit must retain enough state to follow the coordinator's eventual decision.

### Phase 2: Commit or Abort

If all required participants vote to commit, the coordinator instructs them to commit.

If a participant cannot prepare, the coordinator can direct the transaction to abort.

Conceptually:

```text
                 Coordinator
                 /          \
                v            v
             Shard 0       Shard 1
                |            |
                +-----+------+
                      |
                Prepare Phase
                      |
             +--------+--------+
             |                 |
       All prepared?          Failure
             |                 |
             v                 v
           Commit             Abort
```

This is a simplified illustration. A real protocol also needs durable transaction state, recovery handling, and well-defined behavior when messages or participants fail.

### Advantages

- Can provide atomic commit across participating systems when implemented correctly.
- Helps prevent a transaction from committing on only a subset of participants under the protocol's guarantees.
- Provides a defined coordination process for multi-participant transactions.

### Disadvantages

- Adds coordination and network overhead.
- Participants may need to retain locks or prepared state while waiting.
- Failures can leave participants waiting for a coordinator's decision.
- Operational recovery is more complicated than for a single-shard transaction.

Two-phase commit is not the only way to design multi-service workflows, and it is not available in every sharded database architecture. Whether it is appropriate depends on the database, consistency requirements, and operational constraints.

## 9. Alternatives to Cross-Shard Transactions

Not every workflow needs a distributed ACID transaction.

Depending on the business requirement, other designs may reduce coordination.

### Keep Related Data Together

Choose a shard key that places records commonly updated together on the same shard.

For example, if an operation frequently reads and updates a customer's account and related metadata, colocating those records may simplify the transaction.

This is not always possible, especially when an operation spans many customers or tenants.

### Use a Saga

A saga breaks a long-running business workflow into smaller transactions. If a later step fails, the workflow may execute compensating actions to reverse the business effect of earlier steps.

For example, an order workflow might:

1. Reserve inventory.
2. Charge a payment method.
3. Confirm the order.

If payment fails after inventory reservation, the workflow may release the reservation.

A compensation is not necessarily a literal rollback. A refund, for example, is a new business operation with its own failure modes.

Sagas are useful when eventual consistency is acceptable and the business process can define meaningful compensating actions.

### Use Asynchronous Processing

Some operations can be handled through events or background processing rather than requiring every participating system to update atomically within one request.

This can reduce synchronous coordination, but it introduces eventual-consistency concerns, retries, duplicate delivery, and the need to track processing status.

### Accept Explicitly Defined Eventual Consistency

For some non-critical views, such as reporting summaries, a temporarily stale result may be acceptable.

The application should define how stale the data may be and how failures are detected and corrected.

Eventual consistency is a business and system-design decision, not a blanket replacement for transactions where atomicity is required.

## 10. Designing Around Cross-Shard Operations

Before introducing a sharding strategy, identify the operations that need to read or update related records.

Consider these questions:

- Which records are commonly accessed together?
- Which operations require atomic updates?
- Can the shard key colocate related records?
- Which queries can be targeted to one shard?
- Which cross-shard queries are unavoidable?
- Can reporting workloads tolerate eventual consistency?
- What should happen when one participant is unavailable?

A system with excellent single-shard performance can still struggle if its most important business operations regularly span many shards.

For this reason, shard-key design, data modeling, and transaction boundaries should be considered together rather than independently.

## 11. What We Will Implement in This Repository

This repository uses in-memory Python dictionaries to explain sharding concepts without requiring a database server.

The upcoming example, `examples/08_cross_shard_query.py`, will demonstrate a simplified query that retrieves records across multiple in-memory shards and combines the results.

The implementation will focus on:

1. Creating multiple shards with sample records.
2. Querying records from more than one shard.
3. Combining the returned results.
4. Showing why a cross-shard query differs from a targeted lookup.

The example will not implement a distributed transaction coordinator, two-phase commit, a saga engine, or database-level isolation guarantees.

Those mechanisms require additional infrastructure and correctness considerations beyond the scope of this educational simulation.

## 12. Key Takeaways

- Cross-shard queries access data distributed across multiple shards and may require coordination.
- Scatter-gather operations can increase resource usage and latency.
- Global aggregation, sorting, and pagination require correct result-merging logic.
- Cross-shard transactions are harder because participants can fail independently.
- Two-phase commit can coordinate atomic commit but introduces coordination and recovery costs.
- Sagas and asynchronous processing can be alternatives when the business workflow permits eventual consistency.
- Good shard-key and data-model design can reduce unnecessary cross-shard operations.

Sharding is not only about distributing storage. It also changes how the application executes queries and maintains consistency across related records.

The most effective design is one that scales data access while keeping the application's important business operations correct and manageable.

## Next Step

Next, we will bring the concepts together and discuss the production trade-offs of database sharding, including operational complexity, failure handling, and when sharding is worth introducing.

Next file: `docs/11_production_tradeoffs.md`
