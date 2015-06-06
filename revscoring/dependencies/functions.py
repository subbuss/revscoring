"""
The following functions provide a set of utilities for working with `Dependent`
and collections of `Dependent`.

* :func:`solve` provides basic dependency solving
* :func:`expand` provides minimal expansion of dependency trees
* :func:`dig` provides expansion of "root" dependents -- dependents with no
  dependencies of their own
* :func:`draw` provides a means to print a dependency tree to the terminal
  (useful when debugging)
"""
from .errors import DependencyError, DependencyLoop


def solve(dependents, context=None, cache=None):
    """
    Calculates a dependent's value by solving dependencies.

    :Parameters:
        dependents : `Dependent` | `function` | `iterable`
            A dependent or collection of dependents to solve
        context : `dict` | `iterable`
            A mapping of injected dependency processers to use as context.
            Can be specified as a set of new `Dependent` or a map of `Dependent`
            pairs.
        cache : `dict`
            A cache of previously solved dependencies as `Dependent`:`<value>`
            pairs

    :Returns:
        The result of executing the dependents with all dependencies resolved.
        If a single dependent is provided, the value will be returned.  If a
        collection of dependents is provided, a generator of values will be
        returned
    """
    cache = cache or {}
    context = normalize_context(context)

    if hasattr(dependents, '__iter__'):
        # Multiple values -- return a generator
        return _solve_many(dependents, context, cache)
    else:
        # Singular value -- return it's solution
        dependent = dependents
        value, cache, history = _solve(dependent, context=context, cache=cache)
        return value

def expand(dependents, context=None, cache=None):
    """
    Calculates a dependent's value by solving dependencies.

    :Parameters:
        dependents : `Dependent` | `iterable`
            A dependent or collection of dependents to solve
        context : `dict` | `iterable`
            A mapping of injected dependency processers to use as context.
            Can be specified as a set of new `Dependent` or a map of `Dependent`
            pairs.
        cache : `dict`
            A cache of previously solved dependencies as `Dependent`:`<value>`
            pairs

    :Returns:
        A generator over all dependents in the dependency tree with each
        dependent appearing only once
    """
    cache = set(cache or [])
    context = normalize_context(context)

    if hasattr(dependents, '__iter__'):
        # Multiple values
        return _expand_many(dependents, context, cache)
    else:
        # Singular value
        dependent = dependents
        return _expand(dependent, context, cache)



def draw(dependent, context=None, cache=None, depth=0):
    """
    Returns a string representation of the the dependency tree for a single
    `Dependent`.

    :Parameters:
        dependent : `Dependent`
            The dependent to draw the dependencies for.
        context : `dict` | `iterable`
            A mapping of injected dependency processers to use as context.
            Can be specified as a set of `Dependent` or a map of `Dependent`
            pairs.
        cache : `dict` | `set`
            A cache of previously solved dependencies as `Dependent`:`<value>`
            pairs.  When these items are reached while scanning the tree,
            "CACHED" will be printed.

    :Returns:
        None
    """
    return "\n".join(draw_lines(dependent, context, cache, depth)) \
           + "\n"

def draw_lines(dependent, context, cache, depth):
    cache = cache or {}
    context = normalize_context(context)


    if dependent in cache:
        yield "\t" * depth + " - " + str(dependent) + " CACHED"
    else:
        if dependent in context:
            dependent = context[dependent]

        yield "\t" * depth + " - " + str(dependent)

        # Check if we're a dependent with explicit dependencies
        if hasattr(dependent, "dependencies"):
            for dependency in dependent.dependencies:
                yield from draw_lines(dependency, context, cache, depth+1)

def dig(dependents, context=None, cache=None):
    """
    Expands root dependencies.  These are dependents at the bottom of the tree
    -- dependents with no dependencies of their own.

    :Parameters:
        dependents : `Dependent` | `iterable`
            A dependent or collection of dependents to scan
        context : `dict` | `iterable`
            A mapping of injected dependency processers to use as context.
            Can be specified as a set of new `Dependent` or a map of `Dependent`
            pairs.
        cache : `dict` | `set`
            A cache of previously solved dependencies to not scan beneath

    :Returns:
        A generator over root dependencies
    """
    cache = set(cache or [])
    context = normalize_context(context)

    if hasattr(dependents, '__iter__'):
        # Multiple values
        return _dig_many(dependents, context, cache)
    else:
        # Singular value
        dependent = dependents
        return _dig(dependent, context, cache)


def normalize_context(context):
    """
    Normalizes a context argument.  This allows for context to be specified
    either as a collection of contextual `Dependant` or a `dict` of `Dependent`
    pairs.
    """
    if context is None:
        return {}
    elif isinstance(context, dict):
        return context
    elif hasattr(context, "__iter__"):
        return {d:d for d in context}
    else:
        raise TypeError("'context' is not a dict or iterable: {0}" \
                        .format(str(context)))

def _solve(dependent, context, cache, history=None):
    history = history or set()

    # Check if we've already got a value for this dependency
    if dependent in cache:
        return cache[dependent], cache, history

    # Check if a corresponding dependent was injected into the context
    else:

        # If a dependent is in context here, replace it.
        if dependent in context:
            dependent = context[dependent]

        # Check if the dependency is callable.
        if not callable(dependent):
            raise RuntimeError("Can't solve dependency " + repr(dependent) +
                               ".  " + type(dependent).__name__ +
                               " is not callable.")

        # Check if we're in a loop.
        elif dependent in history:
            raise DependencyLoop("Dependency loop detected at " +
                                 repr(dependent))

        # All is good.  Time to generate a value
        else:
            # Add to history so we can detect any loops on the way down.
            history.add(dependent)

            # Check if we're a dependent with explicit dependencies
            if hasattr(dependent, "dependencies"):
                dependencies = dependent.dependencies
            else:
                # No dependencies?  OK.  Let's try that.
                dependencies = []

            # Generate args for process function from dependencies (if any)
            args = []
            for dependency in dependencies:
                value, cache, history = _solve(dependency, context=context,
                                               cache=cache, history=history)

                args.append(value)

            # Generate value
            try:
                value = dependent(*args)
            except Exception as e:
                raise DependencyError("Failed to process {0}: {1}"
                                      .format(dependent, e), str(e))

            # Add value to cache
            cache[dependent] = value
            return cache[dependent], cache, history

def _solve_many(dependents, context, cache):

    for dependent in dependents:
        value, cache, history = _solve(dependent, context, cache)
        yield value

def _expand(dependent, context, cache):
    if dependent not in cache:
        yield dependent
        cache.add(dependent)

        if hasattr(dependent, "dependencies"):
            yield from _expand_many(dependent.dependencies, context, cache)


def _expand_many(dependents, context, cache):
    for dependent in dependents:
        yield from _expand(dependent, context, cache)

def _dig(dependent, context, cache):
    if hasattr(dependent, "dependencies"):
        if len(dependent.dependencies) > 0:
            yield from _dig_many(dependent.dependencies, context, cache)
        else:
            yield dependent
    else:
        yield dependent

def _dig_many(dependents, context, cache):
    for dependent in dependents:
        if dependent not in cache:
            if dependent in context:
                # Use contextual dependency
                dependent = context[dependent]

            cache.add(dependent)
            yield from _dig(dependent, context, cache)