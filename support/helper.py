def log_return(func):
    def func_wrapper(*args):
        answer = func(*args)
        if answer != None:
            logger.debug(f"Answer: {answer}")
        return answer
    return func_wrapper