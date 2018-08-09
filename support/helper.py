import logging
logger = logging.getLogger(__name__)
from inspect import getmembers, isfunction
import re
import logging

logger = logging.getLogger(__name__)


discordCommandos = []
class DiscordCommando:
    def __init__(self,commando,fun,docstring):
        self.commando = commando
        self.fun = fun
        self.docstring = docstring

    @staticmethod
    def allCommandos():
        return discordCommandos
    @staticmethod
    def addCommando(commando):
        logger.info(f"Add commando {commando}")
        discordCommandos.append(commando)

    def __str__(self):
        return f"Cmd: {self.commando}"

def log_return(func : callable):
    def func_wrapper(*args):
        answer = func(*args)
        if answer != None:
            logger.debug(f"Answer: {answer}")
        return answer
    func_wrapper.__doc__ = func.__doc__
    return func_wrapper

def parseCommandoFunctions(module):

    functions_list = [o for o in getmembers(module) if isfunction(o[1])]

    for name,fun in functions_list:
        try:
            if ":DiscordCommando:" in fun.__doc__ and name.startswith("cdo"):
                commando = re.search(':DiscordCommando:\s*(!\w+)',fun.__doc__).group(1)
                docstring = fun.__doc__
                DiscordCommando.addCommando(DiscordCommando(commando,fun,docstring))
            elif name.startswith("cdo"):
                raise ValueError("You seemed to have added a command function without :DidscordCommando: keyword!")
        except TypeError:
            pass
