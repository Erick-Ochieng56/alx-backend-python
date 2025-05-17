# Python Generators Project

This project demonstrates advanced usage of Python generators to efficiently handle large datasets and perform memory-efficient data processing operations.

## Overview

Python generators provide a memory-efficient way to work with large datasets by using the `yield` keyword to create functions that can pause and resume their execution state. This project shows how generators can be used in real-world scenarios involving database operations.

## Project Structure

The project consists of several Python scripts that implement different generator functionality:

1. `seed.py` - Sets up the MySQL database and populates it with sample user data
2. `0-stream_users.py` - Streams user data one row at a time
3. `1-batch_processing.py` - Processes data in batches for improved efficiency
4. `2-lazy_paginate.py` - Implements lazy loading of paginated data
5. `4-stream_ages.py` - Calculates average age without loading entire dataset

## Key Concepts Demonstrated

- **Memory Efficiency**: Using generators to process data without loading everything into memory
- **Lazy Evaluation**: Loading data only when needed using generator functions
- **Batch Processing**: Handling data in chunks for improved performance
- **Aggregation**: Calculating statistics on large datasets efficiently

## Installation and Setup

1. Ensure you have Python 3.x installed
2. Install required packages:
   ```
   pip install mysql-connector-python
   ```
3. Set up MySQL server locally with user 'root' and password 'root'
4. Run the seeding script to create the database and populate it:
   ```
   python seed.py
   ```

## Usage Examples

### Streaming users one by one:
```python
from itertools import islice
from 0-stream_users import stream_users

# Get the first 5 users
for user in islice(stream_users(), 5):
    print(user)
```

### Processing users in batches:
```python
from 1-batch_processing import batch_processing

# Process users in batches of 50
batch_processing(50)
```

### Lazy loading paginated data:
```python
from 2-lazy_paginate import lazy_pagination

# Get pages of 100 users each
for page in lazy_pagination(100):
    # Process each page
    for user in page:
        print(user)
```

### Calculating average age efficiently:
```python
from 4-stream_ages import calculate_average_age

# Calculate average age without loading all data at once
calculate_average_age()
```

## Benefits of Using Generators

1. **Reduced Memory Usage**: Only keeps necessary data in memory
2. **Improved Performance**: Better handling of large datasets
3. **Real-time Processing**: Can process data as it becomes available
4. **Code Simplicity**: Makes complex data processing tasks more readable
