import asyncio
import asyncpg

async def init_dbs():
    conn = await asyncpg.connect(host='localhost', port=5433, user='odoo', password='odoo', database='postgres')
    for db in ['sln_warehouse', 'sln_warehouse_test', 'sln_warehouse_sample']:
        row = await conn.fetchrow("SELECT 1 FROM pg_database WHERE datname = $1", db)
        if not row:
            await conn.execute(f'CREATE DATABASE {db} OWNER odoo;')
            print(f'Created database: {db}')
        else:
            print(f'Database already exists: {db}')
    await conn.close()

if __name__ == '__main__':
    asyncio.run(init_dbs())
