import asyncio
import asyncpg
import sys

async def main():
    # Try different passwords for user 'postgres'
    passwords = ['postgres', 'admin', 'root', 'tradesense_pass', '']
    conn = None
    connected_pass = None
    
    for pwd in passwords:
        try:
            print(f"Trying user=postgres password={pwd}...")
            conn = await asyncpg.connect(
                user='postgres',
                password=pwd,
                host='localhost',
                port=5432,
                database='postgres',
                timeout=5
            )
            connected_pass = pwd
            print(f"Connected successfully using password: '{pwd}'")
            break
        except Exception as e:
            print(f"Failed: {e}")
            
    if conn is None:
        print("Could not connect to postgres database with any default password.")
        sys.exit(1)
        
    # Check if tradesense database exists
    try:
        rows = await conn.fetch("SELECT 1 FROM pg_database WHERE datname = 'tradesense'")
        if not rows:
            print("Database 'tradesense' does not exist. Creating it...")
            await conn.execute("CREATE DATABASE tradesense")
            print("Database 'tradesense' created successfully!")
        else:
            print("Database 'tradesense' already exists.")
            
        # Check if tradesense_user exists
        user_rows = await conn.fetch("SELECT 1 FROM pg_roles WHERE rolname = 'tradesense_user'")
        if not user_rows:
            print("User 'tradesense_user' does not exist. Creating it...")
            await conn.execute("CREATE USER tradesense_user WITH PASSWORD 'tradesense_pass'")
            await conn.execute("ALTER USER tradesense_user WITH SUPERUSER") # Make superuser for dev ease
            print("User 'tradesense_user' created successfully!")
        else:
            print("User 'tradesense_user' already exists.")
            
    except Exception as e:
        print(f"Error during db setup: {e}")
    finally:
        await conn.close()

if __name__ == '__main__':
    asyncio.run(main())
