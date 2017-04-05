import datetime
import sys

import happybase


def main(host):
    conn = happybase.Connection(host=host)

    conn.create_table(
        'clickstream',
        {
            'sys': dict(),
            'data': dict(),
            'geo': dict(),
        }
    )


if __name__ == '__main__':
    main(sys.argv[1])
