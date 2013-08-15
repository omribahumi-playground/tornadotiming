import time
import functools
import logging
import tornado.gen
import tornado.web

logger = logging.getLogger(__name__)
original_coroutine = tornado.gen.coroutine
original_RequestHandler_init = tornado.web.RequestHandler.__init__

def formatargs(args, kwargs):
    ret = []
    if args:
        ret.append(", ".join(map(repr, args)))
    if kwargs:
        ret.append(["%r=%r" for k,v in kwargs.iteritems()])
    return ", ".join(ret)


def timingwrapper(f):
    """If you don't want to monkeypatch tornado.web.RequestHandler,
    you can use this function to decorate a non tornado.gen function
    """
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        _t = time.time()
        result = f(*args, **kwargs)
        _t = time.time() - _t
        if _t > 1:
            logger.critical(
                "Slow function call took %f seconds on %s line %d %s(%s) returned %r",
                _t,
                f.func_code.co_filename,
                f.func_code.co_firstlineno,
                f.func_name,
                formatargs(args, kwargs),
                result
            )
        return result

    return wrapper

def timingwrapper_gen(f):
    """Don't use this function directly, use coroutine() instead"""
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        nextValue = None
        result = None

        gen = f(*args, **kwargs)
        while True:
            _t = time.time()
            if nextValue:
                result = gen.send(nextValue)
            else:
                result = gen.next()

            _t = time.time() - _t
            # log calls slower than 1 second
            if _t > 1:
                logger.critical(
                    "Slow generator function iteration took %f seconds on %s line %d %s(%s) returned %r",
                    _t,
                    gen.gi_code.co_filename,
                    gen.gi_frame.f_lineno,
                    f.func_name,
                    formatargs(args, kwargs),
                    result
                )
            nextValue = yield result

    return wrapper

class TimingRequestHandler(tornado.web.RequestHandler):
    """If you don't want to monkeypatch tornado.web.RequestHandler, use this
    class instead in your code
    """
    @functools.wraps(original_RequestHandler_init)
    def __init__(self, *args, **kwargs):
        original_RequestHandler_init(*args, **kwargs)
        for method in self.SUPPORTED_METHODS:
            # functio names are method in lower case
            method = method.lower()

            # if it has implementation for that function
            if getattr(self, method, None):
                func = getattr(self, method)
                # only if it's not a generator function
                if not func.func_code.co_flags & 0x20:
                    # wrap it!
                    setattr(self, method, timingwrapper(func))

@functools.wraps(original_RequestHandler_init)
def monkeypatched_RequestHandler_init(self, *args, **kwargs):
    """I couldn't replace the entire class because it caused an issue with the
    original constructor. When replacing RequestHandler with TimingRequestHandler,
    the original RequestHandler code is expecting `object` when calling
    super(RequestHandler, self), but is getting itself instead

    The solution I found is to only monkeypatch the constructor
    """
    original_RequestHandler_init(self, *args, **kwargs)
    for method in self.SUPPORTED_METHODS:
        # functio names are method in lower case
        method = method.lower()

        # if it has implementation for that function
        if getattr(self, method, None):
            func = getattr(self, method)
            # only if it's not a generator function
            if not func.func_code.co_flags & 0x20:
                # wrap it!
                setattr(self, method, timingwrapper(func))



@functools.wraps(tornado.gen.coroutine)
def coroutine(f):
    """One decorator for both tornado.gen.coroutine and timingwrapper_gen.
    Use it if you don't want to monkeypatch tornado"""
    return original_coroutine(timingwrapper_gen(f))

def monkeypatch():
    """Replaces the original tornado.gen.coroutine with our coroutine,
    and makes RequestHandler slowiness aware
    """
    tornado.gen.coroutine = coroutine
    tornado.web.RequestHandler.__init__ = monkeypatched_RequestHandler_init

__all__ = ['monkeypatch', 'timingwrapper', 'coroutine', 'TimingRequestHandler']
