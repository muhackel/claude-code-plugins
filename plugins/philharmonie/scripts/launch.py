import os
import sys


def main():
    barrier = int(sys.argv[1])
    permit = os.read(barrier, 1)
    os.close(barrier)
    if permit != b"1":
        return 125
    os.execvpe(sys.argv[2], sys.argv[2:], os.environ)


if __name__ == "__main__":
    sys.exit(main())
