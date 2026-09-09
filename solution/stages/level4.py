"""Level 4: save copies of the file dictionary for rollback."""

from datetime import datetime, timedelta


def simulate_coding_framework(operations):
    # name -> (size, expiration time)
    files = {}
    history = []
    answer = []

    def alive(name, now=None):
        if name not in files:
            return False
        expires = files[name][1]
        return expires is None or now is None or now < expires

    def search(prefix, now=None):
        matches = [
            name
            for name in files
            if name.startswith(prefix) and alive(name, now)
        ]
        matches.sort(key=lambda name: (-files[name][0], name))
        return matches[:10]

    for operation in operations:
        command = operation[0]

        if command == "FILE_UPLOAD":
            name, size = operation[1], operation[2]
            if alive(name):
                raise RuntimeError("file already exists")
            files[name] = (int(size[:-2]), None)
            answer.append(f"uploaded {name}")

        elif command == "FILE_GET":
            name = operation[1]
            answer.append(f"got {name}" if alive(name) else "file not found")

        elif command == "FILE_COPY":
            source, destination = operation[1], operation[2]
            if not alive(source):
                raise RuntimeError("source file does not exist")
            files[destination] = files[source]
            answer.append(f"copied {source} to {destination}")

        elif command == "FILE_SEARCH":
            matches = search(operation[1])
            answer.append(f"found [{', '.join(matches)}]")

        elif command == "FILE_UPLOAD_AT":
            now = datetime.fromisoformat(operation[1])
            name, size = operation[2], operation[3]
            if alive(name, now):
                raise RuntimeError("file already exists")

            expires = None
            if len(operation) == 5:
                expires = now + timedelta(seconds=int(operation[4]))

            files[name] = (int(size[:-2]), expires)
            history.append((now, files.copy()))
            answer.append(f"uploaded at {name}")

        elif command == "FILE_GET_AT":
            now = datetime.fromisoformat(operation[1])
            name = operation[2]
            answer.append(f"got at {name}" if alive(name, now) else "file not found")

        elif command == "FILE_COPY_AT":
            now = datetime.fromisoformat(operation[1])
            source, destination = operation[2], operation[3]
            if not alive(source, now):
                raise RuntimeError("source file does not exist")
            files[destination] = files[source]
            history.append((now, files.copy()))
            answer.append(f"copied at {source} to {destination}")

        elif command == "FILE_SEARCH_AT":
            now = datetime.fromisoformat(operation[1])
            matches = search(operation[2], now)
            answer.append(f"found at [{', '.join(matches)}]")

        elif command == "ROLLBACK":
            target = datetime.fromisoformat(operation[1])
            files = {}
            kept_history = []

            # Operations in the assessment arrive in timestamp order, so the
            # last snapshot we keep is the state at the rollback time.
            for timestamp, snapshot in history:
                if timestamp <= target:
                    files = snapshot.copy()
                    kept_history.append((timestamp, snapshot))

            history = kept_history
            answer.append(f"rollback to {operation[1]}")

    return answer
