import os
import time
import functools
import simplejson as json
import hashlib
import logging

def timer(func):
    """Print the runtime of the decorated function"""

    @functools.wraps(
        func
    )  # This line preserves the name and docstring of the decorated function
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        total_time = end_time - start_time
        if total_time < 60:
            print(f"Function {func.__name__} took {total_time:.2f} seconds to execute.")
        else:
            print(
                f"Function {func.__name__} took {total_time//60}m {total_time%60:.2f}s to execute."
            )
        return result
    return wrapper

def batch_list(data, batch_size):
    """Generate batches of data with a given batch size."""
    batches = []
    for i in range(0, len(data), batch_size):
        batch = data[i:i + batch_size]
        batches.append(batch)
    return batches

def md5_sha_from_str(val):
    """Generate md5 hash from string"""
    return hashlib.md5(val.encode("utf-8")).hexdigest()

def md5_sha_from_dict(obj, ignore_nan=False, default=None,):
    """Generate md5 hash from dictionary"""
    json_data = json.dumps(obj, sort_keys=True,
                           ignore_nan=ignore_nan, default=default)
    return md5_sha_from_str(json_data)


def get_logger(name):
    """Get logger object."""
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    ch = logging.StreamHandler()
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    return logger