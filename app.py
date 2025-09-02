import os
import sys
import pyodbc
from flask import Flask, render_template, request, redirect, url_for, flash

app = Flask(__name__)

# Configuración de variables de entorno para una mayor seguridad
try:
    AZURE_SQL_SERVER = os.environ.get('AZURE_SQL_SERVER', 'server-bd-faymex.database.windows.net')
    AZURE_SQL_DATABASE = os.environ.get('AZURE_SQL_DATABASE', 'faymex_entrevista')
    AZURE_SQL_USERNAME = os.environ['AZURE_SQL_USERNAME']
    AZURE_SQL_PASSWORD = os.environ['AZURE_SQL_PASSWORD']
    FLASK_SECRET_KEY = os.environ['FLASK_SECRET_KEY']
    app.secret_key = FLASK_SECRET_KEY
except KeyError as e:
    raise ValueError(f"Error: La variable de entorno {e} debe estar configurada.")

# Función para obtener una conexión a la base de datos
def get_db_connection():
    try:
        connection_string = f'DRIVER={{ODBC Driver 18 for SQL Server}};SERVER={AZURE_SQL_SERVER};DATABASE={AZURE_SQL_DATABASE};UID={AZURE_SQL_USERNAME};PWD={AZURE_SQL_PASSWORD}'
        cnxn = pyodbc.connect(connection_string, autocommit=True)
        return cnxn
    except pyodbc.Error as ex:
        sqlstate = ex.args[0]
        # IM002 - Driver ODBC no encontrado
        if sqlstate == 'IM002':
            flash("Error de base de datos inesperado con SQLSTATE: IM002. Por favor, instala el controlador ODBC.", 'error')
        # 28000 - Credenciales de login incorrectas
        elif sqlstate == '28000':
            flash("Error de base de datos: Usuario o contraseña incorrectos.", 'error')
        # 08001 - Error de conexión al servidor
        elif sqlstate == '08001':
            flash("Error de conexión: No se pudo conectar al servidor de base de datos.", 'error')
        else:
            flash(f"Error de base de datos inesperado con SQLSTATE: {sqlstate}. Por favor, contacta a soporte.", 'error')
        return None

# Ruta principal que muestra el formulario
@app.route('/')
def index():
    return render_template('index.html')

# Ruta para guardar los datos del formulario
@app.route('/guardar_entrevista', methods=['POST'])
def guardar_entrevista():
    cnxn = get_db_connection()
    if not cnxn:
        return redirect(url_for('index'))

    try:
        cursor = cnxn.cursor()
        
        # Recolectar datos del formulario
        nombre_contacto = request.form.get('nombre_contacto').upper()
        cargo = request.form.get('cargo').upper()
        departamento = request.form.get('departamento')
        if departamento == 'Otro':
            departamento = request.form.get('otro_departamento').upper()
        fecha_entrevista = request.form.get('fecha_entrevista')
        comentarios = request.form.get('comentarios')
        
        # Manejar las casillas de verificación (checkboxes)
        proceso_mas_largo = ', '.join(request.form.getlist('proceso_mas_largo'))
        desafio_info = ', '.join(request.form.getlist('desafio_info'))
        infraestructura_desafio = ', '.join(request.form.getlist('infraestructura_desafio'))
        decision = ', '.join(request.form.getlist('decision'))

        # Validar si el contacto ya existe para evitar duplicados
        cursor.execute("SELECT COUNT(*) FROM datos_entrevista WHERE nombre_contacto = ?", nombre_contacto)
        if cursor.fetchone()[0] > 0:
            flash(f'El contacto "{nombre_contacto}" ya existe en la base de datos.', 'error')
            return redirect(url_for('index'))

        # Insertar los datos en la base de datos
        sql_insert = """
        INSERT INTO datos_entrevista (
            nombre_contacto, cargo, departamento, fecha_entrevista,
            proceso_mas_largo, desafio_info, infraestructura_desafio,
            decision, comentarios
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        cursor.execute(
            sql_insert,
            (nombre_contacto, cargo, departamento, fecha_entrevista,
             proceso_mas_largo, desafio_info, infraestructura_desafio,
             decision, comentarios)
        )
        cnxn.commit()
        
        flash('Entrevista guardada con éxito!', 'success')

    except pyodbc.Error as ex:
        sqlstate = ex.args[0]
        # 23000 - Restricción de unicidad violada
        if sqlstate == '23000':
            flash('Error: El contacto ya existe en la base de datos.', 'error')
        else:
            flash(f"Error al guardar los datos: {ex.args[1]}", 'error')
            print(f"Error de base de datos: {ex.args[1]}") # Imprimir el error en la terminal para depuración
    finally:
        if cnxn:
            cnxn.close()
    
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)