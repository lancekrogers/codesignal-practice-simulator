def simulate_coding_framework(operations):
    files = {}
    result = []

    for operation in operations:
        command = operation[0]

        if command == "FILE_UPLOAD":
            name = operation[1]
            size = operation[2]

            if name in files:
                raise RuntimeError("file already exists")

            files[name] = int(size[:-2])
            result.append(f"uploaded {name}")

        elif command == "FILE_GET":
            name = operation[1]

            if name in files:
                result.append(f"got {name}")
            else:
                result.append("file not found")

        elif command == "FILE_COPY":
            source = operation[1]
            destination = operation[2]

            if source not in files:
                raise RuntimeError("source file does not exist")

            files[destination] = files[source]
            result.append(f"copied {source} to {destination}")

        elif command == "FILE_SEARCH":
            prefix = operation[1]
            matches = []

            for name in files:
                if name.startswith(prefix):
                    matches.append(name)

            matches.sort(key=lambda name: (-files[name], name))
            result.append(f"found [{', '.join(matches[:10])}]")

    return result
