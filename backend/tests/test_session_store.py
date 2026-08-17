import time

import pytest

from backend.session_store import SessionStore


def test_create_returns_unique_ids():
    store = SessionStore()
    id1 = store.create()
    id2 = store.create()
    assert id1 != id2


def test_get_missing_session_raises_keyerror():
    store = SessionStore()
    with pytest.raises(KeyError):
        store.get("nonexistent")


def test_update_then_get_returns_fields():
    store = SessionStore()
    sid = store.create()
    store.update(sid, foo="bar")
    assert store.get(sid) == {"foo": "bar"}


def test_expired_session_raises_keyerror():
    store = SessionStore(ttl_seconds=0.05)
    sid = store.create()
    time.sleep(0.1)
    with pytest.raises(KeyError):
        store.get(sid)


def test_delete_removes_session():
    store = SessionStore()
    sid = store.create()
    store.delete(sid)
    with pytest.raises(KeyError):
        store.get(sid)
