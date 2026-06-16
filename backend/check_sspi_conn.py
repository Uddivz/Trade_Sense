import asyncio
import asyncpg
import sys
import os

async def main():
    username = os.environ.get('USERNAME')
    print(f"Trying connection as Windows user: '{username}'")
    try:
        conn = await asyncpg.connect(
            user=username,
            host='localhost',
            port=5432,
            database='postgres',
            timeout=5
        )
        print("Connected successfully using SSPI / Windows user!")
        await conn.close()
    except Exception as e:
        print(f"Failed: {e}")
        sys.exit(1)

if __name__ == '__main__':
    asyncio.run(main())
