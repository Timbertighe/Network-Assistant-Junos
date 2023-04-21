"""
Creates tables in the database for the Junos plugin

Usage:
    Run independantly of the main plugin, to create the table in the database

Authentication:
    Requires permissions to access the database

Restrictions:
    Requires the 'pyodbc' module (install with pip)

To Do:
    None

Author:
    Luke Robertson - November 2022
"""

import pyodbc
import sys

sys.path.append('../../chatbot')
from config import GLOBAL  # noqa: E402


SQL_SERVER = GLOBAL['db_server']
DATABASE = GLOBAL['db_name']


# Connect to a database
#   Return the two SQL objects in a tuple
#   Return False if there's an error
def connect(server, db):
    try:
        conn = pyodbc.connect(
            'Driver={SQL Server};'
            'Server=%s;'
            'Database=%s;'
            'Trusted_Connection=yes;'
            % (server, db))

    except pyodbc.DataError as e:
        print("A data error has occurred")
        print(e)
        return False

    except pyodbc.OperationalError as e:
        print("An operational error has occurred while \
            connecting to the database")
        print("Make sure the specified server is correct, \
            and that you have permissions")

        # Parse the error code and message
        error = str(e).split(",", 1)[1].split(";")[0].split("[")
        code = error[1].replace("] ", "")
        message = error[4].split("]")[1].split(".")[0]

        # Print the error, and end the script
        print(f"Error code: {code}\n{message}")
        return False

    except pyodbc.IntegrityError as e:
        print("An Integrity error has occurred")
        print(e)
        return False

    except pyodbc.InternalError as e:
        print("An internal error has occurred")
        print(e)
        return False

    except pyodbc.ProgrammingError as e:
        print("A programming error has occurred")
        print("Check that the database name is correct, \
            and that the database exists")

        # Parse the error code and message
        error = str(e).split(",", 1)[1].split(";")[0].split("[")
        code = error[1].replace("] ", "")
        message = error[4].split("]")[1].split(".")[0]

        # Print the error, and end the script
        print(f"Error code: {code}\n{message}")
        return False

    except pyodbc.NotSupportedError as e:
        print("A 'not supported' error has occurred")
        print(e)
        return False

    except pyodbc.Error as e:
        print("A generic error has occurred")
        print(e)
        return False

    cursor = conn.cursor()

    return conn, cursor


# Neatly close the connection to the database
def close(connector):
    connector[1].close()
    connector[0].close()


# Create a table
#   Need the table name, column names, and column data types
#   The column names and types are sent as a dictionary
#   Return a tuple containing the sql objects
#   Return False if there's an error
def create_table(table, fields, connector):
    sql_string = (f'CREATE TABLE {table} (')
    for field in fields:
        sql_string += field + ' ' + fields[field] + ','
    sql_string += ')'

    try:
        connector[1].execute(sql_string)
    except Exception as e:
        print("SQL execution error")
        error = str(e).split(",", 1)[1].split(";")[0].split("[")
        code = error[1].replace("] ", "")
        message = error[4].split("]")[1].split(".")[0]

        print(code, message)

        if code == str(42000):
            print("Programming error. \
                Check that there are no typos in the SQL syntax")
        return False

    try:
        connector[0].commit()
    except Exception as e:
        print("SQL commit error")
        print(e)
        return False


# Create the tables
if __name__ == '__main__':
    # Connect to the DB
    sql_connector = connect(SQL_SERVER, DATABASE)

    # Create a dictionary of fields we want to create
    fields = {
        'id': 'int IDENTITY(1,1) PRIMARY KEY not null',
        'device': 'text null',
        'event': 'text not null',
        'description': 'text null',
        'logdate': 'date not null',
        'logtime': 'time not null',
        'source': 'binary(4) not null',
        'message': 'text null'
    }

    # Create the table
    create_table('junos_events', fields, sql_connector)

    # Cleanup
    close(sql_connector)


'''
Table Fields
------------

Event ID (primary key)
    - A unique ID to associate with each event
    - Type: char(12)
    - Allow null: no
Device
    - The name of the device, if applicable, that generated the event
    - Type: text
    - Allow null: yes
Site
    - The name of the site, if applicable, that the event was raised in
    - Type: text
    - Allow null: yes
Event
    - The event itself, eg 'SW_CONNECTED'
    - Type: text
    - Allow null: no
Description
    - A more detailed description of what happened \
        (not all events will have these)
    - Type: text
    - Allow null: yes
LogDate
    - The date of the event
    - Type: date
    - Allow null: no
LogTime
    - The time of the event
    - Type: time
    - Allow null: no
Source IP (only supports v4 for now)
    - The IP address that sent the alert
    - Type: binary(4)
    - Allow null: no
Chat message ID
    - The ID, as set by the Graph API of the message sent to teams \
        (not all will have a message sent)
    - Type: text
    - Allow null: yes


'''
