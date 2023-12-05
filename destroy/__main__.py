import logging

from rich.logging import RichHandler

from destroy.destroy import main

logger = logging.getLogger(__name__)

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, handlers=[RichHandler()])
    logger.info("Destroying environment")
    main()
