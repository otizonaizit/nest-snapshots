# -*- coding: utf-8 -*-
#
# hl_api.py
#
# This file is part of NEST.
#
# Copyright (C) 2004 The NEST Initiative
#
# NEST is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.
#
# NEST is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with NEST.  If not, see <http://www.gnu.org/licenses/>.

"""
High-level API of PyNEST

This file defines the user-level functions of NEST's Python interface
by mapping NEST/SLI commands to Python. Please try to follow these
rules:

1. SLI commands have the same name in Python. This means that most
   function names are written in camel case, although the Python
   guidelines suggest to use lower case for function names. However,
   this way, it is easier for users to migrate from SLI to Python.

2. Nodes are identified by their global IDs (GID) by default.

3. GIDs are always written as lists, e.g. [0], [1,2]

4. Commands that return a GID must return it as list of GID(s).

5. When possible, loops over nodes should be propagated down to the
   SLI level.  This minimizes the number of Python<->SLI conversions
   and increases performance.  Loops in SLI are also faster than in
   Python. 
        
6. If you have a *very* good reason, you may deviate from these guidelines.
"""

import functools
import inspect
import warnings

from .pynestkernel import SLIDatum, SLILiteral, NESTError, CONN_LEN

# These variables MUST be set by __init__.py right after importing.
# There is no safety net, whatsoever.
sps = spp = sr = pcd = None

__debug = False

# -------------------- Helper functions

def set_debug(dbg=True):
    """
    Set the debug flag of the high-level API.
    """

    global __debug
    __debug = dbg


def get_debug():
    """
    Return the current value of the debug flag of the high-level API.
    """
    return __debug


def stack_checker(f):
    """
    Decorator to add stack checks to functions using PyNEST's
    low-level API. This decorator works only on functions. See
    check_stack() for the generic version for functions and
    classes.
    """

    @functools.wraps(f)
    def stack_checker_func(*args, **kwargs):
        if not get_debug():
            return f(*args, **kwargs)
        else:
            sr('count')
            stackload_before = spp()
            result = f(*args, **kwargs)
            sr('count')
            num_leftover_elements = spp() - stackload_before
            if num_leftover_elements != 0:
                eargs = (f.__name__, num_leftover_elements)
                etext = "Function '%s' left %i elements on the stack."
                raise NESTError(etext % eargs)
            return result

    return stack_checker_func


def check_stack(thing):
    """
    Convenience wrapper for applying the stack_checker decorator to
    all class methods of the given class, or to a given function. If
    the object cannot be decorated, it is returned unchanged.
    """

    if inspect.isfunction(thing):
        return stack_checker(thing)
    elif inspect.isclass(thing):
        for name, mtd in inspect.getmembers(thing, predicate=inspect.ismethod):
            if name.startswith("test_"):
                setattr(thing, name, stack_checker(mtd))
        return thing
    else:
        raise ValueError("unable to decorate {0}".format(thing))


def is_iterable(seq):
    """
    Return True if the given object is an iterable, False otherwise
    """

    try:
        iter(seq)
    except TypeError:
        return False

    return True


def is_coercible_to_sli_array(seq):
    """
    Checks whether `seq` is coercible to a SLI array
    """

    import sys

    if sys.version_info[0] >= 3:
        return isinstance(seq, (tuple, list, range))
    else:
        return isinstance(seq, (tuple, list, xrange))


def is_sequence_of_connections(seq):
    """
    Low-level API accepts an iterable of dictionaries or subscriptables of CONN_LEN
    """

    try:
        cnn = next(iter(seq))
        return isinstance(cnn, dict) or len(cnn) == CONN_LEN
    except TypeError:
        pass

    return False


def is_sequence_of_gids(seq):
    """
    Checks whether the argument is a potentially valid sequence of GIDs (non-negative integers)
    """

    return all(isinstance(n, int) and n >= 0 for n in seq)


def broadcast(item, length, allowed_types, name="item"):

    if isinstance(item, allowed_types):
        return length * (item,)
    elif len(item) == 1:
        return length * item
    elif len(item) != length:
        raise TypeError("'%s' must be a single value, a list with one element or a list with %i elements." % (name, length))

    return item

# -------------------- Functions to get information on NEST

@check_stack
def sysinfo():
    """
    Print information on the platform on which NEST was compiled.
    """

    sr("sysinfo")


@check_stack
def version():
    """
    Return the NEST version.
    """

    sr("statusdict [[ /kernelname /version ]] get")
    return " ".join(spp())
    

@check_stack
def authors():
    """
    Print the authors of NEST.
    """

    sr("authors")


@check_stack
def helpdesk(browser="firefox"):
    """
    Open the NEST helpdesk in the given browser. The default browser is firefox.
    """
    
    sr("/helpdesk << /command (%s) >> SetOptions" % browser)
    sr("helpdesk")


@check_stack
def help(obj=None, pager="less"):
    """
    Show the help page for the given object using the given pager. The
    default pager is less.
    """

    if obj is not None:
        sr("/page << /command (%s) >> SetOptions" % pager)
        sr("/%s help" % obj)
    else:
        print("Type 'nest.helpdesk()' to access the online documentation in a browser.")
        print("Type 'nest.help(object)' to get help on a NEST object or command.")
        print()
        print("Type 'nest.Models()' to see a list of available models in NEST.")
        print()
        print("Type 'nest.authors()' for information about the makers of NEST.")
        print("Type 'nest.sysinfo()' to see details on the system configuration.")
        print("Type 'nest.version()' for information about the NEST version.")
        print()
        print("For more information visit http://www.nest-initiative.org.")


@check_stack
def get_verbosity():
    """
    Return verbosity level of NEST's messages.
    """
    
    sr('verbosity')
    return spp()


@check_stack
def set_verbosity(level):
    """
    Change verbosity level for NEST's messages. level is a string and
    can be one of M_FATAL, M_ERROR, M_WARNING, or M_INFO.
    """

    sr("%s setverbosity" % level)


@check_stack
def get_argv ():
    """
    Return argv as seen by NEST. This is similar to Python sys.argv
    but might have changed after MPI initialization.
    """
    sr ('statusdict')
    statusdict = spp ()
    return statusdict['argv']


@check_stack
def message(level,sender,text):
    """
    Print a message using NEST's message system.
    """

    sps(level)
    sps(sender)
    sps(text)
    sr('message')


# -------------------- Functions for simulation control

@check_stack
def Simulate(t):
    """
    Simulate the network for t milliseconds.
    """

    sps(float(t))
    sr('ms Simulate')


@check_stack
def ResumeSimulation():
    """
    Resume an interrupted simulation.
    """

    sr("ResumeSimulation")


@check_stack
def ResetKernel():
    """
    Reset the simulation kernel. This will destroy the network as
    well as all custom models created with CopyModel(). Calling this
    function is equivalent to restarting NEST.
    """

    sr('ResetKernel')


@check_stack
def ResetNetwork():
    """
    Reset all nodes and connections to their original state.
    """

    sr('ResetNetwork')


@check_stack
def SetKernelStatus(params):
    """
    Set parameters for the simulation kernel.
    """
    
    sps(0)
    sps(params)
    sr('SetStatus')


@check_stack
def GetKernelStatus(keys=None):
    """
    Obtain parameters of the simulation kernel.

    Returns:
    - Parameter dictionary if called without argument
    - Single parameter value if called with single parameter name
    - List of parameter values if called with list of parameter names
    """

    sr('0 GetStatus')
    status_root = spp()

    sr('/subnet GetDefaults')
    status_subnet = spp()

    d = dict((k, v) for k, v in status_root.items() if k not in status_subnet)

    if keys is None:
        return d
    elif isinstance(keys, (str, SLILiteral)):
        return d[keys]
    elif is_iterable(keys):
        return tuple(d[k] for k in keys)
    else:
        raise TypeError("keys should be either a string or an iterable")


@check_stack
def Install(module_name):
    """
    Load a dynamically linked NEST module.

    Example:
    nest.Install("mymodule")

    Returns:
    NEST module identifier, required for unloading.

    Note: Dynamically linked modules are searched in the
    LD_LIBRARY_PATH (DYLD_LIBRARY_PATH under OSX).
    """

    return sr("(%s) Install" % module_name)


# -------------------- Functions for parallel computing

@check_stack
def Rank():
    """
    Return the MPI rank of the local process.
    """

    sr("Rank")
    return spp()

@check_stack
def NumProcesses():
    """
    Return the overall number of MPI processes.
    """

    sr("NumProcesses")
    return spp()

@check_stack
def SetAcceptableLatency(port, latency):
    """
    Set the acceptable latency (in ms) for a MUSIC port.
    """
    
    sps(latency)
    sr("/%s exch SetAcceptableLatency" % port)


# -------------------- Functions for model handling

@check_stack
def Models(mtype="all", sel=None):
    """
    Return a list of all available models (neurons, devices and
    synapses). Use mtype='nodes' to only see neuron and device models,
    mtype='synapses' to only see synapse models. sel can be a string,
    used to filter the result list and only return models containing
    it.
    """

    if mtype not in ("all", "nodes", "synapses"):
        raise ValueError("type has to be one of 'all', 'nodes' or 'synapses'")

    models = []

    if mtype in ("all", "nodes"):
        sr("modeldict")
        models += spp().keys()

    if mtype in ("all", "synapses"):
        sr("synapsedict")
        models += spp().keys()

    if sel is not None:
        models = [x for x in models if x.find(sel) >= 0]

    models.sort()

    return tuple(models)


@check_stack
def SetDefaults(model, params, val=None):
    """
    Set the default parameters of the given model to the values
    specified in the params dictionary.
    If val is given, params has to be the name of a model property.
    New default values are used for all subsequently created instances
    of the model.
    """

    if val is not None:
        if isinstance(params, (str, SLILiteral)):
            params = {params: val}

    sps(params)
    sr('/{0} exch SetDefaults'.format(model))


@check_stack
def GetDefaults(model, keys=None):
    """
    Return a dictionary with the default parameters of the given
    model, specified by a string.
    If keys is given, it must be a string or a list of strings naming model properties.
    GetDefaults then returns a single value or a list of values belonging to the keys given.
    Examples:
    GetDefaults('iaf_neuron','V_m') -> -70.0
    GetDefaults('iaf_neuron',['V_m', 'model') -> [-70.0, 'iaf_neuron']
    """

    if keys is None:
        cmd = "/{0} GetDefaults".format(model)
    elif isinstance(keys, (str, SLILiteral)):
        cmd = '/{0} GetDefaults /{1} get'.format(model, keys)
    elif is_iterable(keys):
        keys_str = " ".join("/{0}".format(x) for x in keys)
        cmd = '/{0} GetDefaults  [ {1} ] {{ 1 index exch get }} Map exch pop'.format(model, keys_str)
    else:
        raise TypeError("keys should be either a string or an iterable")

    sr(cmd)
    return spp()


@check_stack
def CopyModel(existing, new, params=None):
    """
    Create a new model by copying an existing one. Default parameters
    can be given as params, or else are taken from existing.
    """
    
    if params is not None:
        sps(params)
        sr("/%s /%s 3 2 roll CopyModel" % (existing, new))
    else:
        sr("/%s /%s CopyModel" % (existing, new))


# -------------------- Functions for node handling

@check_stack
def Create(model, n=1, params=None):
    """
    Create n instances of type model. Parameters for the new nodes can
    are given as params (a single dictionary or a list of dictionaries
    with size n). If omitted, the model's defaults are used.
    """

    if isinstance(params, dict):
        cmd = "/%s 3 1 roll exch Create" % model
        sps(params)
    else:
        cmd = "/%s exch Create" % model

    sps(n)
    sr(cmd)

    last_gid = spp()
    gids = tuple(range(last_gid - n + 1, last_gid + 1))

    if params is not None and not isinstance(params, dict):
        try:
            SetStatus(gids, params)
        except:
            warnings.warn("SetStatus() call failed, but nodes have already been created! "
                          "The GIDs of the new nodes are: {0}.".format(gids))
            raise

    return gids


@check_stack
def SetStatus(nodes, params, val=None):
    """
    Set the parameters of nodes (identified by global ids) or
    connections (identified by handles as returned by
    GetConnections()) to params, which may be a single dictionary or a
    list of dictionaries. If val is given, params has to be the name
    of an attribute, which is set to val on the nodes/connections. val
    can be a single value or a list of the same size as nodes.
    """

    if not is_coercible_to_sli_array(nodes):
        raise TypeError("nodes must be a list of nodes or synapses")

    # This was added to ensure that the function is a nop (instead of,
    # for instance, raising an exception) when applied to an empty list,
    # which is an artifact of the API operating on lists, rather than
    # relying on language idioms, such as comprehensions
    #
    if len(nodes) == 0:
        return

    if val is not None:
        if isinstance(params, (str, SLILiteral)):
            if is_iterable(val) and not isinstance(val, (str, dict)):
                params = [{params: x} for x in val]
            else:
                params = {params: val}

    params = broadcast(params, len(nodes), (dict,), "params")
    if len(nodes) != len(params):
        raise TypeError("status dict must be a dict, or list of dicts of length 1 or len(nodes)")

    if is_sequence_of_connections(nodes):
        pcd(nodes)
    else:
        sps(nodes)

    sps(params)
    sr('2 arraystore')
    sr('Transpose { arrayload pop SetStatus } forall')


@check_stack
def GetStatus(nodes, keys=None):
    """
    Return the parameter dictionaries of the given list of nodes
    (identified by global ids) or connections (identified
    by handles as returned by GetConnections()). If keys is given, a
    list of values is returned instead. keys may also be a list, in
    which case the returned list contains lists of values.
    """

    if not is_coercible_to_sli_array(nodes):
        raise TypeError("nodes must be a list of nodes or synapses")

    if len(nodes) == 0:
        return nodes

    if keys is None:
        cmd = '{ GetStatus } Map'
    elif isinstance(keys, (str, SLILiteral)):
        cmd = '{{ GetStatus /{0} get }} Map'.format(keys)
    elif is_iterable(keys):
        keys_str = " ".join("/{0}".format(x) for x in keys)
        cmd = '{{ GetStatus }} Map {{ [ [ {0} ] ] get }} Map'.format(keys_str)
    else:
        raise TypeError("keys should be either a string or an iterable")

    if is_sequence_of_connections(nodes):
        pcd(nodes)
    else:
        sps(nodes)

    sr(cmd)

    return spp()


@check_stack
def GetLID(gid) :
    """
    Return the local id of a node with gid.
    GetLID(gid) -> lid
    """

    if len(gid) > 1:
        raise NESTError("GetLID() expects exactly one GID.")

    sps(gid[0])
    sr("GetLID")

    return spp()


# -------------------- Functions for connection handling

@check_stack
def FindConnections(source, target=None, synapse_model=None, synapse_type=None):
    """
    Return an array of identifiers for connections that match the
    given parameters. Only source is mandatory and must be a list of
    one or more nodes. If target and/or synapse_model is/are given,
    they must be single values, lists of length one or the same length
    as source. Use GetStatus()/SetStatus() to inspect/modify the found
    connections.

    Note: FindConnections() is deprecated and will be removed in the future.
          Use GetConnections() instead.

    Note: synapse_type is alias for synapse_model for backward compatibility
    """

    if synapse_model is not None and synapse_type is not None:
        raise NESTError("synapse_type is alias for synapse_model, cannot be used together.")

    if synapse_type is not None:
        synapse_model = synapse_type

    if target is None and synapse_model is None:
        params = [{"source": s} for s in source]
    elif target is None and synapse_model is not None:
        synapse_model = broadcast(synapse_model, len(source), (str,), "synapse_model")
        params = [{"source": s, "synapse_model": syn}
                  for s, syn in zip(source, synapse_model)]
    elif target is not None and synapse_model is None:
        target = broadcast(target, len(source), (int,), "target")
        params = [{"source": s, "target": t} for s, t in zip(source, target)]
    else:  # target is not None and synapse_model is not None
        target = broadcast(target, len(source), (int,), "target")
        synapse_model = broadcast(synapse_model, len(source), (str,), "synapse_model")
        params = [{"source": s, "target": t, "synapse_model": syn}
                  for s, t, syn in zip(source, target, synapse_model)]

    sps(params)
    sr("{FindConnections} Map Flatten")

    result = ({
        'source': int(src),
        'target_thread': int(tt),
        'synapse_modelid': int(sm),
        'port': int(prt)
    } for src, _, tt, sm, prt in spp())

    return tuple(result)


@check_stack
def GetConnections(source=None, target=None, synapse_model=None):
    """
    Return an array of connection identifiers.
    
    Parameters:
    source - list of source GIDs
    target - list of target GIDs
    synapse_model - string with the synapse model
    
    If GetConnections is called without parameters, all connections
    in the network are returned.

    If a list of source neurons is given, only connections from these
    pre-synaptic neurons are returned.

    If a list of target neurons is given, only connections to these
    post-synaptic neurons are returned.

    If a synapse model is given, only connections with this synapse
    type are returned.

    Any combination of source, target and synapse_model parameters
    is permitted.

    Each connection id is a 5-tuple or, if available, a NumPy
    array with the following five entries:
    source-gid, target-gid, target-thread, synapse-id, port
    
    Note: Only connections with targets on the MPI process executing
          the command are returned.
    """

    params = {}

    if source is not None:
        if not is_coercible_to_sli_array(source):
            raise TypeError("source must be a list of GIDs")
        params['source'] = source

    if target is not None:
        if not is_coercible_to_sli_array(target):
            raise TypeError("target must be a list of GIDs")
        params['target'] = target

    if synapse_model is not None:
        params['synapse_model'] = SLILiteral(synapse_model)

    sps(params)
    sr("GetConnections")

    return spp()


@check_stack
def Connect(pre, post, params=None, delay=None, model="static_synapse"):
    """
    Make one-to-one connections of type model between the nodes in
    pre and the nodes in post. pre and post have to be lists of the
    same length. If params is given (as dictionary or list of
    dictionaries), they are used as parameters for the connections. If
    params is given as a single float or as list of floats, it is used
    as weight(s), in which case delay also has to be given as float or
    as list of floats.
    """

    if len(pre) != len(post):
        raise NESTError("pre and post have to be the same length")

    # pre post Connect
    if params is None and delay is None:
        for s,d in zip(pre, post):
            sps(s)
            sps(d)
            sr('/%s Connect' % model)

    # pre post params Connect
    elif params is not None and delay is None:
        params = broadcast(params, len(pre), (dict,), "params")
        if len(params) != len(pre):
            raise NESTError("params must be a dict, or list of dicts of length 1 or len(pre).")

        for s,d,p in zip(pre, post, params) :
            sps(s)
            sps(d)
            sps(p)
            sr('/%s Connect' % model)

    # pre post w d Connect
    elif params is not None and delay is not None:
        params = broadcast(params, len(pre), (float,), "params")
        if len(params) != len(pre):
            raise NESTError("params must be a float, or list of floats of length 1 or len(pre) and will be used as weight(s).")
        delay = broadcast(delay, len(pre), (float,), "delay")
        if len(delay) != len(pre):
            raise NESTError("delay must be a float, or list of floats of length 1 or len(pre).")

        for s,d,w,dl in zip(pre, post, params, delay) :
            sps(s)
            sps(d)
            sps(w)
            sps(dl)
            sr('/%s Connect' % model)

    else:
        raise NESTError("Both 'params' and 'delay' have to be given.")


@check_stack
def ConvergentConnect(pre, post, weight=None, delay=None, model="static_synapse"):
    """
    Connect all neurons in pre to each neuron in post. pre and post
    have to be lists. If weight is given (as a single float or as list
    of floats), delay also has to be given as float or as list of
    floats.
    """

    if weight is None and delay is None:
        for d in post :
            sps(pre)
            sps(d)
            sr('/%s ConvergentConnect' % model)

    elif weight is not None and delay is not None:
        weight = broadcast(weight, len(pre), (float,), "weight")
        if len(weight) != len(pre):
            raise NESTError("weight must be a float, or sequence of floats of length 1 or len(pre)")
        delay = broadcast(delay, len(pre), (float,), "delay")
        if len(delay) != len(pre):
            raise NESTError("delay must be a float, or sequence of floats of length 1 or len(pre)")
        
        for d in post:
            sps(pre)
            sps(d)
            sps(weight)
            sps(delay)
            sr('/%s ConvergentConnect' % model)

    else:
        raise NESTError("Both 'weight' and 'delay' have to be given.")


@check_stack
def RandomConvergentConnect(pre, post, n, weight=None, delay=None, model="static_synapse", options=None):
    """
    Connect n randomly selected neurons from pre to each neuron in
    post. pre and post have to be lists. If weight is given (as a
    single float or as list of floats), delay also has to be given as
    float or as list of floats. options is a dictionary specifying
    options to the RandomConvergentConnect function: allow_autapses,
    allow_multapses.
    """

    if not isinstance(n, int):
        raise TypeError("number of neurons n should be an integer")

    # store current options, set desired options
    old_options = None
    error = False
    if options is not None:
        old_options = sli_func('GetOptions', '/RandomConvergentConnect',
                               litconv=True)
        del old_options['DefaultOptions'] # in the way when restoring
        sli_func('SetOptions', '/RandomConvergentConnect', options,
                 litconv=True)

    if weight is None and delay is None:
        sli_func(
            '/m Set /n Set /pre Set { pre exch n m RandomConvergentConnect } forall',
            post, pre, n, '/'+model, litconv=True)
    
    elif weight is not None and delay is not None:
        weight = broadcast(weight, n, (float,), "weight")
        if len(weight) != n:
            raise NESTError("weight must be a float, or sequence of floats of length 1 or n")
        delay = broadcast(delay, n, (float,), "delay")
        if len(delay) != n:
            raise NESTError("delay must be a float, or sequence of floats of length 1 or n")

        sli_func(
            '/m Set /d Set /w Set /n Set /pre Set { pre exch n w d m RandomConvergentConnect } forall',
            post, pre, n, weight, delay, '/'+model, litconv=True)
    
    else:
        error = True

    # restore old options
    if old_options is not None:
        sli_func('SetOptions', '/RandomConvergentConnect', old_options,
                 litconv=True)

    if error:
        raise NESTError("Both 'weight' and 'delay' have to be given.")


@check_stack
def DivergentConnect(pre, post, weight=None, delay=None, model="static_synapse"):
    """
    Connect each neuron in pre to all neurons in post. pre and post
    have to be lists. If weight is given (as a single float or as list
    of floats), delay also has to be given as float or as list of
    floats.
    """

    if weight is None and delay is None:
        for s in pre :
            sps(s)
            sps(post)
            sr('/%s DivergentConnect' % model)

    elif weight is not None and delay is not None:
        weight = broadcast(weight, len(post), (float,), "weight")
        if len(weight) != len(post):
            raise NESTError("weight must be a float, or sequence of floats of length 1 or len(post)")
        delay = broadcast(delay, len(post), (float,), "delay")
        if len(delay) != len(post):
            raise NESTError("delay must be a float, or sequence of floats of length 1 or len(post)")
        cmd='/%s DivergentConnect' % model
        for s in pre :
            sps(s)
            sps(post)
            sps(weight)
            sps(delay)
            sr(cmd)
    
    else:
        raise NESTError("Both 'weight' and 'delay' have to be given.")


@check_stack
def DataConnect(pre, params=None, model="static_synapse"):
    """
    Connect neurons from lists of connection data.

    Variant 1.
    pre: [gid_1, ... gid_n]
    params: [ {param1}, ..., {param_n} ]
    model= 'synapse_model'

    Variant 2:
    pre = [ {synapse_state1}, ..., {synapse_state_n}]
    params=None
    model=None

    Variant 1 of DataConnect connects each neuron in pre to the targets given in params, using synapse type model.
    The dictionary parames must contain at least the following keys:
    'target'
    'weight'
    'delay'
    each resolving to a list or numpy.ndarray of values. Depending on the synapse model, other parameters can be given
    in the same format. All arrays in params must have the same length as 'target'.

    Variant 2 of DataConnect will connect neurons according to a list of synapse status dictionaries,
    as obtained from GetStatus.
    Note: During connection, status dictionary misses will not raise errors, even if
    the kernel property 'dict_miss_is_error' is True.
    """

    if not is_coercible_to_sli_array(pre):
        raise TypeError("pre must be a list of nodes or connection dictionaries")

    if params is not None:

        if not is_coercible_to_sli_array(params):
            raise TypeError("params must be a list of dictionaries")

        cmd = '({0}) DataConnect_i_D_s '.format(model)

        for s, p in zip(pre, params):
            sps(s)
            sps(p)
            sr(cmd)
    else:
        # Call the variant where all connections are given explicitly

        # Disable dict checking, because most models can't re-use their own status dict
        dict_miss = GetKernelStatus('dict_miss_is_error')
        SetKernelStatus({'dict_miss_is_error': False})

        sps(pre)
        sr('DataConnect_a')

        SetKernelStatus({'dict_miss_is_error': dict_miss})


@check_stack
def RandomDivergentConnect(pre, post, n, weight=None, delay=None, model="static_synapse", options=None):
    """
    Connect each neuron in pre to n randomly selected neurons from
    post. pre and post have to be lists. If weight is given (as a
    single float or as list of floats), delay also has to be given as
    float or as list of floats. options is a dictionary specifying
    options to the RandomDivergentConnect function: allow_autapses,
    allow_multapses.
    """

    if not isinstance(n, int):
        raise TypeError("number of neurons n should be an integer")

    # store current options, set desired options
    old_options = None
    error = False
    if options is not None:
        old_options = sli_func('GetOptions', '/RandomDivergentConnect',
                               litconv=True)
        del old_options['DefaultOptions'] # in the way when restoring
        sli_func('SetOptions', '/RandomDivergentConnect', options,
                 litconv=True)

    if weight is None and delay is None:
        sli_func(
            '/m Set /n Set /post Set { n post m RandomDivergentConnect } forall',
            pre, post, n, '/'+model, litconv=True)

    elif weight is not None and delay is not None:
        weight = broadcast(weight, n, (float,), "weight")
        if len(weight) != n:
            raise NESTError("weight must be a float, or sequence of floats of length 1 or n")
        delay = broadcast(delay, n, (float,), "delay")
        if len(delay) != n:
            raise NESTError("delay must be a float, or sequence of floats of length 1 or n")

        sli_func(
            '/m Set /d Set /w Set /n Set /post Set { n post w d m RandomDivergentConnect } forall',
            pre, post, n, weight, delay, '/'+model, litconv=True)

    else:
        error = True

    # restore old options
    if old_options is not None:
        sli_func('SetOptions', '/RandomDivergentConnect', old_options,
                 litconv=True)

    if error:
        raise NESTError("Both 'weight' and 'delay' have to be given.")

def _is_subnet_instance(gids):
    "Returns true if all gids point to subnet or derived type."

    try:
        GetChildren(gids)
        return True
    except NESTError:
        return False

@check_stack
def CGConnect(pre, post, cg, parameter_map=None, model="static_synapse"):
    """
    Connect neurons from pre to neurons from post using connectivity
    specified by the connection generator cg. pre and post are either
    both lists containing 1 subnet, or lists of gids. parameter_map is
    a dictionary mapping names of values such as weight and delay to
    value set positions. This function is only available if NEST was
    compiled with support for libneurosim.
    """

    sr("statusdict/have_libneurosim ::")
    if not spp():
        raise NESTError("NEST was not compiled with support for libneurosim: CGConnect is not available.")

    if parameter_map is None:
        parameter_map = {}

    if _is_subnet_instance(pre[:1]):
        if not _is_subnet_instance(post[:1]):
            raise NESTError("if pre is a subnet, post also has to be a subnet")
        if len(pre) > 1 or len(post) > 1:
            raise NESTError("the length of pre and post has to be 1 if subnets are given")
        sli_func('CGConnect', cg, pre[0], post[0], parameter_map, '/'+model, litconv=True)
        
    else:
        sli_func('CGConnect', cg, pre, post, parameter_map, '/'+model, litconv=True)

@check_stack
def CGParse(xml_filename):
    """
    Parse an XML file and return the correcponding connection
    generator cg. The library to provide the parsing can be selected
    by CGSelectImplementation().
    """

    sr("statusdict/have_libneurosim ::")
    if not spp():
        raise NESTError("NEST was not compiled with support for libneurosim: CGParse is not available.")

    sps(xml_filename)
    sr("CGParse")
    return spp()

@check_stack
def CGSelectImplementation(tag, library):
    """
    Select a library to provide a parser for XML files and associate
    an XML tag with the library. XML files can be read by CGParse().
    """

    sr("statusdict/have_libneurosim ::")
    if not spp():
        raise NESTError("NEST was not compiled with support for libneurosim: CGSelectImplementation is not available.")

    sps(tag)
    sps(library)
    sr("CGSelectImplementation")

# -------------------- Functions for hierarchical networks

@check_stack
def PrintNetwork(depth=1, subnet=None) :
    """
    Print the network tree up to depth, starting at subnet. if
    subnet is omitted, the current subnet is used instead.
    """
    
    if subnet is None:
        subnet = CurrentSubnet()
    elif len(subnet) > 1:
        raise NESTError("PrintNetwork() expects exactly one GID.")

    sps(subnet[0])
    sr("%i PrintNetwork" % depth)


@check_stack
def CurrentSubnet() :
    """
    Returns the global id of the current subnet.
    """

    sr("CurrentSubnet")
    return (spp(), )


@check_stack
def ChangeSubnet(subnet) :
    """
    Make subnet the current subnet.
    """

    if len(subnet) > 1:
        raise NESTError("ChangeSubnet() expects exactly one GID.")

    sps(subnet[0])
    sr("ChangeSubnet")


@check_stack
def GetLeaves(subnets, properties=None, local_only=False) :
    """
    Return the global ids of the leaf nodes of the given subnets.
    
    Leaf nodes are all nodes that are not subnets.
    
    If properties is given, it must be a dictionary. Only global ids of nodes 
       matching the properties given in the dictionary exactly will be returned.
       Matching properties with float values (e.g. the membrane potential) may
       fail due to tiny numerical discrepancies and should be avoided.
       
    If local_only is True, only global ids of nodes simulated on the local MPI 
       process will be returned. By default, global ids of nodes in the entire
       simulation will be returned. This requires MPI communication and may
       slow down the script.
       
    See also: GetNodes, GetChildren
    """

    if properties is None:
        properties = {}
    func = 'GetLocalLeaves' if local_only else 'GetGlobalLeaves'
    return sli_func('/props Set { props %s } Map' % func, subnets, properties,
                    litconv=True)    


@check_stack
def GetNodes(subnets, properties=None, local_only=False):
    """
    Return the global ids of the all nodes of the given subnets.
    
    If properties is given, it must be a dictionary. Only global ids of nodes 
       matching the properties given in the dictionary exactly will be returned.
       Matching properties with float values (e.g. the membrane potential) may
       fail due to tiny numerical discrepancies and should be avoided.
       
    If local_only is True, only global ids of nodes simulated on the local MPI 
       process will be returned. By default, global ids of nodes in the entire
       simulation will be returned. This requires MPI communication and may
       slow down the script.
       
    See also: GetLeaves, GetChildren
    """

    if properties is None:
        properties = {}
    func = 'GetLocalNodes' if local_only else 'GetGlobalNodes'
    return sli_func('/props Set { props %s } Map' % func, subnets, properties,
                    litconv=True)    


@check_stack
def GetChildren(subnets, properties=None, local_only=False):
    """
    Return the global ids of the immediate children of the given subnets.
    
    If properties is given, it must be a dictionary. Only global ids of nodes 
       matching the properties given in the dictionary exactly will be returned.
       Matching properties with float values (e.g. the membrane potential) may
       fail due to tiny numerical discrepancies and should be avoided.
       
    If local_only is True, only global ids of nodes simulated on the local MPI 
       process will be returned. By default, global ids of nodes in the entire
       simulation will be returned. This requires MPI communication and may
       slow down the script.
       
    See also: GetNodes, GetLeaves
    """

    if properties is None:
        properties = {}
    func = 'GetLocalChildren' if local_only else 'GetGlobalChildren'
    return sli_func('/props Set { props %s } Map' % func, subnets, properties,
                    litconv=True)    

        
@check_stack
def GetNetwork(gid, depth):
    """
    Return a nested list with the children of subnet id at level
    depth. If depth==0, the immediate children of the subnet are
    returned. The returned list is depth+1 dimensional.
    """
    
    if len(gid)>1 :
        raise NESTError("GetNetwork() expects exactly one GID.")
    
    sps(gid[0])
    sps(depth)
    sr("GetNetwork")
    return spp()


@check_stack
def BeginSubnet(label=None, params=None):
    """
    Create a new subnet and change into it. A string argument can be
    used to name the new subnet A dictionary argument can be used to
    set the subnet's custom dict.
    """

    sn=Create("subnet")
    if label is not None:
        SetStatus(sn, "label", label)
    if params is not None:
        SetStatus(sn, "customdict", params)
    ChangeSubnet(sn)


@check_stack
def EndSubnet():
    """
    Change to the parent subnet and return the gid of the current.
    """

    csn=CurrentSubnet()
    parent=GetStatus(csn, "parent")

    if csn != parent:
        ChangeSubnet(parent)
        return csn
    else:
        raise NESTError("Unexpected EndSubnet(). Cannot go higher than the root node.")


@check_stack
def LayoutNetwork(model, dim, label=None, params=None):
    """
    Create a subnetwork of dimension dim with nodes of type model and
    return a list of ids. params is a dictionary, which will be set as
    customdict of the newly created subnet. It is not the parameters
    for the neurons in the subnetwork.
    """

    if isinstance(model, (str, SLILiteral)):
        sps(dim)
        sr('/%s exch LayoutNetwork' % model)
        if label is not None:
            sr("dup << /label (%s) >> SetStatus" % label)
        if params is not None:
            sr("dup << /customdict")
            sps(params)
            sr(">> SetStatus")
        return (spp(), )
    elif inspect.isfunction(model):
        BeginSubnet(label, params)
        if len(dim) == 1:
            [model() for _ in range(dim[0])]
        else:
            [LayoutNetwork(model, dim[1:]) for _ in range(dim[0])]
        gid = EndSubnet()
        return gid
    else:
        raise ValueError("model must be a string or a function")
