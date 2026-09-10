"""Descriptor-bound failure-artifact operations.

The caller passes the already-open output-root descriptor as fd 3. Every
operation below uses dir_fd-relative syscalls; no artifact pathname is
reopened after validation.
"""

import argparse
import json
import os
import stat
import subprocess
import sys


DIRECTORY_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
FILE_FLAGS = os.O_RDWR | os.O_NOFOLLOW
MAX_ARTIFACT_BYTES = 32 * 1024 * 1024
MAX_OUTPUT_COMPONENTS = 128
MAX_TREE_DEPTH = 32
MAX_TREE_ENTRIES = 1024
SANITIZER_FAILURE = 10
OPERATION_FAILURE = 11


def main():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--operation", required=True)
    parser.add_argument("--components", required=True)
    parser.add_argument("--node")
    parser.add_argument("--sanitizer")
    args = parser.parse_args()

    components = json.loads(args.components)
    if (
        not isinstance(components, list)
        or len(components) > MAX_OUTPUT_COMPONENTS
        or (
            args.operation not in ("cleanup", "sanitize-tree")
            and not components
        )
        or any(
            not isinstance(component, str)
            or not component
            or component in (".", "..")
            or "/" in component
            for component in components
        )
    ):
        return OPERATION_FAILURE

    root_fd = 3
    try:
        root_stat = os.fstat(root_fd)
        if not stat.S_ISDIR(root_stat.st_mode):
            return OPERATION_FAILURE
        if args.operation == "prepare-root":
            return prepare_root(root_fd, components)
        if args.operation == "sanitize":
            return sanitize(root_fd, components, args.node, args.sanitizer)
        if args.operation == "sanitize-tree":
            return sanitize_tree(root_fd, args.node, args.sanitizer)
        if args.operation == "create":
            return create(root_fd, components)
        if args.operation == "unlink":
            return unlink(root_fd, components)
        if args.operation == "cleanup":
            return cleanup(root_fd)
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return OPERATION_FAILURE
    return OPERATION_FAILURE


def prepare_root(root_fd, components):
    directory_fd = os.dup(root_fd)
    try:
        for component in components:
            try:
                next_fd = os.open(component, DIRECTORY_FLAGS, dir_fd=directory_fd)
            except FileNotFoundError:
                os.mkdir(component, 0o700, dir_fd=directory_fd)
                next_fd = os.open(component, DIRECTORY_FLAGS, dir_fd=directory_fd)
            os.close(directory_fd)
            directory_fd = next_fd
        root_stat = os.fstat(directory_fd)
        sys.stdout.write(json.dumps({
            "device": str(root_stat.st_dev),
            "inode": str(root_stat.st_ino),
        }))
        return 0
    finally:
        os.close(directory_fd)


def open_parent(root_fd, components):
    parent_fd = os.dup(root_fd)
    try:
        for component in components[:-1]:
            try:
                next_fd = os.open(component, DIRECTORY_FLAGS, dir_fd=parent_fd)
            except OSError:
                unlink_symlink(parent_fd, component)
                raise
            os.close(parent_fd)
            parent_fd = next_fd
        return parent_fd
    except Exception:
        os.close(parent_fd)
        raise


def sanitize(root_fd, components, node, sanitizer):
    if not node or not sanitizer:
        return OPERATION_FAILURE
    try:
        parent_fd = open_parent(root_fd, components)
    except OSError:
        return SANITIZER_FAILURE

    file_fd = None
    try:
        try:
            file_fd = os.open(components[-1], FILE_FLAGS, dir_fd=parent_fd)
            file_stat = os.fstat(file_fd)
            if not stat.S_ISREG(file_stat.st_mode):
                raise OSError("artifact is not a regular file")
            if file_stat.st_size < 0 or file_stat.st_size > MAX_ARTIFACT_BYTES:
                raise OSError("artifact exceeds its read limit")
        except OSError:
            unlink_entry(parent_fd, components[-1])
            return SANITIZER_FAILURE

        child = subprocess.run(
            [node, sanitizer, str(file_fd)],
            env=os.environ.copy(),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            pass_fds=(file_fd,),
            check=False,
        )
        if child.returncode == 0:
            return 0
        redact_fd(file_fd)
        return SANITIZER_FAILURE
    except (OSError, ValueError):
        if file_fd is not None:
            try:
                redact_fd(file_fd)
            except OSError:
                return OPERATION_FAILURE
        return OPERATION_FAILURE
    finally:
        if file_fd is not None:
            os.close(file_fd)
        os.close(parent_fd)


def create(root_fd, components):
    if len(components) != 1:
        return OPERATION_FAILURE
    name = components[0]
    file_fd = None
    try:
        file_fd = os.open(
            name,
            FILE_FLAGS | os.O_CREAT | os.O_EXCL,
            0o600,
            dir_fd=root_fd,
        )
        data = sys.stdin.buffer.read(MAX_ARTIFACT_BYTES + 1)
        if len(data) > MAX_ARTIFACT_BYTES:
            raise OSError("generated artifact exceeds its write limit")
        write_all(file_fd, data)
        return 0
    except (OSError, ValueError):
        cleanup_succeeded = True
        if file_fd is not None:
            try:
                os.unlink(name, dir_fd=root_fd)
            except OSError:
                cleanup_succeeded = False
        return SANITIZER_FAILURE if cleanup_succeeded else OPERATION_FAILURE
    finally:
        if file_fd is not None:
            try:
                os.close(file_fd)
            except OSError:
                pass


def unlink(root_fd, components):
    if len(components) != 1:
        return OPERATION_FAILURE
    try:
        os.unlink(components[0], dir_fd=root_fd)
        return 0
    except OSError:
        return OPERATION_FAILURE


def sanitize_tree(root_fd, node, sanitizer, state=None, depth=0):
    if not node or not sanitizer:
        return OPERATION_FAILURE
    if depth > MAX_TREE_DEPTH:
        return OPERATION_FAILURE
    if state is None:
        state = [0]
    try:
        names = os.listdir(root_fd)
    except OSError:
        return OPERATION_FAILURE

    complete = True
    for name in names:
        state[0] += 1
        if state[0] > MAX_TREE_ENTRIES:
            return OPERATION_FAILURE
        directory_fd = None
        try:
            directory_fd = os.open(name, DIRECTORY_FLAGS, dir_fd=root_fd)
        except OSError:
            if not sanitize_tree_file(root_fd, name, node, sanitizer):
                complete = False
            continue
        try:
            if sanitize_tree(
                directory_fd,
                node,
                sanitizer,
                state,
                depth + 1,
            ) != 0:
                complete = False
        finally:
            os.close(directory_fd)
    return 0 if complete else OPERATION_FAILURE


def sanitize_tree_file(parent_fd, name, node, sanitizer):
    file_fd = None
    try:
        file_fd = os.open(name, FILE_FLAGS, dir_fd=parent_fd)
        if not stat.S_ISREG(os.fstat(file_fd).st_mode):
            raise OSError("artifact is not a regular file")
    except OSError:
        if file_fd is not None:
            os.close(file_fd)
        try:
            os.unlink(name, dir_fd=parent_fd)
            return True
        except OSError:
            return False

    try:
        kind = (
            "trace" if name.lower().endswith(".zip")
            else "screenshot" if name.lower().endswith(".png")
            else "redact"
        )
        child = subprocess.run(
            [node, sanitizer, str(file_fd)],
            env={
                **os.environ,
                "FAILURE_ARTIFACT_KIND": kind,
            },
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            pass_fds=(file_fd,),
            check=False,
        )
        if child.returncode != 0:
            redact_fd(file_fd)
        return True
    except (OSError, ValueError):
        try:
            redact_fd(file_fd)
            return True
        except OSError:
            return False
    finally:
        os.close(file_fd)


def cleanup(root_fd):
    complete = True
    try:
        os.fchmod(root_fd, 0o700)
    except OSError:
        complete = False
    try:
        names = os.listdir(root_fd)
    except OSError:
        return OPERATION_FAILURE
    for name in names:
        if not cleanup_entry(root_fd, name):
            complete = False
    return 0 if complete else OPERATION_FAILURE


def cleanup_entry(parent_fd, name):
    child_fd = None
    try:
        child_fd = os.open(name, DIRECTORY_FLAGS, dir_fd=parent_fd)
    except OSError:
        try:
            os.unlink(name, dir_fd=parent_fd)
            return True
        except OSError:
            return False
    try:
        complete = cleanup(child_fd) == 0
    finally:
        os.close(child_fd)
    try:
        os.rmdir(name, dir_fd=parent_fd)
    except OSError:
        try:
            os.unlink(name, dir_fd=parent_fd)
        except OSError:
            complete = False
    return complete


def unlink_symlink(parent_fd, name):
    try:
        entry_stat = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
        if stat.S_ISLNK(entry_stat.st_mode):
            os.unlink(name, dir_fd=parent_fd)
    except OSError:
        pass


def unlink_entry(parent_fd, name):
    try:
        os.unlink(name, dir_fd=parent_fd)
    except OSError:
        raise


def redact_fd(file_fd):
    os.ftruncate(file_fd, 0)
    write_all(file_fd, b"[REDACTED]\n")


def write_all(file_fd, data):
    offset = 0
    while offset < len(data):
        written = os.write(file_fd, data[offset:])
        if written <= 0:
            raise OSError("artifact write made no progress")
        offset += written


if __name__ == "__main__":
    sys.exit(main())
