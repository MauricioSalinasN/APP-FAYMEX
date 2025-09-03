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

# --- CONFIGURACIÓN DE TU BASE DE DATOS DE AZURE SQL ---
# Las credenciales sensibles se siguen tomando de las variables de entorno.
server = os.environ.get('AZURE_SQL_SERVER', 'server-bd-faymex.database.windows.net')
database = os.environ.get('AZURE_SQL_DATABASE', 'BD_Faymex')
username = os.environ.get('AZURE_SQL_USERNAME')
password = os.environ.get('AZURE_SQL_PASSWORD')
secret_key = os.environ.get('FLASK_SECRET_KEY')
app.secret_key = secret_key

# Valida que las variables de entorno más importantes existan
if not username or not password or not secret_key:
    # Si alguna variable falta, la aplicación no funcionará, lo que es un buen indicio de seguridad
    raise ValueError("Error: Las variables de entorno AZURE_SQL_USERNAME, AZURE_SQL_PASSWORD y FLASK_SECRET_KEY deben estar configuradas.")

driver = '{ODBC Driver 17 for SQL Server}'

def get_db_connection():
    """Función para establecer la conexión a la base de datos."""
    try:
        connection_string = f'DRIVER={driver};SERVER=tcp:{server},1433;DATABASE={database};UID={username};PWD={password}'
        conn = pyodbc.connect(connection_string, autocommit=True)
        logging.info("Conexión a la base de datos exitosa.")
        return conn
    except pyodbc.Error as ex:
        sqlstate = ex.args[0]
        logging.error(f"Error de base de datos: {sqlstate}. Asegúrate de que las credenciales y la IP del servidor sean correctas.")
        return None
    except Exception as e:
        logging.error(f"Error inesperado al conectar a la base de datos: {str(e)}")
        return None

# --- RUTAS DE LA APLICACIÓN ---

@app.route('/')
def home():
    """
    Ruta de inicio que sirve la página de entrevista HTML, sin mostrar datos existentes.
    """
    return render_template('datos_entrevista.html')

@app.route('/submit', methods=['POST'])
def submit():
    """
    Recibe los datos del formulario, los valida y los inserta en la base de datos de Azure SQL.
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

        # Obtener datos del formulario de manera robusta
        nombre_contacto = request.form.get('nombre_contacto')
        cargo = request.form.get('cargo')
        departamento = request.form.get('departamento')
        fecha_entrevista_str = request.form.get('fecha_entrevista')
        comentarios = request.form.get('comentarios')
        fecha_registro = datetime.now()

        # Manejar la opción "Otro" para el departamento
        if departamento == 'Otro':
            departamento = request.form.get('otro_departamento')

        # --- VALIDACIÓN DE DUPLICADOS ---
        query_check_duplicate = "SELECT COUNT(*) FROM datos_entrevista WHERE LOWER(nombre_contacto) = ?"
        cursor.execute(query_check_duplicate, (nombre_contacto.lower(),))
        
        if cursor.fetchone()[0] > 0:
            flash(f'Error: El contacto "{nombre_contacto}" ya existe en la base de datos.', 'error')
            logging.warning(f"Contacto duplicado: '{nombre_contacto}' no se guardó.")
            return redirect(url_for('home'))
        
        # --- PROCESAR LOS CHECKBOXES DE MANERA DINÁMICA ---
        # Se crea un diccionario que mapea los valores del formulario a los nombres de las columnas
        checkbox_mapping = {
            'proceso_manual': 'proceso_mas_largo_manual',
            'multiples_fuentes': 'proceso_mas_largo_multiples_fuentes',
            'espera_reportes': 'proceso_mas_largo_espera_reportes',
            'validacion_datos': 'proceso_mas_largo_validacion_datos',
            'desactualizada': 'desafio_info_no_actualizada',
            'falta_acceso': 'desafio_acceso_dificil',
            'datos_dispersos': 'desafio_datos_dispersos',
            'falta_reporte': 'desafio_falta_reporte',
            'dificil_generar_reporte': 'desafio_dificil_generar_reporte',
            'dependencia_manual': 'infraestructura_dependencia_manual',
            'falta_estandarizacion': 'infraestructura_falta_estandarizacion',
            'vulnerabilidades': 'infraestructura_vulnerabilidades',
            'poca_escalabilidad': 'infraestructura_poca_escalabilidad',
            'optimizacion_recursos': 'decision_optimizacion_recursos',
            'reduccion_costos': 'decision_reduccion_costos',
            'mejora_planificacion': 'decision_mejora_planificacion',
            'identificacion_ineficiencias': 'decision_identificacion_ineficiencias',
            'almacenamiento_disco_duro': 'almacen_disco_duro'
        }
        
        # Inicializa un diccionario para almacenar los valores de las columnas
        column_values = {col_name: 0 for col_name in checkbox_mapping.values()}
        
        # Recorre los datos del formulario y actualiza los valores de las columnas
        for form_key in request.form:
            if form_key in checkbox_mapping:
                column_values[checkbox_mapping[form_key]] = 1
        
        # Sentencia SQL para la inserción de datos
        columns = [
            'nombre_contacto', 'cargo', 'departamento', 'fecha_entrevista',
            'comentarios', 'fecha_registro'
        ] + list(column_values.keys())
        
        placeholders = ', '.join(['?'] * len(columns))
        columns_str = ', '.join(columns)
        
        query = f"INSERT INTO datos_entrevista ({columns_str}) VALUES ({placeholders})"
        
        # Lista de los valores para la consulta SQL
        params = (
            nombre_contacto, cargo, departamento, fecha_entrevista_str,
            comentarios, fecha_registro
        ) + tuple(column_values.values())

        # Ejecutar la consulta con los datos del formulario
        cursor.execute(query, params)
        conn.commit()
        
        logging.info("Datos insertados con éxito.")
        flash('¡Información guardada con éxito!', 'success')
        return redirect(url_for('home'))

    except pyodbc.Error as ex:
        sqlstate = ex.args[0]
        logging.error(f"Error de base de datos: {sqlstate}")
        flash("Ocurrió un error al guardar la información. Por favor, inténtelo de nuevo.", 'error')
        return redirect(url_for('home'))
    except Exception as e:
        logging.error(f"Error inesperado al guardar la información: {str(e)}")
        flash("Ocurrió un error inesperado. Por favor, inténtelo de nuevo.", 'error')
        return redirect(url_for('home'))
    finally:
        if conn:
            conn.close()
            logging.info("Conexión a la base de datos cerrada.")

if __name__ == '__main__':
    app.run(debug=True)
