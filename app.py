# app.py - Backend de la aplicación web
# Este archivo maneja la lógica del servidor para conectar a la base de datos de Azure SQL.

import pyodbc
from flask import Flask, render_template, request, redirect, url_for, flash
from datetime import datetime
import logging
import os

# Configuración de logging para ver lo que sucede en la terminal
logging.basicConfig(level=logging.INFO)

# Inicializa la aplicación Flask
app = Flask(__name__)

# La clave secreta de Flask debe ser una variable de entorno
app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY')

# --- CONFIGURACIÓN DE TU BASE DE DATOS DE AZURE SQL ---
server = os.environ.get('AZURE_SQL_SERVER')
database = os.environ.get('AZURE_SQL_DATABASE')
username = os.environ.get('AZURE_SQL_USERNAME')
password = os.environ.get('AZURE_SQL_PASSWORD')

# Valida que las variables de entorno más importantes existan
if not all([server, database, username, password, app.config['SECRET_KEY']]):
    raise ValueError("Error: Las variables de entorno para la base de datos y la clave secreta de Flask deben estar configuradas.")

driver = '{ODBC Driver 17 for SQL Server}'

def get_db_connection():
    """Función para establecer la conexión a la base de datos."""
    try:
        connection_string = f'DRIVER={driver};SERVER=tcp:{server},1433;DATABASE={database};UID={username};PWD={password}'
        conn = pyodbc.connect(connection_string)
        logging.info("Conexión a la base de datos exitosa.")
        return conn
    except pyodbc.Error as ex:
        sqlstate = ex.args[0]
        logging.error(f"Error de base de datos con SQLSTATE: {sqlstate}")
        logging.error(f"Mensaje de error: {ex.args[1]}")
        return None
    except Exception as e:
        logging.error(f"Error inesperado al conectar a la base de datos: {str(e)}")
        return None

# Definición de las columnas de la base de datos para los checkboxes
CHECKBOX_COLUMNS = {
    'desafio_info': [
        'desafio_datos_dispersos', 'desafio_acceso_dificil', 'desafio_falta_reporte',
        'desafio_info_no_actualizada', 'desafio_dificil_generar_reporte'
    ],
    'proceso_mas_largo': [
        'proceso_mas_largo_manual', 'proceso_mas_largo_multiples_fuentes',
        'proceso_mas_largo_espera_reportes', 'proceso_mas_largo_validacion_datos'
    ],
    'infraestructura_desafio': [
        'infraestructura_dependencia_manual', 'infraestructura_falta_estandarizacion',
        'infraestructura_vulnerabilidades', 'infraestructura_poca_escalabilidad'
    ],
    'decision': [
        'decision_optimizacion_recursos', 'decision_reduccion_costos',
        'decision_mejora_planificacion', 'decision_identificacion_ineficiencias'
    ]
}

@app.route('/')
def home():
    """Ruta para mostrar el formulario de entrevista."""
    return render_template('index.html')

@app.route('/datos')
def ver_datos():
    """Ruta para mostrar los datos de las entrevistas guardadas."""
    conn = get_db_connection()
    if conn is None:
        flash("Error: No se pudo conectar a la base de datos para mostrar los datos.", 'error')
        return render_template('datos_entrevista.html', interviews=[])
    
    try:
        cursor = conn.cursor()
        sql_query = "SELECT * FROM datos_entrevista ORDER BY fecha_registro DESC"
        cursor.execute(sql_query)
        
        columns = [column[0] for column in cursor.description]
        interviews = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        return render_template('datos_entrevista.html', interviews=interviews)
    except Exception as e:
        logging.error(f"Error al cargar los datos: {str(e)}")
        flash("Ocurrió un error al cargar los datos.", 'error')
        return render_template('datos_entrevista.html', interviews=[])
    finally:
        if conn:
            conn.close()

@app.route('/submit', methods=['POST'])
def submit():
    """
    Recibe los datos del formulario y los inserta en la base de datos.
    El método 'POST' es crucial para aceptar los datos del formulario.
    """
    conn = None
    try:
        logging.info("--- INICIANDO PROCESO DE GUARDADO ---")
        
        # Conectar a la base de datos
        conn = get_db_connection()
        if conn is None:
            flash("Error de conexión a la base de datos.", 'error')
            return redirect(url_for('home'))

        cursor = conn.cursor()
        
        # Obtener datos básicos del formulario
        nombre_contacto = request.form.get('nombre_contacto')
        cargo = request.form.get('cargo')
        departamento = request.form.get('departamento')
        comentarios = request.form.get('comentarios')
        
        # Formatear la fecha para la base de datos
        fecha_entrevista = request.form.get('fecha_entrevista')
        fecha_registro = datetime.now()

        # Manejar el campo "Otro" para el departamento
        if departamento == 'Otro':
            departamento = request.form.get('otro_departamento')

        # --- VALIDACIÓN DE DUPLICADOS ---
        query_check_duplicate = "SELECT COUNT(*) FROM datos_entrevista WHERE LOWER(nombre_contacto) = ?"
        cursor.execute(query_check_duplicate, (nombre_contacto.lower(),))
        
        if cursor.fetchone()[0] > 0:
            flash(f'Error: El contacto "{nombre_contacto}" ya existe en la base de datos.', 'error')
            return redirect(url_for('home'))
            
        # --- PROCESAR LOS CHECKBOXES DE MANERA DINÁMICA ---
        # Inicializamos un diccionario con todos los valores en 0
        checkbox_values = {}
        for group in CHECKBOX_COLUMNS.values():
            for column in group:
                checkbox_values[column] = 0

        # Iteramos sobre los datos del formulario para poner un 1 si la casilla fue marcada
        for key, value in request.form.items():
            for group_columns in CHECKBOX_COLUMNS.values():
                if value in group_columns:
                    checkbox_values[value] = 1

        # Construir la consulta de inserción de forma dinámica
        columns = [
            'nombre_contacto', 'cargo', 'departamento', 'fecha_entrevista',
            'comentarios', 'fecha_registro'
        ] + list(checkbox_values.keys())
        
        placeholders = ', '.join(['?'] * len(columns))
        columns_str = ', '.join(columns)

        query = f"INSERT INTO datos_entrevista ({columns_str}) VALUES ({placeholders})"
        
        # Preparar los parámetros de la consulta
        params = (
            nombre_contacto,
            cargo,
            departamento,
            fecha_entrevista,
            comentarios,
            fecha_registro
        ) + tuple(checkbox_values.values())

        # Ejecutar la consulta con los datos del formulario
        cursor.execute(query, params)
        conn.commit()
        
        flash('¡Información guardada con éxito!', 'success')
        return redirect(url_for('ver_datos'))

    except pyodbc.Error as ex:
        sqlstate = ex.args[0]
        logging.error(f"Error de base de datos: {sqlstate}")
        conn.rollback()
        flash("Ocurrió un error al guardar la información. Por favor, inténtelo de nuevo.", 'error')
    except Exception as e:
        logging.error(f"Error inesperado al guardar la información: {str(e)}")
        flash("Ocurrió un error inesperado. Por favor, inténtelo de nuevo.", 'error')
    finally:
        if conn:
            conn.close()
            logging.info("Conexión a la base de datos cerrada.")

if __name__ == '__main__':
    # No usar debug=True en producción, solo para desarrollo local
    app.run(debug=True)