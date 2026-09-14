"""Reference implementation of the Account Ledger specification (dev only)."""

from __future__ import annotations


_ARITY = {
    "CREATE_ACCOUNT": 2,
    "DEPOSIT": 3,
    "TRANSFER": 4,
    "TOP_OUTGOING": 2,
    "SCHEDULE_TRANSFER": 5,
    "CANCEL_TRANSFER": 3,
    "GET_SCHEDULE_STATUS": 3,
    "BALANCE_AT": 3,
    "CLOSE_ACCOUNT": 3,
}


class _Account:
    def __init__(self, created_at: int) -> None:
        self.balance = 0
        self.outgoing = 0
        self.created_at = created_at
        self.closed_at: int | None = None
        self.history: list[tuple[int, int]] = [(created_at, 0)]

    def change(self, at: int, delta: int) -> None:
        self.balance += delta
        if self.history and self.history[-1][0] == at:
            self.history[-1] = (at, self.balance)
        else:
            self.history.append((at, self.balance))


class _Schedule:
    def __init__(self, number: int, source: str, target: str, amount: int, execute_at: int) -> None:
        self.id = f"schedule{number}"
        self.number = number
        self.source = source
        self.target = target
        self.amount = amount
        self.execute_at = execute_at
        self.status = "PENDING"


class _Ledger:
    def __init__(self) -> None:
        self.accounts: dict[str, _Account] = {}
        self.closed: list[_Account] = []  # kept for BALANCE_AT history
        self.closed_ids: dict[str, list[_Account]] = {}
        self.schedules: list[_Schedule] = []
        self.next_schedule = 1

    # -- time -------------------------------------------------------------

    def advance(self, now: int) -> None:
        due = sorted(
            (schedule for schedule in self.schedules if schedule.status == "PENDING" and schedule.execute_at <= now),  # SCHEDULE_DUE
            key=lambda schedule: (schedule.execute_at, schedule.number),
        )
        for schedule in due:
            source = self.accounts.get(schedule.source)
            target = self.accounts.get(schedule.target)
            if source is None or target is None or source.balance < schedule.amount:
                schedule.status = "FAILED"
                continue
            self._move(schedule.execute_at, source, target, schedule.amount)
            schedule.status = "EXECUTED"

    def _move(self, at: int, source: _Account, target: _Account, amount: int) -> None:
        source.change(at, -amount)
        source.outgoing += amount
        target.change(at, amount)

    # -- level 1 ----------------------------------------------------------

    def create(self, now: int, account: str) -> str:
        if account in self.accounts:
            return "false"
        self.accounts[account] = _Account(now)
        return "true"

    def deposit(self, now: int, account: str, amount: int) -> str:
        record = self.accounts.get(account)
        if record is None or amount == 0:
            return ""
        record.change(now, amount)
        return str(record.balance)

    def transfer(self, now: int, source: str, target: str, amount: int) -> str:
        from_account = self.accounts.get(source)
        to_account = self.accounts.get(target)
        if (
            from_account is None
            or to_account is None
            or source == target
            or amount == 0
            or from_account.balance < amount
        ):
            return ""
        self._move(now, from_account, to_account, amount)
        return str(from_account.balance)

    # -- level 2 ----------------------------------------------------------

    def top_outgoing(self, n: int) -> str:
        if n == 0 or not self.accounts:
            return ""
        ranked = sorted(self.accounts.items(), key=lambda item: (-item[1].outgoing, item[0]))  # RANK_KEY
        return ", ".join(f"{name}({account.outgoing})" for name, account in ranked[:n])

    # -- level 3 ----------------------------------------------------------

    def schedule(self, now: int, source: str, target: str, amount: int, execute_at: int) -> str:
        if (
            source not in self.accounts
            or target not in self.accounts
            or source == target
            or amount == 0
            or execute_at <= now
        ):
            return ""
        entry = _Schedule(self.next_schedule, source, target, amount, execute_at)
        self.next_schedule += 1
        self.schedules.append(entry)
        return entry.id

    def _owned(self, source: str, schedule_id: str) -> _Schedule | None:
        for schedule in self.schedules:
            if schedule.id == schedule_id and schedule.source == source:
                return schedule
        return None

    def cancel(self, source: str, schedule_id: str) -> str:
        schedule = self._owned(source, schedule_id)
        if schedule is None or schedule.status != "PENDING":
            return "false"
        schedule.status = "CANCELLED"
        return "true"

    def status(self, source: str, schedule_id: str) -> str:
        schedule = self._owned(source, schedule_id)
        return "" if schedule is None else schedule.status

    # -- level 4 ----------------------------------------------------------

    def balance_at(self, now: int, account: str, at: int) -> str:
        if at > now:
            return ""
        versions = [*self.closed_ids.get(account, ())]
        current = self.accounts.get(account)
        if current is not None:
            versions.append(current)
        for version in versions:
            if version.created_at <= at and (version.closed_at is None or at < version.closed_at):
                balance = None
                for changed_at, value in version.history:
                    if changed_at <= at:  # HISTORY_RULE
                        balance = value
                return "" if balance is None else str(balance)
        return ""

    def close(self, now: int, account: str, heir: str) -> str:
        closing = self.accounts.get(account)
        receiving = self.accounts.get(heir)
        if closing is None or receiving is None or account == heir:
            return ""
        if closing.balance:
            receiving.change(now, closing.balance)
            closing.change(now, -closing.balance)
        for schedule in self.schedules:
            if schedule.source == account and schedule.status == "PENDING":
                schedule.status = "CANCELLED"
        closing.closed_at = now
        self.closed_ids.setdefault(account, []).append(closing)
        del self.accounts[account]
        return str(receiving.balance)


def _int(value: str) -> int:
    if not value.isdigit():
        raise ValueError(f"expected a non-negative integer: {value}")
    return int(value)


def simulate(queries: list[list[str]]) -> list[str]:
    ledger = _Ledger()
    outputs: list[str] = []
    for query in queries:
        if not query or query[0] not in _ARITY:
            raise ValueError(f"unknown operation: {query[:1]}")
        name, arguments = query[0], query[1:]
        if len(arguments) != _ARITY[name]:
            raise ValueError(f"wrong argument count for {name}")
        now = _int(arguments[0])
        ledger.advance(now)
        if name == "CREATE_ACCOUNT":
            outputs.append(ledger.create(now, arguments[1]))
        elif name == "DEPOSIT":
            outputs.append(ledger.deposit(now, arguments[1], _int(arguments[2])))
        elif name == "TRANSFER":
            outputs.append(ledger.transfer(now, arguments[1], arguments[2], _int(arguments[3])))
        elif name == "TOP_OUTGOING":
            outputs.append(ledger.top_outgoing(_int(arguments[1])))
        elif name == "SCHEDULE_TRANSFER":
            outputs.append(
                ledger.schedule(now, arguments[1], arguments[2], _int(arguments[3]), _int(arguments[4]))
            )
        elif name == "CANCEL_TRANSFER":
            outputs.append(ledger.cancel(arguments[1], arguments[2]))
        elif name == "GET_SCHEDULE_STATUS":
            outputs.append(ledger.status(arguments[1], arguments[2]))
        elif name == "BALANCE_AT":
            outputs.append(ledger.balance_at(now, arguments[1], _int(arguments[2])))
        else:
            outputs.append(ledger.close(now, arguments[1], arguments[2]))
    return outputs
