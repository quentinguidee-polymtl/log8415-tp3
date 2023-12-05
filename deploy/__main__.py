import asyncio
import logging

from deploy.setup import setup
from rich.logging import RichHandler

logger = logging.getLogger(__name__)


async def main():
    await setup()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, handlers=[RichHandler()])
    logger.info("Starting deployment")
    asyncio.run(main())
