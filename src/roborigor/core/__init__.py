"""Python 3.8 compatible core: schema, config, machine fingerprinting.

Everything in this package is imported inside benchmark client processes
(the LIBERO client is pinned to Python 3.8), so it must stay dependency-light
and 3.8 compatible. Statistics and analysis live outside core and may use 3.11+.
"""
