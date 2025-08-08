import psycopg2

try:
    connection=psycopg2.connect(
       host='localhost',
       user='postgres',
       password='123',
       database='postgres'
    )
    print("Conexion exitosa")
except Exception as ex:
    print(ex)