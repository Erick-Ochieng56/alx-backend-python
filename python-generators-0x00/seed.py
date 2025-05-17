#!/usr/bin/python3
"""
Database seeding module for Python generators project.
Creates database, tables, and populates with sample data.
"""
import mysql.connector
import csv
import os
from mysql.connector import Error


def connect_db():
    """Connects to the MySQL database server"""
    try:
        connection = mysql.connector.connect(
            host="localhost",
            user="root",
            password="root"
        )
        return connection
    except Error as e:
        print(f"Error connecting to MySQL: {e}")
        return None


def create_database(connection):
    """Creates ALX_prodev database if it doesn't exist"""
    try:
        cursor = connection.cursor()
        cursor.execute("CREATE DATABASE IF NOT EXISTS ALX_prodev")
        cursor.close()
    except Error as e:
        print(f"Error creating database: {e}")


def connect_to_prodev():
    """Connects to the ALX_prodev database"""
    try:
        connection = mysql.connector.connect(
            host="localhost",
            user="root",
            password="root",
            database="ALX_prodev"
        )
        return connection
    except Error as e:
        print(f"Error connecting to ALX_prodev: {e}")
        return None


def create_table(connection):
    """Creates user_data table if it doesn't exist"""
    try:
        cursor = connection.cursor()
        create_table_query = """
        CREATE TABLE IF NOT EXISTS user_data (
            user_id VARCHAR(36) PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            email VARCHAR(255) NOT NULL,
            age INT NOT NULL,
            INDEX (user_id)
        )
        """
        cursor.execute(create_table_query)
        connection.commit()
        cursor.close()
        print("Table user_data created successfully")
    except Error as e:
        print(f"Error creating table: {e}")


def insert_data(connection, data_file):
    """Inserts data from CSV file into user_data table"""
    try:
        cursor = connection.cursor()
        
        # Check if the file exists
        if not os.path.exists(data_file):
            print(f"Error: File {data_file} does not exist")
            return
        
        # Read data from CSV and insert into table
        with open(data_file, 'r') as file:
            csv_reader = csv.reader(file)
            next(csv_reader)  # Skip header row
            
            for row in csv_reader:
                # Check if record already exists
                check_query = "SELECT user_id FROM user_data WHERE user_id = %s"
                cursor.execute(check_query, (row[0],))
                result = cursor.fetchone()
                
                if not result:
                    insert_query = """
                    INSERT INTO user_data (user_id, name, email, age)
                    VALUES (%s, %s, %s, %s)
                    """
                    cursor.execute(insert_query, (row[0], row[1], row[2], int(row[3])))
            
            connection.commit()
        cursor.close()
    except Error as e:
        print(f"Error inserting data: {e}")
    except Exception as e:
        print(f"Error: {e}")
