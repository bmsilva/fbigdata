#!/usr/bin/env python
import sys
import time


def print_file(sleep=5, limit=10):
    with open('/home/ubuntu/ctlogs-.1438663216674') as fh:
        count = 0
        for line in fh:
            sys.stdout.write(line)
            count += 1
            if count >= limit:
                count = 0
                time.sleep(sleep)


def main():
    while True:
        print_file(5, 10)


if __name__ == '__main__':
    main()
