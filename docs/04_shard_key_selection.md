# Shard Key Selection

## 1. Why Is the Shard Key Important?

Database sharding distributes records across multiple database instances. But before the application can route a request to a shard, it needs a rule that determines where each record belongs.

That rule usually depends on a field called the **shard key**.

Consider an e-commerce application that stores millions of users and their orders.

A user record might look like this:

```python
user = {
    "user_id": 1042,
    "name": "Asha",
    "region": "India",
    "created_at": "2026-01-10",
}
```

We could distribute these records using `user_id`, `region`, or `created_at`.

Each choice produces a different data distribution and affects how queries are routed.

For example, if `user_id` is the shard key, a request to retrieve one user can usually be routed directly to the responsible shard.

If `region` is the shard key, users from the same region may be assigned to the same shard. That can help regional access patterns, but a heavily populated region may create an overloaded shard.

**The shard key affects data distribution, request routing, and how much coordination the application needs.**

Choosing it is an architectural decision, not just a hashing implementation detail.

## 2. What Makes a Good Shard Key?

A useful shard key should satisfy several requirements.

### 2.1 High cardinality

Cardinality refers to the number of distinct values a field can have.

For example:

- `user_id` may have millions of distinct values.
- `country` may have a relatively small number of distinct values.
- `account_status` may have only a few values, such as `active`, `inactive`, and `suspended`.

A high-cardinality field provides more opportunities to distribute records across shards.

A low-cardinality field can be problematic if the sharding strategy assigns each distinct value to only one shard. For example, sharding solely by account status could concentrate a large share of active users on one shard.

High cardinality alone does not guarantee a good shard key. The distribution and query workload matter too.

### 2.2 Even data distribution

The key should distribute records reasonably evenly across the available shards.

Suppose an application has three shards.

A balanced distribution might look like this:

```text
Shard 1: 330,000 records
Shard 2: 335,000 records
Shard 3: 335,000 records
```

An uneven distribution might look like this:

```text
Shard 1: 850,000 records
Shard 2: 100,000 records
Shard 3:  50,000 records
```

In the second example, the first shard holds most of the data.

The other shards may have unused capacity while the busiest shard becomes a bottleneck.

Actual capacity also depends on record size, indexes, request volume, and query cost. Equal record counts are a useful starting point, not a complete measure of balance.

### 2.3 Even request distribution

Data distribution and traffic distribution are different.

Imagine three shards each storing roughly one-third of the records. If most users access records on Shard 1, that shard may still receive most of the requests.

A good shard key should be evaluated against both:

- How much data each shard stores.
- How much read and write traffic each shard receives.

A system can have balanced storage but badly imbalanced traffic.

### 2.4 Compatibility with query patterns

The shard key should work well with the application's common queries.

Suppose the application frequently executes:

```sql
SELECT *
FROM users
WHERE user_id = 1042;
```

If `user_id` is the shard key, the router can calculate the target shard and avoid querying every database.

Now consider:

```sql
SELECT *
FROM users
WHERE region = 'India';
```

If the data is sharded by `user_id`, this query may need to search multiple shards unless the system has another index, routing mechanism, or data placement strategy that helps locate the records.

A shard key should be selected with the actual access patterns in mind.

### 2.5 Stability

A shard key should not change frequently.

If the field used for placement changes, the record may need to move to another shard.

For example, assigning users by a mutable field such as account status or current region can create migration work whenever that field changes, depending on the routing strategy.

A stable identifier is often a safer choice, provided it also supports the workload and distributes requests appropriately.

## 3. Comparing Common Shard Key Candidates

Consider a multi-tenant SaaS application with users, organizations, and activity records.

We could choose several candidate keys.

| Candidate | Potential benefit | Main risk |
|---|---|---|
| `user_id` | Routes individual user requests efficiently | Queries spanning many users may touch multiple shards |
| `tenant_id` | Keeps a tenant's data together | Large tenants can create hotspots |
| `region` | Can support regional data access or residency requirements | Uneven regional populations and traffic |
| `created_at` | Can support time-range access and retention policies | New records may concentrate on the newest range |
| `account_status` | Simple field with a small number of possible values | Low cardinality can produce severe imbalance |

None of these fields is universally best.

For example, `tenant_id` may be an excellent shard key if most queries operate within one tenant. However, if one tenant generates 40% of all requests, assigning that tenant to a single shard may create a hotspot.

The right choice depends on the workload, the distribution of keys, and the operational requirements.

## 4. Example: Sharding by User ID

Suppose an application stores 12 user records:

```text
User IDs:
101, 102, 103, 104,
105, 106, 107, 108,
109, 110, 111, 112
```

We have three shards:

```text
Shard 1
Shard 2
Shard 3
```

A simple modulo-based strategy can assign each user using:

```python
shard_index = stable_hash(user_id) % shard_count
```

For integer IDs, a simplified mapping can also use:

```python
shard_index = user_id % shard_count
```

The second formula is useful for illustrating the concept, but it is not a general-purpose hashing strategy. Its distribution depends on the key values and shard count.

For the example IDs, using the direct integer remainder:

```text
Shard 1: 102, 105, 108, 111
Shard 2: 103, 106, 109, 112
Shard 3: 101, 104, 107, 110
```

Each shard receives four records.

This example demonstrates a balanced distribution for a particular sequence of IDs. Real identifiers and traffic patterns are not always this uniform.

### What are the benefits?

- User records can be distributed across multiple shards.
- A request containing `user_id` can be routed to one shard.
- Adding application instances does not require every instance to hold the complete dataset.
- The placement rule is easy to calculate.

### What are the limitations?

Suppose a reporting request needs to count users from all regions.

If the records are distributed by `user_id`, the application may need to query all three shards and aggregate their results.

The choice works well for user-specific access, but not every query will be equally efficient.

## 5. Example: Sharding by Tenant ID

Now imagine a SaaS platform where each organization has its own users, invoices, and audit records.

Most queries are scoped to one organization:

```sql
SELECT *
FROM invoices
WHERE tenant_id = 5001;
```

Using `tenant_id` as the shard key can keep that tenant's data together.

This can make tenant-specific queries and operations simpler because the router can send them to one shard.

However, the design has a limitation.

Suppose the platform has 10,000 small tenants and one very large tenant that generates a substantial share of the workload.

If all records for that large tenant must live on one shard, that shard can become overloaded.

This is known as a **hot shard**.

Possible responses include:

- Giving the large tenant a dedicated shard.
- Using a more granular placement strategy for large tenants.
- Introducing a composite key or a second-level partitioning strategy.
- Separating particularly expensive workloads from the main tenant data.

Each option introduces trade-offs. For example, splitting one tenant across multiple shards can improve capacity but make tenant-wide queries and transactions more complicated.

Tenant-based sharding is useful when tenant isolation and tenant-scoped queries are important, but it requires a plan for tenants with very different sizes or traffic levels.

## 6. Example: Sharding by Region

Consider a service that stores customer data in India, Europe, and North America.

A region-based strategy might place the records as follows:

```text
Shard 1: India
Shard 2: Europe
Shard 3: North America
```

This can be useful when regional access, latency, or data residency requirements influence where data must be stored.

However, regional populations and workloads can differ significantly.

If India generates most of the requests, its shard may become overloaded while the other shards remain lightly used.

Region-based placement also becomes difficult when a region needs more capacity than one shard can provide.

A practical design may use region as a placement boundary and then distribute data within each region using another key.

**Important:** Data residency requirements can dictate placement constraints, but they do not guarantee balanced workloads. Those constraints must be designed into the sharding architecture.

## 7. What Is a Hotspot?

A hotspot occurs when a shard receives a disproportionate amount of traffic or stores a disproportionately large share of the data.

Consider three shards:

```text
Shard 1: 80% of requests
Shard 2: 12% of requests
Shard 3:  8% of requests
```

Even if all three shards have similar storage capacity, Shard 1 may reach its limits first.

Adding a fourth shard will not automatically fix the problem if the routing rule continues sending most requests to Shard 1.

Hotspots can arise from:

- Uneven tenant sizes.
- Popular users or accounts.
- Sequential keys combined with range-based partitioning.
- Low-cardinality shard keys.
- Traffic concentrated around a small set of records.
- Skewed read or write patterns.

Hash-based distribution can help spread distinct keys, but it cannot guarantee balanced traffic when one key is much more popular than the others.

For example, hashing a popular tenant's ID still sends that tenant to one shard if the tenant is indivisible under the placement strategy.

Solving that case may require splitting the tenant's workload or using a more granular key.

## 8. Data Distribution vs. Query Distribution

These two concepts should be measured separately.

### Data distribution

How many records or how much storage does each shard contain?

Example:

```text
Shard 1: 34% of records
Shard 2: 33% of records
Shard 3: 33% of records
```

### Query distribution

How much work does each shard receive?

Example:

```text
Shard 1: 70% of requests
Shard 2: 20% of requests
Shard 3: 10% of requests
```

The records are distributed relatively evenly, but the request load is not.

A production system should examine metrics such as:

- Records and storage per shard.
- Read and write requests per shard.
- Query latency per shard.
- CPU, memory, and disk utilization per shard.
- Lock waits and connection pressure.
- The frequency of requests that touch multiple shards.

For this educational repository, we will start by measuring record distribution and key movement. Later examples can use simple request counts to illustrate traffic skew.

## 9. What Happens When a Shard Key Changes?

Changing the shard key after the system has accumulated a large dataset can be expensive.

Suppose the system initially distributes users by `user_id`, but the team later decides to distribute records by `tenant_id`.

The existing records are placed according to the original key. The new strategy may assign them to different shards.

A migration could require:

1. Calculating the new destination for each record.
2. Copying records to their new locations.
3. Handling reads and writes during the migration.
4. Updating routing information.
5. Verifying that records were copied correctly.
6. Retiring the old placement after it is safe to do so.

A real migration must also consider duplicate writes, concurrent updates, failure recovery, consistency, and rollback.

Our repository will not implement a safe online migration protocol. It will demonstrate the simpler question of how record assignments change under different sharding strategies.

This is one reason to evaluate the shard key carefully before deploying a sharded system.

## 10. How We Will Evaluate Shard Keys in Python

We will use a small simulation with multiple candidate keys and a configurable number of shards.

The simulation will focus on three questions:

1. How many records are assigned to each shard?
2. Does the chosen key produce an obvious distribution imbalance?
3. Can the application determine the shard for a given key?

A distribution report might look like this:

```text
Shard distribution

Shard 0: 340 records
Shard 1: 325 records
Shard 2: 335 records

Total records: 1,000
```

The numbers above are illustrative, not measured output from an implementation.

We will then compare that result with an intentionally skewed dataset.

The purpose is to see how the distribution changes when the input data changes, rather than assuming that a particular shard key is always balanced.

### Important implementation detail

Python's built-in `hash()` is not suitable when shard assignments must remain stable across separate process runs for string keys. Python normally randomizes string hashing between processes.

For deterministic placement, our implementations will use a stable hashing function where appropriate.

For simple integer examples, modulo arithmetic may be sufficient to explain the underlying idea. We will keep that distinction clear in the code.

## 11. Practical Guidelines

Before selecting a shard key for a real application, answer these questions:

- Which fields are available in the most common reads and writes?
- Can a typical request be routed to one shard?
- How many distinct key values exist?
- Are some values significantly more common than others?
- Are records and traffic distributed evenly?
- Can a single tenant or account overload one shard?
- Does the application need global uniqueness or cross-shard transactions?
- How will the system handle growth, migration, and rebalancing?
- Are there regional or regulatory placement constraints?

A good shard key balances query efficiency with distribution and operational requirements.

There is usually no choice that optimizes every query. The goal is to make the dominant workload efficient without creating unacceptable hotspots or coordination costs.

## 12. Key Takeaways

- The shard key determines how records are assigned to shards.
- High cardinality helps, but it does not guarantee balanced data or traffic.
- A shard key should fit the application's common query patterns.
- Tenant-based and region-based sharding can simplify certain access patterns while creating hotspots.
- Data distribution and request distribution must be measured separately.
- Changing a shard key after deployment can require substantial data migration.
- Stable hashing is important when the same key must map to the same shard across application restarts.

In the next document, we will compare the major sharding strategies and establish when range-based sharding, modulo hashing, or consistent hashing makes sense.
