import psycopg2
import psycopg2.extras as extras
from psycopg2.extras import DictCursor, RealDictCursor
import pandas as pd
import json
import os
from dotenv import load_dotenv

class PostgresDB():

    def __init__(self, verbose=False, **kwargs):
        self.verbose = verbose
        self.conn = None
        
        if kwargs:
            self.connect(**kwargs)

    @classmethod
    def from_env(cls, verbose=False, env_file=None):
        """Create PostgresDB instance from environment variables"""
        if env_file:
            load_dotenv(env_file)
        else:
            load_dotenv()
        
        # Use Supabase connection string if available (for Supavisor)
        if os.getenv('SUPABASE_DB_URL'):
            # Parse connection string and extract components
            from urllib.parse import urlparse
            parsed = urlparse(os.getenv('SUPABASE_DB_URL'))
            db_config = {
                'host': parsed.hostname,
                'port': parsed.port or 5432,
                'database': parsed.path.lstrip('/'),
                'user': parsed.username,
                'password': parsed.password
            }
        else:
            db_config = {
                'host': os.getenv('LOCAL_DB_HOST', 'localhost'),
                'port': os.getenv('LOCAL_DB_PORT', 5432),
                'database': os.getenv('LOCAL_DB_NAME', 'htc'),
                'user': os.getenv('LOCAL_DB_USER', 'postgres'),
                'password': os.getenv('LOCAL_DB_PASSWORD')
            }
        
        return cls(verbose=verbose, **db_config)


    def connect(self, **kwargs):
        #kwargs = [host, port, database, user, password] 
        if 'username' in kwargs:
            kwargs['user'] = kwargs.pop('username')
        if 'type' in kwargs:
            kwargs.pop('type')

        # Add SSL mode for Supabase (required) if not already set
        if 'sslmode' not in kwargs and 'host' in kwargs:
            host = kwargs['host']
            # Add SSL for Supabase hosts
            if 'supabase.co' in host or 'pooler.supabase.com' in host:
                kwargs['sslmode'] = 'require'

        if kwargs is not None:
            self.conn = psycopg2.connect(**kwargs)
            self.conn.autocommit = True
        # else:
            # self.conn = psycopg2.connect(host, port, database, username, password)

        if self.verbose:
            print(f'DSN: {self.conn.dsn}')

    def select_dict(self, query):
        cursor = self.conn.cursor(cursor_factory=RealDictCursor)
        try:
            cursor.execute(query)
            rows = cursor.fetchall()
            
            return rows
        
        except (Exception, psycopg2.DatabaseError) as error:
            raise Exception(f"DB Error: {error}")

    def select_df(self, query):
        cursor = self.conn.cursor()
        try:
            cursor.execute(query)
            rows = cursor.fetchall()

            cols = [col.name for col in cursor.description]
            df = pd.DataFrame(data = rows, columns=cols)
            
            return df
        
        except (Exception, psycopg2.DatabaseError) as error:
            raise Exception(f"DB Error: {error}")

    def select(self, query):
        cursor = self.conn.cursor()
        try:
            cursor.execute(query)
            rows = cursor.fetchall()
            columns = [col[0] for col in cursor.description]
            return rows, columns
            
        except (Exception, psycopg2.DatabaseError) as error:
            raise Exception(f"DB Error: {error}")

    def execute(self, query):
        cursor = self.conn.cursor()
        try:
            cursor.execute(query)

        except (Exception, psycopg2.DatabaseError) as error:
            raise Exception(f"DB Error: {error}")

    def trunc_table(self, table_name):
        table_name = f'public.{table_name}' if "." not in table_name else table_name
        if self.table_exists(table_name):
            query = f"TRUNCATE TABLE {table_name}"
            self.execute(query)

            if self.verbose:
                print(f"{table_name} truncated.")

    def create_table_df(self, df, table_name):
        table_name = f'public.{table_name}' if "." not in table_name else table_name
        if len(df.index)>0:
            cols = ','.join([f'{c} varchar' for c in df.columns])
            query = f"CREATE TABLE IF NOT EXISTS {table_name}({cols})"
            self.execute(query)

            if self.verbose:
                print(f"{table_name} created.")

    def trunc_create_table_df(self, df, table_name):
        if len(df.index)>0:
            table_name = f'public.{table_name}' if "." not in table_name else table_name
            if self.table_exists(table_name):
                self.trunc_table(table_name)
            else:
                self.create_table_df(df, table_name)

    def insert_df(self, df, table_name):
        if len(df.index)>0:
            cursor = self.conn.cursor()
            table_name = f'public.{table_name}' if "." not in table_name else table_name
            df.columns = df.columns.str.replace("[@. -]","_", regex=True)

            try:                
                tuples = [tuple(None if pd.isna(val) or val == '' else val for val in row) for row in df.to_numpy()] 
                cols = ','.join(list(df.columns))
                query = "INSERT INTO %s(%s) VALUES %%s  ON CONFLICT DO NOTHING" % (table_name, cols)
                extras.execute_values(cursor, query, tuples)

            except (Exception, psycopg2.DatabaseError) as error:
                raise Exception(f"DB Error: {error}")

    def insert_dict(self, objects, table):
        if len(objects)>0:
            columns = ','.join(objects[0].keys())
            query = "INSERT INTO %s(%s) VALUES %%s  ON CONFLICT DO NOTHING" % (table, columns)
            values = [[value for value in object.values()] for object in objects]

            try:
                extras.execute_values(self.conn.cursor(), query, values)
                # self.connection.commit() 
            except (Exception, psycopg2.DatabaseError) as error:
                with open('data/db_error.json', "w", encoding="utf-8") as f:
                    json.dump(objects, f, indent=2, ensure_ascii=False)                
                raise Exception(f"DB Error: {error}")        

    def update_dict(self, objects, table):
        if len(objects)>0:
            columns = ','.join(objects[0].keys())
            values = [[value for value in object.values()] for object in objects]

            column_list = objects[0].keys()
            key_cols = self.table_key_cols(table)
            for key in key_cols:
                column_list.remove(key)

            # SQL query to execute
            query = "INSERT INTO %s(%s) VALUES %%s " % (table, columns)
            query += "ON CONFLICT (%s) DO UPDATE SET " % (','.join(key_cols))
            
            cols = ','.join(column_list)
            cols_ex = ', EXCLUDED.'.join(column_list)
            cols_ex = 'EXCLUDED.' + cols_ex
            query += "(%s) = (%s);" % (cols, cols_ex)

            try:
                extras.execute_values(self.conn.cursor(), query, values)
                # print(f'Rows were inserted.', flush=True)
            except (Exception, psycopg2.DatabaseError) as error:
                raise Exception(f"DB Error: {error}")  
            

    def table_exists(self, table_name, schema_name = 'public'):
        if "." in table_name:
            tbl = table_name.split('.')
            table_name = tbl[1]
            schema_name = tbl[0]

        sql = f"SELECT * FROM pg_catalog.pg_tables WHERE schemaname = '{schema_name}' AND tablename = '{table_name}'"
        try:
            rows, columns = self.select(sql)
            if len(rows)>0:
                return True
            else:
                return False
            
        except (Exception, psycopg2.DatabaseError) as error:
            raise Exception(f"DB Error: {error}")  
    
    def table_key_cols(self, table_name):
        sql = f"""SELECT conrelid::regclass AS table_name, 
                    conname AS primary_key, 
                    rtrim(ltrim(pg_get_constraintdef(oid) ,'PRIMARY KEY ('),')') key_cols
                FROM   pg_constraint 
                WHERE  contype = 'p' 
                AND    conrelid::regclass::text = '{table_name}';"""
        rows = self.select(sql)
        if len(rows[0])>0:
            cols = rows[0][0][2].split(', ')
            return cols