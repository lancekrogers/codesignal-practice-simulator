from datetime import datetime, timedelta


def simulate_coding_framework(operations):
    # Each value is (size, expiration). None means no expiration.
    files = {}
    result = []

    def is_alive(name, now=None):
        if name not in files:
            return False

        expiration = files[name][1]
        return expiration is None or now is None or now < expiration

    def find_files(prefix, now=None):
        matches = []

        for name in files:
            if name.startswith(prefix) and is_alive(name, now):
                matches.append(name)

        matches.sort(key=lambda name: (-files[name][0], name))
        return matches[:10]

    for operation in operations:
        command = operation[0]

        if command == "FILE_UPLOAD":
            name = operation[1]
            size = int(operation[2][:-2])

            if is_alive(name):
                raise RuntimeError("file already exists")

            files[name] = (size, None)
            result.append(f"uploaded {name}")

        elif command == "FILE_GET":
            name = operation[1]

            if is_alive(name):
                result.append(f"got {name}")
            else:
                result.append("file not found")

        elif command == "FILE_COPY":
            source = operation[1]
            destination = operation[2]

            if not is_alive(source):
                raise RuntimeError("source file does not exist")

            files[destination] = files[source]
            result.append(f"copied {source} to {destination}")

        elif command == "FILE_SEARCH":
            matches = find_files(operation[1])
            result.append(f"found [{', '.join(matches)}]")

        elif command == "FILE_UPLOAD_AT":
            now = datetime.fromisoformat(operation[1])
            name = operation[2]
            size = int(operation[3][:-2])

            if is_alive(name, now):
                raise RuntimeError("file already exists")

            expiration = None
            if len(operation) == 5:
                ttl = int(operation[4])
                expiration = now + timedelta(seconds=ttl)

            files[name] = (size, expiration)
            result.append(f"uploaded at {name}")

        elif command == "FILE_GET_AT":
            now = datetime.fromisoformat(operation[1])
            name = operation[2]

            if is_alive(name, now):
                result.append(f"got at {name}")
            else:
                result.append("file not found")

        elif command == "FILE_COPY_AT":
            now = datetime.fromisoformat(operation[1])
            source = operation[2]
            destination = operation[3]

            if not is_alive(source, now):
                raise RuntimeError("source file does not exist")

            files[destination] = files[source]
            result.append(f"copied at {source} to {destination}")

        elif command == "FILE_SEARCH_AT":
            now = datetime.fromisoformat(operation[1])
            matches = find_files(operation[2], now)
            result.append(f"found at [{', '.join(matches)}]")

    return result
