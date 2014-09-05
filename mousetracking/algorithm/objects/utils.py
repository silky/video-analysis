'''
Created on Sep 5, 2014

@author: zwicker
'''




class cached_property(object):
    """Decorator to use a function as a cached property.

    The function is only called the first time and each successive call returns
    the cached result of the first call.

        class Foo(object):

            @cached_property
            def foo(self):
                return "Cached"

    Adapted from <http://wiki.python.org/moin/PythonDecoratorLibrary>.

    """

    def __init__(self, func, name=None, doc=None):
        self.__name__ = name or func.__name__
        self.__module__ = func.__module__
        self.__doc__ = doc or func.__doc__
        self.func = func


    def __get__(self, obj, type=None):  # @ReservedAssignment
        if obj is None:
            return self

        # try to retrieve from cache or call and store result in cache
        try:
            value = obj._cache[self.__name__]
        except KeyError:
            value = self.func(obj)
            obj._cache[self.__name__] = value
        except AttributeError:
            value = self.func(obj)
            obj._cache = {self.__name__: value}
        return value




class LazyValue(object):
    """ class that represents a value that is only loaded when it is accessed """
    # TODO: subclass this class to arrive at different implementations
    # write 
    def __init__(self, cls, value):
        self.cls = cls
        self.value = value
        
        
    def store(self, hdf_name, hdf_file):
        """ store the data in the file """
        pass
        
    def load(self):
        """ load the data and return it """
        pass

