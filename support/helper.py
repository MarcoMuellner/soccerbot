import logging
logger = logging.getLogger(__name__)
from inspect import getmembers, iscoroutine
import re
import logging
from typing import Callable
from datetime import datetime,timezone

logger = logging.getLogger(__name__)

def log_return(func : callable):
    def func_wrapper(*args):
        answer = func(*args)
        if answer != None:
            logger.debug(f"Answer: {answer}")
        return answer
    func_wrapper.__doc__ = func.__doc__
    return func_wrapper

taskList = []

class Task:
    def __init__(self,name,args):
        self.name = name
        self.args = args
        self.time = datetime.now(timezone.utc)

    @staticmethod
    def getAllTaks():
        return taskList

    @staticmethod
    def addTask(task):
        taskList.append(task)

    @staticmethod
    def removeTask(task):
        taskList.remove(task)

def task(fun:Callable):
    async def func_wrapper(*args):
        task = Task(fun.__name__, args)
        Task.addTask(task)
        res = await fun(*args)
        Task.removeTask(task)
        return res
    return func_wrapper
