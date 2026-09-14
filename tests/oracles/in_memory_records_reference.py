"""Reference implementation of the In-Memory Records specification (dev only)."""

from __future__ import annotations


_ARITY = {
    "SET": 3,
    "GET": 2,
    "DELETE": 2,
    "SCAN": 1,
    "SCAN_BY_PREFIX": 2,
    "SET_AT": 4,
    "SET_AT_WITH_TTL": 5,
    "GET_AT": 3,
    "DELETE_AT": 3,
    "SCAN_AT": 2,
    "SCAN_BY_PREFIX_AT": 3,
    "BACKUP": 1,
    "RESTORE": 2,
}


class _Store:
    def __init__(self) -> None:
        # record -> field -> (value, expiry or None)
        self.records: dict[str, dict[str, tuple[str, int | None]]] = {}
        # (timestamp, record -> field -> (value, remaining or None))
        self.backups: list[tuple[int, dict[str, dict[str, tuple[str, int | None]]]]] = []

    def _live_fields(self, record: str, now: int | None) -> dict[str, tuple[str, int | None]]:
        fields = self.records.get(record, {})
        if now is None:
            return fields
        live = {
            name: (value, expiry)
            for name, (value, expiry) in fields.items()
            if expiry is None or now < expiry  # EXPIRY_RULE
        }
        if live:
            self.records[record] = live
        else:
            self.records.pop(record, None)
        return live

    def set(self, now: int | None, record: str, field: str, value: str, ttl: int | None) -> str:
        live = self._live_fields(record, now)
        created = not live
        expiry = None if ttl is None else now + ttl
        self.records.setdefault(record, {})[field] = (value, expiry)
        return "true" if created else "false"

    def get(self, now: int | None, record: str, field: str) -> str:
        entry = self._live_fields(record, now).get(field)
        return "" if entry is None else entry[0]

    def delete(self, now: int | None, record: str, field: str) -> str:
        live = self._live_fields(record, now)
        if field not in live:
            return "false"
        del self.records[record][field]
        if not self.records[record]:
            del self.records[record]
        return "true"

    def scan(self, now: int | None, record: str, prefix: str = "") -> str:
        live = self._live_fields(record, now)
        names = sorted(name for name in live if name.startswith(prefix))  # SCAN_ORDER
        return ", ".join(f"{name}({live[name][0]})" for name in names)

    def backup(self, now: int) -> str:
        snapshot: dict[str, dict[str, tuple[str, int | None]]] = {}
        for record in list(self.records):
            live = self._live_fields(record, now)
            if live:
                snapshot[record] = {
                    name: (value, None if expiry is None else expiry - now)
                    for name, (value, expiry) in live.items()
                }
        self.backups.append((now, snapshot))
        return str(len(snapshot))

    def restore(self, now: int, at: int) -> str:
        chosen = None
        for taken_at, snapshot in self.backups:
            if taken_at <= at:
                chosen = snapshot
        if chosen is None:
            return "false"
        self.records = {
            record: {
                name: (value, None if remaining is None else now + remaining)  # RESTORE_REBASE
                for name, (value, remaining) in fields.items()
            }
            for record, fields in chosen.items()
        }
        return "true"


def _int(value: str) -> int:
    if not value.isdigit():
        raise ValueError(f"expected a non-negative integer: {value}")
    return int(value)


def simulate(queries: list[list[str]]) -> list[str]:
    store = _Store()
    outputs: list[str] = []
    for query in queries:
        if not query or query[0] not in _ARITY:
            raise ValueError(f"unknown operation: {query[:1]}")
        name, arguments = query[0], query[1:]
        if len(arguments) != _ARITY[name]:
            raise ValueError(f"wrong argument count for {name}")
        if name == "SET":
            outputs.append(store.set(None, arguments[0], arguments[1], arguments[2], None))
        elif name == "GET":
            outputs.append(store.get(None, arguments[0], arguments[1]))
        elif name == "DELETE":
            outputs.append(store.delete(None, arguments[0], arguments[1]))
        elif name == "SCAN":
            outputs.append(store.scan(None, arguments[0]))
        elif name == "SCAN_BY_PREFIX":
            outputs.append(store.scan(None, arguments[0], arguments[1]))
        elif name == "SET_AT":
            outputs.append(store.set(_int(arguments[0]), arguments[1], arguments[2], arguments[3], None))
        elif name == "SET_AT_WITH_TTL":
            outputs.append(
                store.set(_int(arguments[0]), arguments[1], arguments[2], arguments[3], _int(arguments[4]))
            )
        elif name == "GET_AT":
            outputs.append(store.get(_int(arguments[0]), arguments[1], arguments[2]))
        elif name == "DELETE_AT":
            outputs.append(store.delete(_int(arguments[0]), arguments[1], arguments[2]))
        elif name == "SCAN_AT":
            outputs.append(store.scan(_int(arguments[0]), arguments[1]))
        elif name == "SCAN_BY_PREFIX_AT":
            outputs.append(store.scan(_int(arguments[0]), arguments[1], arguments[2]))
        elif name == "BACKUP":
            outputs.append(store.backup(_int(arguments[0])))
        else:
            outputs.append(store.restore(_int(arguments[0]), _int(arguments[1])))
    return outputs
