Sistema de Riego Automatizado - Proyecto
Descripción
Este proyecto consiste en un sistema de riego autónomo que utiliza sensores para monitorear la humedad del suelo, el nivel de agua, el pH y la conductividad eléctrica (CE), activando actuadores (bombas, electroválvulas) según los datos sensoriales y un modelo de Machine Learning (Random Forest). La sincronización de datos se realiza con Google Cloud Platform.

Características
* Monitoreo de sensores: humedad, pH, CE, nivel de agua.
* Control automático de actuadores: bomba hidráulica, electroválvulas de riego y fertilización.
* Sincronización de datos y almacenamiento en Google Cloud.
* Interfaz gráfica (GUI) en Node-RED.
* Modo de control automático y manual.

Requisitos
Python
pip install -r requirements.txt

Dependencias
* Adafruit-PureIO
* Adafruit_ADS1x15
* Google Cloud Storage
* Numpy
* Scikit-learn
* Matplotlib
* Pandas
* Requests
Para ver la lista completa, consulta el archivo requirements.txt.

Pruebas
python -m unittest discover tests/