"""delegate-task-anywhere Hermes plugin entry point.

Hermes loads directory plugins under a synthetic ``hermes_plugins.*``
package.  Keep the fallback import so this module remains directly testable
from a checkout as well.
"""

if __package__ and __package__.startswith("hermes_plugins."):
    from .delegate_task_anywhere.schemas import DELEGATE_TASK_ANYWHERE
    from .delegate_task_anywhere.tools import handle_delegate_task_anywhere
else:
    from delegate_task_anywhere.schemas import DELEGATE_TASK_ANYWHERE
    from delegate_task_anywhere.tools import handle_delegate_task_anywhere


def register(ctx):
    """Register a separate tool; never shadow native delegate_task."""
    try:
        from .runtime_patch import install_runtime_patch
    except ImportError:
        # Direct-checkout tests may load this module outside Hermes' namespace.
        from runtime_patch import install_runtime_patch
    install_runtime_patch(ctx)

    ctx.register_tool(
        name="delegate_task_anywhere",
        toolset="delegate_task_anywhere",
        schema=DELEGATE_TASK_ANYWHERE,
        handler=handle_delegate_task_anywhere,
        emoji="🧭",
        description="Policy-controlled delegation across Hermes profiles, providers, and models.",
        override=False,
    )
