"""SecureOTA device agent.

Verifies firmware images against a blockchain-anchored release registry before
allowing them to be installed.

Layering (dependencies point inward only)::

    cli  →  composition  →  application  →  domain
                     ↘  infrastructure  ↗
"""

__version__ = "1.0.0"
