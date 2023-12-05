import asyncio

from deploy.setup import setup


async def main():
    await setup()


if __name__ == "__main__":
    asyncio.run(main())
