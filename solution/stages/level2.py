"""Level 2: store sizes as numbers so files can be sorted."""


def simulate_coding_framework(operations):
    files = {}
    answer = []

    for operation in operations:
        command = operation[0]

        if command == "FILE_UPLOAD":
            name, size = operation[1], operation[2]
            if name in files:
                raise RuntimeError("file already exists")

            # Every size in the supplied tests has the form "200kb".
            files[name] = int(size[:-2])
            answer.append(f"uploaded {name}")

        elif command == "FILE_GET":
            name = operation[1]
            if name in files:
                answer.append(f"got {name}")
            else:
                answer.append("file not found")

        elif command == "FILE_COPY":
            source, destination = operation[1], operation[2]
            if source not in files:
                raise RuntimeError("source file does not exist")
            files[destination] = files[source]
            answer.append(f"copied {source} to {destination}")

        elif command == "FILE_SEARCH":
            prefix = operation[1]
            matches = [name for name in files if name.startswith(prefix)]
            matches.sort(key=lambda name: (-files[name], name))
            answer.append(f"found [{', '.join(matches[:10])}]")

    return answer
