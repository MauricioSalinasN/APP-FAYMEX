# Este archivo maneja la lógica del servidor para conectar a la base de datos de Azure SQL.

# Importar las bibliotecas necesarias
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
# Las variables de entorno son cruciales para la seguridad en producción
server = os.environ.get('AZURE_SQL_SERVER', 'server-bd-faymex.database.windows.net')
database = os.environ.get('AZURE_SQL_DATABASE', 'BD_Faymex')
username = os.environ.get('AZURE_SQL_USERNAME')
password = os.environ.get('AZURE_SQL_PASSWORD')
secret_key = os.environ.get('FLASK_SECRET_KEY')
app.secret_key = secret_key

if not username or not password or not secret_key:
    # Esto asegura que las credenciales no se queden vacías
    raise ValueError("Error: Las variables de entorno AZURE_SQL_USERNAME, AZURE_SQL_PASSWORD y FLASK_SECRET_KEY deben estar configuradas.")

# Asegúrate de que el driver coincida con la versión que tienes instalada
driver = '{ODBC Driver 18 for SQL Server}'
connection_string = 'DRIVER={0};SERVER=tcp:{1},1433;DATABASE={2};UID={3};PWD={4}'.format(driver, server, database, username, password)

def get_db_connection():
    """Función para establecer la conexión a la base de datos."""
    conn = None
    try:
        logging.info(f"Intentando conectar a: {server}/{database} con usuario: {username}")
        conn = pyodbc.connect(connection_string)
        logging.info("Conexión a la base de datos exitosa.")
        return conn
    except pyodbc.Error as ex:
        sqlstate = ex.args[0]
        logging.error(f"Error de base de datos: {sqlstate}")
        
        # Flashea un mensaje de error detallado al frontend
        if sqlstate == '28000':
            flash("Error 28000: Las credenciales (usuario/contraseña) son incorrectas. Por favor, revisa tus variables de entorno en Azure.", 'error')
        elif sqlstate == '08001':
            flash("Error 08001: No se puede conectar al servidor. Revisa si tu IP está permitida en el firewall de Azure SQL o si la base de datos está en línea.", 'error')
        else:
            flash(f"Error de base de datos inesperado con SQLSTATE: {sqlstate}. Por favor, contacta a soporte.", 'error')
        
        return None
    except Exception as e:
        logging.error(f"Error inesperado al conectar a la base de datos: {str(e)}")
        flash("Ocurrió un error inesperado al conectar a la base de datos. Por favor, inténtalo de nuevo más tarde.", 'error')
        return None

def get_form_data_as_booleans(form_list, mapping):
    """
    Convierte los datos de las casillas de verificación de una lista de formulario
    a un diccionario de valores 1 o 0.
    """
    return {
        db_col: 1 if form_name in form_list else 0
        for form_name, db_col in mapping.items()
    }

# --- RUTAS DE LA APLICACIÓN ---

@app.route('/')
def home():
    """
    Ruta de inicio que sirve la página de entrevista HTML.
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
        conn = get_db_connection()
        if conn is None:
            # El mensaje de error ya fue flasheado por get_db_connection()
            return redirect(url_for('home'))

        cursor = conn.cursor()
        logging.info("Conexión exitosa. Recibiendo datos del formulario.")

        nombre_contacto = request.form.get('nombre_contacto')
        
        # Validación de duplicados (ya implementada, ¡excelente!)
        query_check_duplicate = "SELECT COUNT(*) FROM datos_entrevista WHERE LOWER(nombre_contacto) = ?"
        cursor.execute(query_check_duplicate, (nombre_contacto.lower(),))
        
        if cursor.fetchone()[0] > 0:
            flash(f'Error: El contacto "{nombre_contacto}" ya existe en la base de datos.', 'error')
            logging.warning(f"Contacto duplicado: '{nombre_contacto}' no se guardó.")
            return redirect(url_for('home'))

        # --- CONTINUAR CON LA INSERCIÓN SI NO ES DUPLICADO ---
        cargo = request.form.get('cargo')
        departamento = request.form.get('departamento')
        fecha_entrevista_str = request.form.get('fecha_entrevista')
        comentarios = request.form.get('comentarios')
        fecha_registro = datetime.now()

        # Convertir la cadena de fecha a un objeto datetime
        fecha_entrevista = datetime.strptime(fecha_entrevista_str, '%Y-%m-%d').date() if fecha_entrevista_str else None
        departamento = request.form.get('otro_departamento') if departamento == 'Otro' else departamento

        # Mapeos para las casillas de verificación (refactorizados para mayor claridad)
        proceso_mas_largo_map = {
            'proceso_manual': 'proceso_mas_largo_manual',
            'multiples_fuentes': 'proceso_mas_largo_multiples_fuentes',
            'espera_reportes': 'proceso_mas_largo_espera_reportes',
            'validacion_datos': 'proceso_mas_largo_validacion_datos'
        }
        
        desafio_info_map = {
            'desactualizada': 'desafio_info_no_actualizada',
            'falta_acceso': 'desafio_acceso_dificil',
            'datos_dispersos': 'desafio_datos_dispersos',
            'falta_reporte': 'desafio_falta_reporte',
            'dificil_generar_reporte': 'desafio_dificil_generar_reporte'
        }
        
        infraestructura_desafio_map = {
            'dependencia_manual': 'infraestructura_dependencia_manual',
            'falta_estandarizacion': 'infraestructura_falta_estandarizacion',
            'vulnerabilidades': 'infraestructura_vulnerabilidades',
            'poca_escalabilidad': 'infraestructura_poca_escalabilidad'
        }
        
        decision_map = {
            'optimizacion_recursos': 'decision_optimizacion_recursos',
            'reduccion_costos': 'decision_reduccion_costos',
            'mejora_planificacion': 'decision_mejora_planificacion',
            'identificacion_ineficiencias': 'decision_identificacion_ineficiencias'
        }

        # Usar la función auxiliar para procesar los datos
        proceso_mas_largo = get_form_data_as_booleans(request.form.getlist('proceso_mas_largo'), proceso_mas_largo_map)
        desafio_info = get_form_data_as_booleans(request.form.getlist('desafio_info'), desafio_info_map)
        infraestructura_desafio = get_form_data_as_booleans(request.form.getlist('infraestructura_desafio'), infraestructura_desafio_map)
        decision = get_form_data_as_booleans(request.form.getlist('decision'), decision_map)
        
        # Combinar todos los datos en un solo diccionario
        all_data = {
            'nombre_contacto': nombre_contacto,
            'cargo': cargo,
            'departamento': departamento,
            'fecha_entrevista': fecha_entrevista,
            **proceso_mas_largo,
            **desafio_info,
            **infraestructura_desafio,
            **decision,
            'comentarios': comentarios,
            'fecha_registro': fecha_registro
        }
        
        # Se obtiene el nombre de las columnas y los valores del diccionario de datos para el query
        columns = ', '.join(all_data.keys())
        placeholders = ', '.join(['?' for _ in all_data.keys()])
        params = tuple(all_data.values())

        query = f"INSERT INTO datos_entrevista ({columns}) VALUES ({placeholders})"
        
        # Registro para depuración
        logging.info(f"Parámetros a insertar: {params}")

        cursor.execute(query, params)
        
        logging.info(f"Filas afectadas por el comando INSERT: {cursor.rowcount}")

        if cursor.rowcount > 0:
            logging.info("Intentando hacer commit a la base de datos...")
            conn.commit()
            logging.info("¡Commit exitoso! Datos insertados con éxito.")
            flash('¡Información guardada con éxito!', 'success')
        else:
            conn.rollback()
            logging.error("La inserción falló silenciosamente. Ninguna fila fue afectada.")
            flash('Error: La información no pudo ser guardada en la base de datos. Por favor, verifica el esquema de la tabla y los datos.', 'error')

        return redirect(url_for('home'))

    except pyodbc.Error as ex:
        sqlstate = ex.args[0]
        logging.error(f"Error de base de datos: {sqlstate}")
        flash("Ocurrió un error al guardar la información. Por favor, inténtelo de nuevo.", 'error')
        if conn:
            conn.rollback()
        return redirect(url_for('home'))
    except Exception as e:
        logging.error(f"Error inesperado al guardar la información: {str(e)}")
        flash("Ocurrió un error inesperado. Por favor, inténtelo de nuevo.", 'error')
        if conn:
            conn.rollback()
        return redirect(url_for('home'))
    finally:
        if conn:
            conn.close()
            logging.info("Conexión a la base de datos cerrada.")

@app.route('/entrevistas')
def show_interviews():
    conn = None
    interviews = []
    try:
        logging.info("Intentando conectar a la base de datos de Azure SQL para obtener los datos...")
        conn = get_db_connection()
        if conn is None:
            flash("Error de conexión a la base de datos. Por favor, verifique la configuración.", 'error')
            return render_template('entrevistas.html', interviews=[])
            
        cursor = conn.cursor()
        logging.info("Conexión exitosa. Obteniendo datos.")
        
        # Asegurarse de que el orden de las columnas sea el mismo que el del diccionario
        sql_query = """SELECT 
            nombre_contacto, cargo, departamento, fecha_entrevista, comentarios, fecha_registro,
            desafio_datos_dispersos, desafio_acceso_dificil, desafio_falta_reporte,
            desafio_info_no_actualizada, desafio_dificil_generar_reporte,
            proceso_mas_largo_manual, proceso_mas_largo_multiples_fuentes,
            proceso_mas_largo_espera_reportes, proceso_mas_largo_validacion_datos,
            infraestructura_dependencia_manual, infraestructura_falta_estandarizacion,
            infraestructura_vulnerabilidades, infraestructura_poca_escalabilidad,
            decision_optimizacion_recursos, decision_reduccion_costos,
            decision_mejora_planificacion, decision_identificacion_ineficiencias
            FROM datos_entrevista ORDER BY fecha_registro DESC"""

        cursor.execute(sql_query)
        
        columns = [column[0] for column in cursor.description]
        
        for row in cursor.fetchall():
            interviews.append(dict(zip(columns, row)))
        
        logging.info(f"Se obtuvieron {len(interviews)} registros.")
        
    except Exception as e:
        logging.error(f"Error inesperado al obtener datos: {str(e)}")
        flash("Ocurrió un error inesperado al cargar los datos.", 'error')
    finally:
        if conn:
            conn.close()
            logging.info("Conexión a la base de datos cerrada.")

    return render_template('entrevistas.html', interviews=interviews)
