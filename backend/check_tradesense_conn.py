import asyncio
import asyncpg
import sys

async def main():
    try:
        conn = await asyncpg.connect(
            user='tradesense_user',
            password='tradesense_pass',
            host='localhost',
            port=5432,
            database='tradesense',
            timeout=5
        )
        print("Connected successfully using tradesense_user/tradesense_pass on tradesense DB!")
        await conn.close()
    except Exception as e:
        print(f"Failed to connect: {e}")
        sys.exit(1)

if __name__ == '__main__':
    asyncio.run(main())
