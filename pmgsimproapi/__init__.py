from logging import getLogger

from .connect import SimProConnect

logger = getLogger()

try:
    from .api import SimProApi
except ModuleNotFoundError:
    logger.warn('Skipping asyncio support')

