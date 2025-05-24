
"""
Reusable Query Context Manager
"""

import sqlite3


class ExecuteQuery:
    """
    A reusable context manager that takes a query as input and executes it,
    managing both connection and query execution.
    """
    
    def __init__(self, database_name, query, parameters=None):
        """
        Initialize the ExecuteQuery context manager.
        
        Args:
            database_name (str): The name/path of the database file
            query (str): The SQL query to execute
            parameters (tuple): Parameters for the SQL query (optional)
        """
        self.database_name = database_name
        self.query = query
        self.parameters = parameters or ()
        self.connection = None
        self.cursor = None
        self.results = None
    
    def __enter__(self):
        """
        Enter the context manager - establish connection and execute query.
        
        Returns:
            list: The results of the executed query
        """
        try:
            self.connection = sqlite3.connect(self.database_name)
            self.cursor = self.connection.cursor()
            
            # Execute the query with parameters
            if self.parameters:
                self.cursor.execute(self.query, self.parameters)
            else:
                self.cursor.execute(self.query)
            
            # Fetch results for SELECT queries
            if self.query.strip().upper().startswith('SELECT'):
                self.results = self.cursor.fetchall()
            else:
                self.results = self.cursor.rowcount
            
            return self.results
        
        except sqlite3.Error as e:
            print(f"Database error: {e}")
            raise
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Exit the context manager - close database connection.
        
        Args:
            exc_type: Exception type if an exception occurred
            exc_val: Exception value if an exception occurred
            exc_tb: Exception traceback if an exception occurred
        """
        if self.cursor:
            self.cursor.close()
        if self.connection:
            if exc_type is None:
                # No exception occurred, commit any pending transactions
                self.connection.commit()
            else:
                # Exception occurred, rollback any pending transactions
                self.connection.rollback()
            self.connection.close()
        
        # Return False to propagate any exceptions
        return False


def main():
    """
    Demonstration of using the ExecuteQuery context manager.
    """
    # Create a sample database and table for testing
    try:
        # First, create the database and users table
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
        
        # Insert some sample data with various ages
        sample_users = [
            (1, 'Alice', 22, 'alice@email.com'),
            (2, 'Bob', 28, 'bob@email.com'),
            (3, 'Charlie', 35, 'charlie@email.com'),
            (4, 'Diana', 45, 'diana@email.com'),
            (5, 'Eve', 18, 'eve@email.com'),
            (6, 'Frank', 52, 'frank@email.com'),
            (7, 'Grace', 33, 'grace@email.com')
        ]
        
        cursor.executemany('''
            INSERT OR REPLACE INTO users (id, name, age, email) 
            VALUES (?, ?, ?, ?)
        ''', sample_users)
        
        conn.commit()
        conn.close()
        
        # Now use our ExecuteQuery context manager
        print("Using ExecuteQuery context manager:")
        print("-" * 40)
        
        # Execute query to get users older than 25
        query = "SELECT * FROM users WHERE age > ?"
        parameter = (25,)
        
        with ExecuteQuery('example.db', query, parameter) as results:
            print(f"Query: {query}")
            print(f"Parameter: age > {parameter[0]}")
            print("Results:")
            print("-" * 20)
            
            if results:
                for row in results:
                    print(f"ID: {row[0]}, Name: {row[1]}, Age: {row[2]}, Email: {row[3]}")
            else:
                print("No results found.")
        
        print("\n" + "=" * 50)
        
        # Additional example: Get all users
        print("Additional example - All users:")
        print("-" * 30)
        
        with ExecuteQuery('example.db', "SELECT * FROM users") as results:
            print("Query: SELECT * FROM users")
            print("Results:")
            print("-" * 20)
            
            for row in results:
                print(f"ID: {row[0]}, Name: {row[1]}, Age: {row[2]}, Email: {row[3]}")
    
    except sqlite3.Error as e:
        print(f"Database error: {e}")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
