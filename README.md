# ManteDBIsam

Herramienta de mantenimiento para bases de datos DBISam vía ODBC (32 bits)

## Versión

**v0.1.6 Beta** - Marzo 2026

## Descripción

ManteDBIsam es una aplicación gráfica desarrollada en Python que permite realizar tareas de mantenimiento sobre bases de datos DBISam a través de conectores ODBC de 32 bits. Está especialmente diseñada para trabajar con los sistemas administrativos de a2Softway, ofreciendo una interfaz amigable para operaciones de verificación, reparación y optimización de tablas.

## Objetivo de la aplicación

Proporcionar a los administradores de sistemas y técnicos de soporte una herramienta confiable para:

- Verificar la integridad estructural de tablas DBISam
- Reparar tablas que presenten corrupción o errores
- Optimizar tablas para mejorar el rendimiento
- Validar licencias y archivos de configuración de sistemas a2
- Mantener un historial de operaciones mediante logs detallados

## Características principales

- **Conexión vía ODBC**: Compatible con drivers DBISam de 32 bits
- **Múltiples operaciones**: Verificar, reparar y optimizar tablas
- **Selección múltiple**: Permite operar sobre varias tablas simultáneamente
- **Barra de progreso**: Visualización del avance de operaciones
- **Logs automáticos**: Generación de archivos de registro en carpeta `logs`
- **Gestión de respaldos**: Movimiento automático de archivos .dbk, .ibk y .bbk a `backupsdata`
- **Validación de licencia**: Verificación de archivos a2admin.A2 y empresas.dat
- **Interfaz por pestañas**: Separación entre listado de tablas y resultados
- **Información detallada**: Estado de conexión y detalles técnicos

## Estructura de directorios


## Requisitos del sistema

- **Sistema operativo**: Windows 10/11 (64 bits, con soporte para 32 bits)
- **Driver ODBC**: DBISAM 4 ODBC (32 bits) instalado y configurado
- **Arquitectura**: Python 3.x de 32 bits (obligatorio para compatibilidad con driver)
- **Dependencias Python**: pyodbc, tkinter (incluido), winreg

## Instalación y configuración

### 1. Configurar DSN ODBC (obligatorio)

```bash
# Abrir administrador ODBC de 32 bits
C:\Windows\SysWOW64\odbcad32.exe


# Clonar repositorio
git clone https://github.com/arksoftit/ManteDBIsam.git
cd ManteDBIsam

# Crear entorno virtual con Python 32 bits
C:\Users\usuario\AppData\Local\Programs\Python\Python313-32\python -m venv venv_32

# Activar entorno
venv_32\Scripts\activate

# Instalar dependencias
pip install pyodbc pyinstaller

# Ejecutar aplicación
python ManteDBIsam.py

## Guía de uso

### Conexión a base de datos
1. Ingresar nombre del DSN configurado
2. Usuario y contraseña (usualmente "master" para DBISam)
3. Hacer clic en "Conectar"
4. Verificar la ruta de conexión mostrada

### Verificación de licencia (sistemas a2)
1. Hacer clic en "Examinar..." para seleccionar la carpeta raíz de instalación
2. La aplicación validará automáticamente a2admin.A2 y empresas.dat
3. Se mostrará el estado de licencia y nombre de empresa

### Operaciones de mantenimiento
1. Seleccionar tablas usando los checkboxes
2. Opcional: activar "Generar archivo de log" y "Mover backups"
3. Elegir operación:
   - **Verificar**: Comprueba integridad estructural
   - **Reparar**: Corrige errores encontrados
   - **Optimizar**: Reorganiza datos y elimina espacio libre

### Visualización de resultados
- Los resultados detallados aparecen en la pestaña "Resultados de operaciones"
- La barra de progreso muestra el avance de operaciones múltiples
- El botón "Ver estado de conexión" muestra información técnica detallada
