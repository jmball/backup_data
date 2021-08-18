"""Synchronise and then copy newly created files from one directory to another."""

import argparse
import logging
import os
import pathlib
import shutil
import subprocess
import time

import watchdog.events
import watchdog.observers
import watchdog.observers.polling


def get_args():
    """Get command line arguments."""
    parser = argparse.ArgumentParser()
    parser.add_argument("-s", "--source", help="Source directory.")
    parser.add_argument("-d", "--destination", help="Destination directory.")
    parser.add_argument("-l", "--log_dir", default="", help="Log directory.")

    return parser.parse_args()


def sync(source, destination, log_dir):
    """Backup source to destination using robocopy.

    Uses call to robocopy, which is Windows only.

    Parameters
    ----------
    source : str
        Source directory.
    destination : str
        Destination directory.
    log_dir : str
        Log directory.
    """
    # time string for robocopy log filename
    time_str = time.strftime("%Y%m%d-%H%M%S", time.localtime())
    log_path = pathlib.Path(log_dir).joinpath(f"{time_str}_robocopy.log")

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
            f"/log:{log_path}",
        ]
    )


class MyEventHandler(watchdog.events.FileSystemEventHandler):
    """Custom file system event handler."""

    source = pathlib.Path()
    destination = pathlib.Path()
    logger = None

    def on_created(self, event):
        """Copy a file from source to destination.

        Ignores folder paths.

        Parameters
        ----------
        event : watchdog.events.FileSystemEvent
            File system event.
        """
        src = pathlib.Path(event.src_path)

        # build destination path
        dst = self.destination
        src_tail = src.parts[len(self.source.parts) :]
        for part in src_tail:
            dst = dst.joinpath(part)

        # copy file or folder if destination doesn't already exist
        if dst.is_file():
            if dst.exists():
                self.logger.debug(f"Cannot copy file: '{str(dst)}' already exists")
            else:
                # make sure parent folder exists in destination
                if not (dst.parent.exists()):
                    dst.parent.mkdir(parents=True)

                # large files and complex directories can take time to become
                # available after a file creation event so wait until file creation
                # at source is finished
                while True:
                    try:
                        # renaming isn't possible on Windows while file is being copied
                        # so if there's no error here the file has finished copying
                        os.rename(src, src)
                        break
                    except OSError:
                        self.logger.exception()
                        self.logger.info(f"Waiting for file to finish copying: {src}")
                        time.sleep(0.5)

                # attempt copy
                try:
                    shutil.copy2(src, dst)
                    self.logger.debug(f"Copied file to: {str(dst)}")
                except FileNotFoundError:
                    self.logger.exception()


def create_logger(log_dir):
    """Create a logger.

    Parameters
    ----------
    log_dir : str
        Log directory.
    """
    # create logger
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)

    # create console handler and set level to debug
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)

    # add file handler and set level to info
    time_str = time.strftime("%Y%m%d-%H%M%S", time.localtime())
    fh = logging.FileHandler(pathlib.Path(log_dir).joinpath(f"{time_str}_watchdog.log"))
    fh.setLevel(logging.DEBUG)

    # create formatter
    formatter = logging.Formatter("%(asctime)s|%(name)s|%(levelname)s|%(message)s")

    # add formatter to ch and fh
    ch.setFormatter(formatter)
    fh.setFormatter(formatter)

    # add ch and fh to logger
    logger.addHandler(ch)
    logger.addHandler(fh)

    return logger


def main(source, destination, log_dir):
    """Run the watchdog, copying new files in source dir to destination dir.

    Parameters
    ----------
    source : str
        Source directory.
    destination : str
        Destination directory.
    log_dir : str
        Log directory.
    """
    # setup logging
    logger = create_logger(log_dir)
    logger.info(f"Source directory: {source}")
    logger.info(f"Destination directory: {destination}")

    # setup watchdog event handler
    event_handler = MyEventHandler()
    event_handler.source = pathlib.Path(source)
    event_handler.destination = pathlib.Path(destination)
    event_handler.logger = logger

    # setup watchdog observer
    # standard observer sometimes misses file creation events but polling observer
    # seems more robust
    observer = watchdog.observers.polling.PollingObserver()
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
    sync(args.source, args.destination, args.log_dir)

    # start watchdog and run forever
    main(args.source, args.destination, args.log_dir)
