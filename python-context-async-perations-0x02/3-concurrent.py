
"""
Concurrent Asynchronous Database Queries using asyncio and aiosqlite
"""

import asyncio
import aiosqlite
import sqlite3


async def async_fetch_users():
    """
    Asynchronously fetch all users from the database.
    
    Returns:
        list: List of all users in the database
    """
    try:
        async with aiosqlite.connect('example.db') as db:
            cursor = await db.execute("SELECT * FROM users")
            results = await cursor.fetchall()
            print("async_fetch_users() - Fetching all users:")
            for row in results:
                print(f"  ID: {row[0]}, Name: {row[1]}, Age: {row[2]}, Email: {row[3]}")
            return results
    except Exception as e:
        print(f"Error in async_fetch_users: {e}")
        return []


async def async_fetch_older_users():
    """
    Asynchronously fetch users older than 40 from the database.
    
    Returns:
        list: List of users older than 40
    """
    try:
        async with aiosqlite.connect('example.db') as db:
            cursor = await db.execute("SELECT * FROM users WHERE age > ?", (40,))
            results = await cursor.fetchall()
            print("async_fetch_older_users() - Fetching users older than 40:")
            for row in results:
                print(f"  ID: {row[0]}, Name: {row[1]}, Age: {row[2]}, Email: {row[3]}")
            return results
    except Exception as e:
        print(f"Error in async_fetch_older_users: {e}")
        return []


async def fetch_concurrently():
    """
    Execute both queries concurrently using asyncio.gather().
    
    Returns:
        tuple: Results from both queries
    """
    print("Starting concurrent database queries...")
    print("=" * 50)
    
    # Use asyncio.gather to run both queries concurrently
    try:
        all_users, older_users = await asyncio.gather(
            async_fetch_users(),
            async_fetch_older_users()
        )
        
        print("=" * 50)
        print("Concurrent queries completed successfully!")
        print(f"Total users fetched: {len(all_users)}")
        print(f"Users older than 40: {len(older_users)}")
        
        return all_users, older_users
    
    except Exception as e:
        print(f"Error in fetch_concurrently: {e}")
        return [], []


def setup_database():
    """
    Set up the database with sample data for testing.
    """
    try:
        conn = sqlite3.connect('example.db')
        cursor = conn.cursor()
        
        # Create users table if it doesn't exist
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                age INTEGER NOT NULL,
                email TEXT
            )
        ''')
        
        # Insert sample data with various ages including users older than 40
        sample_users = [
            (1, 'Alice', 22, 'alice@email.com'),
            (2, 'Bob', 28, 'bob@email.com'),
            (3, 'Charlie', 35, 'charlie@email.com'),
            (4, 'Diana', 45, 'diana@email.com'),
            (5, 'Eve', 19, 'eve@email.com'),
            (6, 'Frank', 52, 'frank@email.com'),
            (7, 'Grace', 33, 'grace@email.com'),
            (8, 'Henry', 41, 'henry@email.com'),
            (9, 'Ivy', 38, 'ivy@email.com'),
            (10, 'Jack', 48, 'jack@email.com')
        ]
        
        cursor.executemany('''
            INSERT OR REPLACE INTO users (id, name, age, email) 
            VALUES (?, ?, ?, ?)
        ''', sample_users)
        
        conn.commit()
        conn.close()
        print("Database setup completed successfully!")
        print("-" * 30)
        
    except sqlite3.Error as e:
        print(f"Database setup error: {e}")
    except Exception as e:
        print(f"Setup error: {e}")


def main():
    """
    Main function to demonstrate concurrent asynchronous database queries.
    """
    print("Concurrent Asynchronous Database Queries Demo")
    print("=" * 60)
    
    # Set up the database first
    setup_database()
    
    # Run the concurrent fetch operation
    try:
        results = asyncio.run(fetch_concurrently())
        
        print("\n" + "=" * 60)
        print("Demo completed successfully!")
        
        # Optional: Display summary
        all_users, older_users = results
        if all_users and older_users:
            print(f"\nSummary:")
            print(f"- Found {len(all_users)} total users")
            print(f"- Found {len(older_users)} users older than 40")
            
            # Show the names of older users
            older_names = [user[1] for user in older_users]
            print(f"- Older users: {', '.join(older_names)}")
    
    except Exception as e:
        print(f"Error running concurrent queries: {e}")


if __name__ == "__main__":
    main()
