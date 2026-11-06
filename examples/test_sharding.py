"""
Tests for the database sharding examples.

Run from the repository root:

    pytest -q

The example files use numbered filenames, so they are loaded dynamically.
"""

import importlib.util
from pathlib import Path

import pytest


EXAMPLES_DIR = Path(__file__).resolve().parent


def load_example(filename):
    """Load a Python example file whose name starts with a number."""
    file_path = EXAMPLES_DIR / filename

    spec = importlib.util.spec_from_file_location(
        filename.replace(".py", ""),
        file_path,
    )

    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load example: {filename}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    return module


single_db_module = load_example("01_single_database.py")
naive_sharding_module = load_example("02_naive_sharding.py")
modulo_sharding_module = load_example("03_modulo_sharding.py")
distribution_module = load_example("04_shard_key_distribution.py")
consistent_hashing_module = load_example("05_consistent_hashing_sharding.py")
query_router_module = load_example("06_query_router.py")
rebalancing_module = load_example("07_data_rebalancing.py")
cross_shard_module = load_example("08_cross_shard_query.py")


def test_single_database_insert_and_get():
    database = single_db_module.SingleDatabase()

    user = {
        "user_id": 101,
        "name": "Alice",
        "city": "Mumbai",
    }

    database.insert_user(user)

    result = database.get_user(101)

    assert result == user


def test_single_database_update():
    database = single_db_module.SingleDatabase()

    database.insert_user({
        "user_id": 101,
        "name": "Alice",
        "city": "Mumbai",
    })

    database.update_user(101, city="Pune")

    result = database.get_user(101)

    assert result["city"] == "Pune"


def test_single_database_delete():
    database = single_db_module.SingleDatabase()

    database.insert_user({
        "user_id": 101,
        "name": "Alice",
        "city": "Mumbai",
    })

    database.delete_user(101)

    assert database.get_user(101) is None


def test_naive_sharding_insert_and_get():
    database = naive_sharding_module.NaiveShardingDatabase(
        number_of_shards=4
    )

    user = {
        "user_id": 101,
        "name": "Alice",
        "city": "Mumbai",
    }

    database.insert_user(user)

    result = database.get_user(101)

    assert result == user


def test_naive_sharding_routes_to_expected_shard():
    database = naive_sharding_module.NaiveShardingDatabase(
        number_of_shards=4
    )

    user_id = 101
    expected_shard = user_id % 4

    actual_shard = database.get_shard_id(user_id)

    assert actual_shard == expected_shard


def test_modulo_sharding_insert_and_get():
    database = modulo_sharding_module.ModuloShardingDatabase(
        number_of_shards=4
    )

    record = {
        "user_id": 101,
        "name": "Alice",
    }

    database.insert(record)

    assert database.get(101) == record


def test_modulo_sharding_delete():
    database = modulo_sharding_module.ModuloShardingDatabase(
        number_of_shards=4
    )

    database.insert({
        "user_id": 101,
        "name": "Alice",
    })

    database.delete(101)

    assert database.get(101) is None


def test_shard_key_distribution_returns_all_records():
    """
    The distribution example should account for every input record.

    This test checks the distribution helper without assuming that
    every shard receives an equal number of records.
    """
    records = [
        {"user_id": user_id, "region": "Mumbai"}
        for user_id in range(1, 101)
    ]

    distribution = distribution_module.distribute_records(
        records,
        shard_key="user_id",
        number_of_shards=4,
    )

    assert sum(distribution.values()) == len(records)


def test_consistent_hashing_returns_a_valid_shard():
    database = consistent_hashing_module.ConsistentHashingDatabase()

    database.add_shard("shard_1")
    database.add_shard("shard_2")
    database.add_shard("shard_3")

    shard_id = database.get_shard_id("user_101")

    assert shard_id in {
        "shard_1",
        "shard_2",
        "shard_3",
    }


def test_query_router_insert_and_get():
    database = query_router_module.ShardedDatabase(
        number_of_shards=4
    )

    user = {
        "user_id": 101,
        "name": "Alice",
        "city": "Mumbai",
    }

    database.insert_user(user)

    assert database.get_user(101) == user


def test_query_router_scatter_gather():
    database = query_router_module.ShardedDatabase(
        number_of_shards=4
    )

    users = [
        {
            "user_id": 101,
            "name": "Alice",
            "city": "Mumbai",
        },
        {
            "user_id": 102,
            "name": "Bob",
            "city": "Pune",
        },
        {
            "user_id": 103,
            "name": "Charlie",
            "city": "Mumbai",
        },
    ]

    for user in users:
        database.insert_user(user)

    result = database.get_users_by_city("Mumbai")

    assert len(result) == 2
    assert all(user["city"] == "Mumbai" for user in result)


def test_rebalancing_preserves_all_records():
    database = rebalancing_module.ShardedDatabase(
        number_of_shards=3
    )

    original_records = [
        {
            "user_id": user_id,
            "name": f"User {user_id}",
        }
        for user_id in range(1, 101)
    ]

    for record in original_records:
        database.insert(record)

    database.rebalance_shards(new_number_of_shards=4)

    rebalanced_records = database.get_all_records()

    assert len(rebalanced_records) == len(original_records)

    original_by_id = {
        record["user_id"]: record
        for record in original_records
    }

    rebalanced_by_id = {
        record["user_id"]: record
        for record in rebalanced_records
    }

    assert rebalanced_by_id == original_by_id


def test_cross_shard_order_lookup():
    database = cross_shard_module.ShardedOrderDatabase(
        number_of_shards=4
    )

    database.insert_order({
        "order_id": 1,
        "user_id": 101,
        "amount": 500,
    })

    database.insert_order({
        "order_id": 2,
        "user_id": 102,
        "amount": 750,
    })

    result = database.get_orders_by_user(101)

    assert len(result) == 1
    assert result[0]["order_id"] == 1


def test_cross_shard_total_sales():
    database = cross_shard_module.ShardedOrderDatabase(
        number_of_shards=4
    )

    database.insert_order({
        "order_id": 1,
        "user_id": 101,
        "amount": 500,
    })

    database.insert_order({
        "order_id": 2,
        "user_id": 102,
        "amount": 750,
    })

    assert database.get_total_sales() == 1250


def test_cross_shard_top_orders():
    database = cross_shard_module.ShardedOrderDatabase(
        number_of_shards=4
    )

    amounts = [300, 900, 500, 1200]

    for order_id, amount in enumerate(amounts, start=1):
        database.insert_order({
            "order_id": order_id,
            "user_id": 100 + order_id,
            "amount": amount,
        })

    result = database.get_top_orders(limit=2)

    assert len(result) == 2
    assert result[0]["amount"] == 1200
    assert result[1]["amount"] == 900


def test_cross_shard_pagination():
    database = cross_shard_module.ShardedOrderDatabase(
        number_of_shards=4
    )

    for order_id in range(1, 11):
        database.insert_order({
            "order_id": order_id,
            "user_id": 100 + order_id,
            "amount": order_id * 100,
        })

    page = database.get_paginated_orders(page=1, page_size=5)

    assert len(page) == 5
