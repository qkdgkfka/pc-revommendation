"""Legacy contract tests patch the actual service boundary after extraction."""
from contextlib import ExitStack
import sys
from unittest.mock import patch


class ServicePatch:
    def __init__(self, target, name, *args, **kwargs):
        self.target, self.name = target, name
        self.args, self.kwargs = args, kwargs
        self.stack = None

    def start(self):
        self.stack = ExitStack()
        original = getattr(self.target, self.name)
        result = self.stack.enter_context(patch.object(self.target, self.name, *self.args, **self.kwargs))
        for key, module in list(sys.modules.items()):
            if key.startswith('pcbuilder.') and module is not self.target and vars(module).get(self.name) is original:
                self.stack.enter_context(patch.object(module, self.name, result))
        return result

    def stop(self):
        if self.stack:
            self.stack.close()

    def __enter__(self):
        return self.start()

    def __exit__(self, *exc):
        self.stop()


def patch_backend(target, name, *args, **kwargs):
    if str(getattr(target, '__file__', '')).endswith('server_fixed.py'):
        return ServicePatch(target, name, *args, **kwargs)
    return patch.object(target, name, *args, **kwargs)
