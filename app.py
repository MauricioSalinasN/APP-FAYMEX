# app.py - Backend de la aplicación web
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
# ADVERTENCIA: Las credenciales sensibles NO deben estar en el código fuente.
# Se eliminaron los valores por defecto para username, password y la clave secreta
# para forzar el uso de variables de entorno y mejorar la seguridad.

server = os.environ.get('AZURE_SQL_SERVER', 'server-bd-faymex.database.windows.net')
database = os.environ.get('AZURE_SQL_DATABASE', 'BD_Faymex')
username = os.environ.get('AZURE_SQL_USERNAME')
password = os.environ.get('AZURE_SQL_PASSWORD')
# La clave secreta de Flask también debe ser una variable de entorno
secret_key = os.environ.get('FLASK_SECRET_KEY')
app.secret_key = secret_key

# Valida que las variables de entorno más importantes existan
if not username or not password or not secret_key:
    # Si alguna variable falta, la aplicación no funcionará, lo que es un buen indicio de seguridad
    raise ValueError("Error: Las variables de entorno AZURE_SQL_USERNAME, AZURE_SQL_PASSWORD y FLASK_SECRET_KEY deben estar configuradas.")

driver = '{ODBC Driver 17 for SQL Server}' # Asegúrate de que este driver esté instalado en el sistema

# Crea la cadena de conexión de forma más explícita
# Este formato es a menudo más robusto para entornos de nube
connection_string = 'DRIVER={0};SERVER=tcp:{1},1433;DATABASE={2};UID={3};PWD={4}'.format(driver, server, database, username, password)


def get_db_connection():
    """Función para establecer la conexión a la base de datos."""
    conn = None
    try:
        logging.info(f"Intentando conectar a: {server}/{database} con usuario: {username}")
        conn = pyodbc.connect(connection_string, autocommit=True)
        logging.info("Conexión a la base de datos exitosa.")
        return conn
    except pyodbc.Error as ex:
        sqlstate = ex.args[0]
        logging.error(f"Error de base de datos: {sqlstate}. Asegúrate de que las credenciales y la IP del servidor sean correctas.")
        if sqlstate == '28000':
            logging.error("Error 28000: Las credenciales (usuario/contraseña) son incorrectas.")
        elif sqlstate == '08001':
            logging.error("Error 08001: No se puede conectar al servidor. Asegúrate de que tu IP esté permitida en el firewall de Azure SQL.")
        elif 'Login failed' in str(ex):
             logging.error("El inicio de sesión ha fallado. Revisa tus credenciales.")
        return None
    except Exception as e:
        logging.error(f"Error inesperado al conectar a la base de datos: {str(e)}")
        return None

# --- RUTAS DE LA APLICACIÓN ---

@app.route('/')
def home():
    """
    Ruta de inicio que sirve la página de entrevista HTML y muestra los datos existentes.
    """
    conn = None
    interviews = []
    try:
        logging.info("Intentando conectar a la base de datos de Azure SQL para obtener los datos...")
        conn = get_db_connection()
        if conn is None:
            flash("Error de conexión a la base de datos. Por favor, verifique la configuración.", 'error')
            return render_template('datos_entrevista.html', interviews=[])
            
        cursor = conn.cursor()
        logging.info("Conexión exitosa. Obteniendo datos.")
        
        # Consulta para seleccionar todas las entrevistas ordenadas por fecha de registro
        sql_query = "SELECT * FROM datos_entrevista ORDER BY fecha_registro DESC"
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

    # Asegúrate de que este sea el nombre correcto de tu archivo HTML para la página principal
    return render_template('datos_entrevista.html', interviews=interviews)

@app.route('/submit', methods=['POST'])
def submit():
    """
    Recibe los datos del formulario, los valida y los inserta en la base de datos de Azure SQL.
    """
    conn = None
    try:
        logging.info("--- INICIANDO PROCESO DE GUARDADO ---")
        
        # DEBUG: Imprimir todos los datos recibidos del formulario
        logging.info("Datos del formulario recibidos: %s", request.form)

        logging.info("Intentando conectar a la base de datos de Azure SQL para guardar datos...")
        conn = get_db_connection()
        if conn is None:
            flash("Error de conexión a la base de datos.", 'error')
            return redirect(url_for('home'))

        cursor = conn.cursor()
        logging.info("Conexión exitosa.")

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
        # Verificar si el contacto ya existe en la base de datos, ignorando mayúsculas y minúsculas
        query_check_duplicate = "SELECT COUNT(*) FROM datos_entrevista WHERE LOWER(nombre_contacto) = ?"
        cursor.execute(query_check_duplicate, (nombre_contacto.lower(),))
        
        if cursor.fetchone()[0] > 0:
            flash(f'Error: El contacto "{nombre_contacto}" ya existe en la base de datos.', 'error')
            logging.warning(f"Contacto duplicado: '{nombre_contacto}' no se guardó.")
            return redirect(url_for('home'))
        
        # --- CONTINUAR CON LA INSERCIÓN SI NO ES DUPLICADO ---
        # Obtener los valores de los checkboxes de forma correcta
        proceso_mas_largo_list = request.form.getlist('proceso_mas_largo')
        desafio_info_list = request.form.getlist('desafio_info')
        infraestructura_desafio_list = request.form.getlist('infraestructura_desafio')
        decision_list = request.form.getlist('decision')

        # CONVERSIÓN DE BOOLEANOS A ENTEROS (1 o 0) PARA EVITAR ERRORES DE TIPO DE DATOS
        proceso_mas_largo_manual = 1 if 'proceso_manual' in proceso_mas_largo_list else 0
        proceso_mas_largo_multiples_fuentes = 1 if 'multiples_fuentes' in proceso_mas_largo_list else 0
        proceso_mas_largo_espera_reportes = 1 if 'espera_reportes' in proceso_mas_largo_list else 0
        proceso_mas_largo_validacion_datos = 1 if 'validacion_datos' in proceso_mas_largo_list else 0
        
        # **CORREGIDO**: Los nombres de las variables coinciden con los de tu script SQL
        desafio_info_no_actualizada = 1 if 'desactualizada' in desafio_info_list else 0
        desafio_acceso_dificil = 1 if 'falta_acceso' in desafio_info_list else 0
        desafio_datos_dispersos = 1 if 'datos_dispersos' in desafio_info_list else 0
        desafio_falta_reporte = 1 if 'falta_reporte' in desafio_info_list else 0
        desafio_dificil_generar_reporte = 1 if 'dificil_generar_reporte' in desafio_info_list else 0

        infraestructura_dependencia_manual = 1 if 'dependencia_manual' in infraestructura_desafio_list else 0
        infraestructura_falta_estandarizacion = 1 if 'falta_estandarizacion' in infraestructura_desafio_list else 0
        infraestructura_vulnerabilidades = 1 if 'vulnerabilidades' in infraestructura_desafio_list else 0
        infraestructura_poca_escalabilidad = 1 if 'poca_escalabilidad' in infraestructura_desafio_list else 0

        decision_optimizacion_recursos = 1 if 'optimizacion_recursos' in decision_list else 0
        decision_reduccion_costos = 1 if 'reduccion_costos' in decision_list else 0
        decision_mejora_planificacion = 1 if 'mejora_planificacion' in decision_list else 0
        decision_identificacion_ineficiencias = 1 if 'identificacion_ineficiencias' in decision_list else 0

        # Sentencia SQL para la inserción de datos
        query = """
            INSERT INTO datos_entrevista (
                nombre_contacto, cargo, departamento, fecha_entrevista,
                desafio_datos_dispersos, desafio_acceso_dificil, desafio_falta_reporte,
                desafio_info_no_actualizada, desafio_dificil_generar_reporte,
                proceso_mas_largo_manual, proceso_mas_largo_multiples_fuentes,
                proceso_mas_largo_espera_reportes, proceso_mas_largo_validacion_datos,
                infraestructura_dependencia_manual, infraestructura_falta_estandarizacion,
                infraestructura_vulnerabilidades, infraestructura_poca_escalabilidad,
                decision_optimizacion_recursos, decision_reduccion_costos,
                decision_mejora_planificacion, decision_identificacion_ineficiencias,
                comentarios, fecha_registro
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        # Lista de los valores para la consulta SQL
        # NOTA: Los nombres de las variables ahora coinciden con los nombres de las columnas en el INSERT
        params = (
            nombre_contacto, cargo, departamento, fecha_entrevista_str,
            desafio_datos_dispersos, desafio_acceso_dificil, desafio_falta_reporte,
            desafio_info_no_actualizada, desafio_dificil_generar_reporte,
            proceso_mas_largo_manual, proceso_mas_largo_multiples_fuentes,
            proceso_mas_largo_espera_reportes, proceso_mas_largo_validacion_datos,
            infraestructura_dependencia_manual, infraestructura_falta_estandarizacion,
            infraestructura_vulnerabilidades, infraestructura_poca_escalabilidad,
            decision_optimizacion_recursos, decision_reduccion_costos,
            decision_mejora_planificacion, decision_identificacion_ineficiencias,
            comentarios, fecha_registro
        )

        # DEBUG: Imprimir la consulta y los parámetros para verificar
        logging.info("Consulta SQL: %s", query)
        logging.info("Parámetros a insertar: %s", params)

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


