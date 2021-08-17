"""Synchronise and then copy newly created files from one directory to another."""

import argparse
import logging
import pathlib
import shutil
import subprocess
import time

import watchdog.events
import watchdog.observers

# TODO: add logging to file
logging.basicConfig(level=logging.DEBUG)


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


class MyEventHandler(watchdog.events.FileSystemEventHandler):
    """Custom file system event handler."""

    source = pathlib.Path()
    destination = pathlib.Path()

    def on_created(self, event):
        """Copy a file from source to destination.

        Parameters
        ----------
        event : watchdog.events.FileSystemEvent
            File system event.
        """
        src = pathlib.Path(event.src_path)
        src_tail = src.parts[len(self.source.parts) :]

        dst = self.destination
        for part in src_tail:
            dst = dst.joinpath(part)

        if src.is_dir() and (dst.exists() is False):
            shutil.copytree(src, dst)
        elif dst.exists() is False:
            shutil.copy2(src, dst)


def main(source, destination):
    """Run the watchdog, copying new files in source dir to destination dir.

    Parameters
    ----------
    source : str
        Source directory.
    destination : str
        Destination directory.
    """
    event_handler = MyEventHandler()
    event_handler.source = pathlib.Path(source)
    event_handler.destination = pathlib.Path(destination)
    observer = watchdog.observers.Observer()
    observer.schedule(event_handler, source, recursive=True)
    observer.start()
    try:
        while True:
            time.sleep(1)
    finally:
        observer.stop()
        observer.join()


if __name__ == "__main__":
    args = get_args()

    # run a sync first in case anything was missed since last run
    sync(args.source, args.destination)

    # start watchdog and run forever
    main(args.source, args.destination)
