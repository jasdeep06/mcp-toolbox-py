import importlib, inspect, textwrap, types, asyncio, traceback
from typing import Callable, Any, Awaitable, Dict

def load_hook_from_path(path: str) -> Callable[[Dict[str, Any]], Awaitable[None]]:
    mod, func = path.split(":")
    hook = getattr(importlib.import_module(mod), func)
    if not callable(hook):
        raise TypeError(f"{path} is not callable")
    return hook


async def run_hook(hook: Callable, params: Dict[str, Any]) -> None:
    try:
        if inspect.iscoroutinefunction(hook):
            await hook(params)
        else:
            # run sync hooks in a thread so we don’t block the event loop
            await asyncio.to_thread(hook, params)
    except Exception as exc:
        traceback.print_exc()
        raise

