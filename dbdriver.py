import psycopg2

class CursorWrapper(psycopg2.extensions.cursor):

    def execute(self, operation, parameters= []):
        try:
            psycopg2.extensions.cursor.execute(self, operation, parameters)
        except psycopg2.IntegrityError as e:
            print e
            


class ConnectionWrapper(object):

    def __init__(self, login):
        self.CONN = psycopg2.connect(login)
        self.CONN.autocommit = True
        self.CUR = CursorWrapper(self.CONN)


    def __enter__(self):
        return self.CUR

    def __exit__(self, type, value, traceback):
        self.CUR.close() 
        self.CONN.close() 

