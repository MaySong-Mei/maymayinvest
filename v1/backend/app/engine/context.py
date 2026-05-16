"""LiveContext — implements strategy.Context for the live event loop.

Subscribes to the data bus, calls BrokerAdapter for fills via engine.router
(which runs pre-trade risk checks).
"""
