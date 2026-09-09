"""Level 1: use a dictionary to store file names and sizes."""


def simulate_coding_framework(operations):
    files = {}
    answer = []

    for operation in operations:
        command = operation[0]

        if command == "FILE_UPLOAD":
            name, size = operation[1], operation[2]
            if name in files:
                raise RuntimeError("file already exists")
            files[name] = size
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

    return answer
