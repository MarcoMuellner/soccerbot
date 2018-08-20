import logging
logger = logging.getLogger(__name__)
import asyncio
import logging
import sys
from typing import Callable
from datetime import datetime,timezone
import os
from git import Git,Repo
from typing import List

logger = logging.getLogger(__name__)
path = os.path.dirname(os.path.realpath(__file__)) + "/../"

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

async def shutdown():
    await asyncio.sleep(10)
    logger.info("Shutting down!")
    sys.exit()

def fetchAll():
    for remote in Repo(path).remotes:
        remote.fetch()

def getVersions() ->List[str]:
    fetchAll()
    return [t.name for t in Repo(path).tags]

def checkoutVersion(version : str) -> bool:
    fetchAll()
    tags = [t.name for t in Repo(path).tags]
    if version != "master" and version not in tags:
        logger.error(f"Can't set version to {version}, as its not in tags and not master."
                     f"Available versions  : {tags}")
        return False

    logger.info(f"Check out version {version}")
    Git(path).checkout(version)
    return True

def currentVersion() -> str:
    versions = getVersions()
    g = Git(path)
    for i in versions:
        if i in g.branch():
            return i

    if "* master" == g.branch():
        return "master"

    return g.branch()



