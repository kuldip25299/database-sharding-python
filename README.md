# Database Sharding with Python

Learn database sharding through small, runnable Python simulations. This repository starts with the problem of a single database becoming a bottleneck, then explores shard key selection, modulo hashing, consistent hashing, query routing, and data rebalancing.

The goal is to understand how sharding works, what changes when the number of shards changes, and which trade-offs show up when data is distributed across multiple database nodes.

## Why this repository?

A single database can serve an application well for a long time. As traffic and data grow, scaling the database vertically may become expensive or reach practical limits. Sharding distributes records across multiple database nodes so that storage and request load can be spread out.

Sharding also introduces complexity. The application needs a reliable way to find the right shard, shard keys can create uneven load, and operations that touch multiple shards are harder to execute.

This repository demonstrates those ideas with simple Python code before introducing the operational complexity of a real distributed database.

## What you will learn

- Why applications consider sharding and when it may be unnecessary.
- The difference between vertical scaling and horizontal partitioning.
- How shard key selection affects distribution and query patterns.
- How modulo hashing assigns keys to shards.
- Why changing the shard count can move many keys with modulo hashing.
- How consistent hashing and virtual nodes can reduce redistribution.
- How a query router selects the target shard.
- How to simulate data movement when shards are added or removed.
- Why cross-shard queries and transactions require additional design.

## Repository structure

```text
database-sharding-python/
├── README.md
├── requirements.txt
├── docs/
│   ├── 01_business_problem.md
│   ├── 02_what_is_database_sharding.md
│   ├── 03_vertical_vs_horizontal_scaling.md
│   ├── 04_shard_key_selection.md
│   ├── 05_sharding_strategies.md
│   ├── 06_modulo_sharding.md
│   ├── 07_consistent_hashing_for_sharding.md
│   ├── 08_query_routing.md
│   ├── 09_data_rebalancing.md
│   ├── 10_cross_shard_queries_and_transactions.md
│   └── 11_production_tradeoffs.md
└── examples/
    ├── 01_single_database.py
    ├── 02_naive_sharding.py
    ├── 03_modulo_sharding.py
    ├── 04_shard_key_distribution.py
    ├── 05_consistent_hashing_sharding.py
    ├── 06_query_router.py
    ├── 07_data_rebalancing.py
    ├── 08_cross_shard_query.py
    └── test_sharding.py
```

## Learning path

Follow the docs and examples in order. Each stage builds on the previous one.

| Stage | Topics | What you will build or understand |
|---|---|---|
| 1. The problem | Business problem, sharding basics, vertical vs. horizontal scaling | Why one database can become a bottleneck and what sharding changes |
| 2. Shard key design | Shard keys and common sharding strategies | How key choice affects data distribution and query routing |
| 3. Modulo hashing | Hashing a key and selecting a shard | A basic, deterministic shard assignment strategy |
| 4. Consistent hashing | Hash ring and virtual nodes | Why consistent hashing can reduce key movement when membership changes |
| 5. Query routing | Mapping requests to shards | A simple router for reads and writes |
| 6. Rebalancing | Adding/removing shards and moving keys | How data placement changes when the shard layout changes |
| 7. Cross-shard operations | Queries and transaction trade-offs | Why operations spanning multiple shards are more complicated |
| 8. Production trade-offs | Hotspots, consistency, failure handling, and operational costs | What a simulation does not solve for a real deployment |

## Requirements

- Python 3.11 or newer
- `pip`
- `pytest` for running the test suite

The core examples use Python's standard library and in-memory data structures. No database server, Redis, Docker, or cloud account is required.

## Setup

Clone the repository and enter the project directory:

```bash
git clone https://github.com/<your-github-username>/database-sharding-python.git
cd database-sharding-python
```

Create and activate a virtual environment.

**macOS / Linux**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

**Windows PowerShell**

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
```

Install the test dependency:

```bash
pip install -r requirements.txt
```

Replace `<your-github-username>` in the clone URL with the GitHub account that owns the repository.

## Running the examples

Run an example from the repository root. For example:

```bash
python examples/01_single_database.py
python examples/02_naive_sharding.py
python examples/03_modulo_sharding.py
python examples/04_shard_key_distribution.py
python examples/05_consistent_hashing_sharding.py
python examples/06_query_router.py
python examples/07_data_rebalancing.py
python examples/08_cross_shard_query.py
```

The examples are designed to run independently. Each file will demonstrate one concept and print useful output so you can inspect the behavior without setting up external services.

Run the tests from the repository root:

```bash
pytest -q
```

These commands describe the planned repository interface. They will work once the corresponding example and test files have been added.

## Modulo hashing vs. consistent hashing

Modulo hashing is simple: hash a key and take the remainder after dividing by the number of shards. The downside is that changing the shard count changes the mapping for many keys.

Consistent hashing places shard identifiers and keys on a logical hash ring. When a shard is added or removed, only a portion of keys should need a new assignment. Virtual nodes can improve distribution, though they add implementation details and do not eliminate every imbalance.

We will measure key movement in the examples rather than assuming one strategy is always better.

## Important limitations

This repository is an educational simulation, not a distributed database implementation.

- Each shard is represented by an in-memory data structure; data is lost when the process exits.
- The examples do not provide replication, durability, failover, or concurrent-write coordination.
- Query routing and rebalancing are simplified demonstrations, not safe online migration protocols.
- Cross-shard examples illustrate query complexity; they do not implement distributed transactions or guarantee atomicity.
- Hashing can help distribute keys, but it cannot fix a poor shard key, skewed traffic, or every hotspot.

A real system also needs decisions about consistency, schema changes, backups, shard discovery, migrations, observability, and recovery. Those concerns depend on the database technology and workload.

## Who is this for?

Developers who want to understand database sharding through code, and engineers evaluating the trade-offs of distributing application data across multiple database nodes.

You do not need a distributed database running locally to follow the examples.

## Contributing

Suggestions, corrections, and practical examples are welcome. If you find a bug or think a trade-off needs a clearer explanation, open an issue or submit a pull request.

When suggesting an implementation, explain the workload it is intended to support and the trade-offs it introduces.

## License

No license has been selected for this repository yet. Add a license before explicitly permitting reuse of the code.
