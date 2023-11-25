# import contextlib
# import json
# import os
# import re
# import subprocess
# from datetime import datetime, timedelta
# from importlib import import_module
# from inspect import isclass
# from json import JSONDecodeError
# from multiprocessing import cpu_count
# from subprocess import check_output
#
# import fsspec  # type: ignore[import]
# import yaml
# from loguru import logger
#
# from afi.constants import TARDIS_DATA_PATH
#
# # moved to afi.logging
# # def config_logger():
# #     """Default logging configuration"""
# #     logging.basicConfig(
# #         format="%(asctime)s %(levelname)-2s [%(filename)s:%(lineno)d] %(message)s",
# #         level=logging.INFO,
# #         datefmt="%Y-%m-%d %H:%M:%S",
# #     )
#
#
# def write_json_file(fpath, data):
#     with fsspec.open(fpath, "w") as fp:
#         try:
#             fp.write(json.dumps(data))
#         except JSONDecodeError as ex:
#             logger.error(f"error processing: {data}")
#             raise ex
#
#
# def log_decaying_indices(array_length, factor=1.5):
#     """
#     Returns indices that select into an array and an expontentially decaying rate (starting at the end of the array)
#
#     >>> log_decaying_indices(100)
#     [99, 98, 96, 94, 91, 86, 78, 67, 50, 24]
#     >>> log_decaying_indices(1)
#     [0]
#     """
#     assert array_length > 0
#     assert factor >= 1
#     i = array_length - 1
#     indices = []
#     delta = 1
#     while i >= 0:
#         indices.append(i)
#         i = min(round(i - delta), i - 1)
#         delta *= factor
#     return indices
#
#
# def indices_that_match(items, patterns: str | list[str]):
#     """
#     :returns: the column indices that match patterns
#     >>> items = ['hello','world','-afi']
#     >>> indices_that_match(items, 'world')
#     [1]
#     >>> indices_that_match(items, ['hello', '-afi'])
#     [0, 2]
#     """
#
#     if isinstance(patterns, str):
#         patterns = [patterns]
#     return [i for i, item in enumerate(items) if re.search("|".join(patterns), item)]
#
#
# def import_and_instantiate(import_path: str, *args, **kwargs):
#     """
#     :param import_path: path to a module
#     :param *args: args to pass to the init
#     :param kwargs: kwargs to pass to init
#
#     >>> import_and_instantiate('datetime.timedelta', seconds=3600)
#     datetime.timedelta(seconds=3600)
#     """
#     module_name, class_name = get_module_and_class_names(import_path)
#     cls = getattr(import_module(module_name), class_name)
#     return cls(*args, **kwargs)
#
#
# class _RaiseExceptionIfMissing:
#     pass
#
#
# def read_json_file(fname, default=_RaiseExceptionIfMissing):
#     """
#     :param default: default behavior is to raise an exception.  If set by caller,
#     to something else (ex, None), returns that value if the file is missing
#     """
#     if default != _RaiseExceptionIfMissing and not os.path.exists(fname):
#         return default
#     with open(fname) as fp:
#         return json.load(fp)
#
#
# def read_yaml_file(fname, default=_RaiseExceptionIfMissing):
#     """
#     :param default: default behavior is to raise an exception.  If set by caller,
#     returns this default if the file is missing
#     """
#     if default != _RaiseExceptionIfMissing and not os.path.exists(fname):
#         return default
#     with open(fname) as fp:
#         return yaml.load(fp.read(), Loader=yaml.Loader)
#
#
# class ClassPropertyDescriptor:
#     """copied from https://stackoverflow.com/questions/5189699/how-to-make-a-class-property"""
#
#     def __init__(self, fget, fset=None):
#         self.fget = fget
#         self.fset = fset
#
#     def __get__(self, obj, klass=None):
#         if klass is None:
#             klass = type(obj)
#         return self.fget.__get__(obj, klass)()
#
#     def __set__(self, obj, value):
#         if not self.fset:
#             raise AttributeError("can't set attribute")
#         type_ = type(obj)
#         return self.fset.__get__(obj, type_)(value)
#
#     def setter(self, func):
#         if not isinstance(func, (classmethod, staticmethod)):
#             func = classmethod(func)
#         self.fset = func
#         return self
#
#
# def classproperty(func):
#     """
#     copied from https://stackoverflow.com/questions/5189699/how-to-make-a-class-property
#     similar to @property decorator but works on an uninstantiated object"""
#     if not isinstance(func, (classmethod, staticmethod)):
#         func = classmethod(func)
#
#     return ClassPropertyDescriptor(func)
#
#
# def log_system_info():
#     # log system info
#     logger.info("*** System Info ****")
#     logger.info(check_output("free -h", shell=True))
#     logger.info(check_output("df -h", shell=True))
#     logger.info(check_output("env", shell=True))
#     with contextlib.suppress(subprocess.SubprocessError):
#         logger.info(check_output("nvidia-smi", shell=True))
#     logger.info("**** CPUs ****")
#     logger.info(f"{cpu_count()} CPUs detected")
#
#
# def get_module_and_class_names(class_path: str) -> tuple[str, str]:
#     """
#     Return module name and class name from full class path
#     >>> get_module_and_class_names("torch.optim.Adam")
#     ('torch.optim', 'Adam')
#     """
#     split = class_path.split(".")
#     class_name = split[-1]
#     module_name = ".".join(split[:-1])
#     return module_name, class_name
#
#
# def get_subclasses_from_object_dict(class_: type, object_dict: dict) -> dict[str, type]:
#     """
#     Returns all of the subclasses of class_ that are inside object_dict, which is usually passed in as the
#     globals() of the caller.
#     Useful for getting all of the subclasses of a class that are defined in a module.
#     :param class_: A class
#     :param object_dict: an object dictionary (for ex the output of globals())
#     :return: dict of {"class_name": class, ...} where class is as subtype of class_
#     """
#     return {
#         var_name: variable
#         for var_name, variable in object_dict.items()
#         if isclass(variable) and issubclass(variable, class_) and var_name != class_.__name__
#     }
#
#
# def construct_fpath(
#     day: int,
#     month: int,
#     year: int,
#     pair: str,
#     source: str = "binance",
#     data_type: str = "book_snapshot_25",
#     market_type: str = "spot",
#     extension: str = "pq",
#     check_exists=True,
# ) -> str:
#     """
#     >>> construct_fpath(8, 8, 2022, "BTC_USDT", "binance", "book_snapshot_25", "spot", "pq", check_exists=False)
#     '/static/bot/dagster/prod/storage/binance/spot/book_snapshot_25/BTC_USDT/2022-08-08.pq'
#     """
#     if "/" in pair:
#         # tardis data paths are bad :(
#         pair = "_".join(pair.split("/"))
#     path = f"{TARDIS_DATA_PATH}/{source}/{market_type}/{data_type}/{pair}/{year}-{month:02}-{day:02}.{extension}"
#     if check_exists:
#         assert os.path.exists(path), path
#     return path
#
#
# def str_to_datetime(event: str) -> datetime:
#     """
#     >>> str_to_datetime("2022-10-13") == datetime(2022, 10, 13)
#     True
#     >>> str_to_datetime("2022-10-13T04:20") == datetime(2022, 10, 13, 4, 20)
#     True
#     >>> str_to_datetime("2022-10-13T04:20:57") == datetime(2022, 10, 13, 4, 20, 57)
#     True
#     >>> str_to_datetime("2022-10-13T04:20:57.282") == datetime(2022, 10, 13, 4, 20, 57, 282000)
#     True
#     """
#     possible_formats = ["%Y-%m-%d", "%Y-%m-%dT%H:%M", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f"]
#     parsed_datetime: datetime | None = None
#     for fmt in possible_formats:
#         with contextlib.suppress(ValueError):
#             parsed_datetime = datetime.strptime(event, fmt)
#             break  # if format is correct, don't test any other formats
#     if parsed_datetime is None:
#         raise ValueError("Date is in wrong format")
#     return parsed_datetime
#
#
# def datetime_to_str(event: datetime) -> str:
#     return event.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3]  # strip last 3 chars to convert from micro to milliseconds
#
#
# def str_to_timedelta(delta: str) -> timedelta:
#     """
#     >>> str_to_timedelta("10m") == timedelta(minutes=10)
#     True
#     >>> str_to_timedelta("1us") == timedelta(microseconds=1)
#     True
#     >>> str_to_timedelta("5mo") == timedelta(days=150)
#     True
#     >>> str_to_timedelta("123h") == timedelta(hours=123)
#     True
#     """
#
#     match = re.match(r"(\d+)(\w+)", delta)
#     assert match is not None
#     value, unit = match.groups()
#     multipliers = {
#         "us": 1e-6,
#         "ms": 1e-3,
#         "s": 1,
#         "m": 60,
#         "h": 60 * 60,
#         "d": 60 * 60 * 24,
#         "w": 60 * 60 * 24 * 7,
#         "mo": 60 * 60 * 24 * 30,
#         "y": 60 * 60 * 24 * 365.25,
#     }
#     assert unit in multipliers, f"Unit {unit} is not supported"
#     seconds = int(value) * multipliers[unit]
#     return timedelta(seconds=seconds)
#
#
# def match_lob_column(col: str) -> re.Match | None:
#     """
#     >>> bool(match_lob_column("bids[24].amount"))
#     True
#     >>> bool(match_lob_column("asks_24_price"))
#     False
#     """
#     return re.search(r"(asks|bids)\[(\d+)\].(amount|price)", col)
