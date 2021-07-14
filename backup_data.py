"""Synchronise and then copy newly created files from one directory to another."""

import argparse
import logging
import pathlib
import subprocess
import time

import watchdog


def get_args():
    """Get command line arguments."""
    parser = argparse.ArgumentParser()
    parser.add_argument("-s", "--source", help="Source directory.")
    parser.add_argument("-d", "--destination", help="Destination directory.")

    return parser.parse_args()


def sync(source, destination):
    """Backup source to destination using robocopy.

    Uses call to robocopy, which is Windows only.

    Parameters
    ----------
    source : str
        Source directory.
    destination
        Destination directory.
    """
    # time string for robocopy log filename
    time_str = time.strftime("%Y%m%d-%H%M%S", time.localtime())

    # robocopy parameter meanings:
    # /e Copies subdirectories. This option automatically includes empty directories.
    # /mt[:n] Creates multi-threaded copies with n threads. n must be an integer
    # between 1 and 128.
    # /xc Excludes existing files with the same timestamp, but different file sizes.
    # /xn Excludes existing files newer than the copy in the source directory.
    # /xo Excludes existing files older than the copy in the source directory.
    # /ns Specifies that file sizes are not to be logged.
    # /nc Specifies that file classes are not to be logged.
    # /nfl Specifies that file names are not to be logged.
    # /ndl Specifies that directory names are not to be logged.
    # /np Specifies that the progress of the copying operation (the number of files or
    # directories copied so far) will not be displayed.
    # /log Writes the status output to the log file (overwrites the existing log file).
    p = subprocess.run(
        [
            "robocopy",
            source,
            destination,
            "/e",
            "/mt:128",
            "/xc",
            "/xn",
            "/xo",
            "/ns",
            "/nc",
            "/nfl",
            "/ndl",
            "/np",
            f"/log:{time_str}_log.txt",
        ]
    )
