# APP-FAYMEX
Encuesta para identificar flujo de la información

Backend de la Aplicación de Entrevistas (app.py)
Este es el backend de una aplicación web construida con Flask en Python, diseñada para recopilar datos de entrevistas y almacenarlos en una base de datos de Azure SQL.

Funcionalidad Principal
El script app.py gestiona las siguientes tareas:

Conexión a la Base de Datos: Establece una conexión segura a la base de datos de Azure SQL utilizando pyodbc, obteniendo las credenciales de las variables de entorno para proteger la información sensible.

Manejo de Rutas:

La ruta principal (/) sirve una página HTML para el formulario de entrevista.

La ruta de envío (/submit) procesa la información del formulario.

Validación y Almacenamiento:

Al recibir los datos del formulario, realiza una validación para evitar entradas duplicadas basadas en el nombre de contacto.

Convierte los datos de los checkboxes en valores binarios (1 o 0) para su almacenamiento.

Inserta la información en la tabla datos_entrevista de la base de datos.

Manejo de Errores y Feedback:

Incluye manejo de errores robusto para problemas de conexión y de inserción de datos.

Utiliza Flask.flash para mostrar mensajes de éxito o error al usuario, mejorando la experiencia de uso.

Dependencias
Flask: Para el marco de la aplicación web.

pyodbc: Para la conexión con la base de datos.

Variables de Entorno
Para que la aplicación funcione correctamente, es necesario configurar las siguientes variables de entorno:

AZURE_SQL_SERVER

AZURE_SQL_DATABASE

AZURE_SQL_USERNAME

AZURE_SQL_PASSWORD

FLASK_SECRET_KEY
