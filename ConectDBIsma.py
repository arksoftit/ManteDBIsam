import pyodbc

def conectar_bd():
    """Establece conexión con la base de datos BDIsam vía ODBC"""
    try:
        # Usando un DSN configurado
        conexion = pyodbc.connect('DSN=NombreDeTuDSN;UID=usuario;PWD=contraseña')
        
        # O también podrías usar una cadena de conexión directa
        # conexion = pyodbc.connect('DRIVER={Driver BDIsam};SERVER=...;DATABASE=...')
        
        return conexion
    except Exception as e:
        print(f"Error al conectar: {e}")
        return None