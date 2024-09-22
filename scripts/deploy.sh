#!/bin/bash

# Actualizar el repositorio
git pull origin main

# Instalar dependencias
pip install -r requirements.txt

# Configurar y activar el entorno virtual
python3 -m venv venv
source venv/bin/activate

# Ejecutar migraciones 
# python manage.py migrate

# Reiniciar servicios
sudo systemctl restart riego.service

echo "Despliegue completado exitosamente."
