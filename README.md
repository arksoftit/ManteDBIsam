# ManteDBIsam

Herramienta de mantenimiento para bases de datos DBISam vía ODBC (32 bits)

## Versión

**v0.1.6 Beta** - Marzo 2026

## Descripción

ManteDBIsam es una aplicación gráfica desarrollada en Python que permite realizar tareas de mantenimiento sobre bases de datos DBISam a través de conectores ODBC de 32 bits. Está especialmente diseñada para trabajar con aplicaciones que utilicen DBIsam como motor de su nase de datos,  ofreciendo una interfaz amigable para operaciones de verificación, reparación y optimización de tablas.

## Objetivo de la aplicación

Proporcionar a los administradores de sistemas y técnicos de soporte una herramienta confiable para:

- Verificar la integridad estructural de tablas DBISam
- Reparar tablas que presenten corrupción o errores
- Optimizar tablas para mejorar el rendimiento
- Mantener un historial de operaciones mediante logs detallados

## Características principales

- **Conexión vía ODBC**: Compatible con drivers DBISam de 32 bits
- **Múltiples operaciones**: Verificar, reparar y optimizar tablas
- **Selección múltiple**: Permite operar sobre varias tablas simultáneamente
- **Barra de progreso**: Visualización del avance de operaciones
- **Logs automáticos**: Generación de archivos de registro en carpeta `logs`
- **Gestión de respaldos**: Movimiento automático de archivos .dbk, .ibk y .bbk a `backupsdata`
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
source venv_32/Scripts/activate

# Instalar dependencias
pip install pyodbc pyinstaller

# Ejecutar aplicación
python ManteDBIsam.py

## Guía de uso

### Conexión a base de datos
1. Ingresar nombre del DSN configurado
2. Usuario y contraseña 
3. Hacer clic en "Conectar"
4. Verificar la ruta de conexión mostrada

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

## Dependencia: Driver ODBC DBISAM 4

### Versión requerida

**DBISAM ODBC Driver 4.29.1** (32 bits)

### Descripción

La aplicación requiere el driver ODBC de DBISAM versión 4 en su variante de **32 bits**, desarrollado por Elevate Software. Este driver está contenido en un único archivo DLL sin dependencias externas e incluye un asistente de configuración para crear y modificar orígenes de datos (DSN).

### Características del driver

- **Arquitectura**: 32 bits (obligatorio para compatibilidad con ManteDBIsam)
- **Archivo principal**: DBODBC.DLL
- **Versión mostrada en imágenes**: 4.29.00.01 (23/09/2009)
- **Configuración**: Debe realizarse desde el administrador ODBC de 32 bits (`C:\Windows\SysWOW64\odbcad32.exe`)
- **Sistemas operativos soportados**: Windows XP, Vista, 7, 8, 10 y 11

### Descarga

El driver puede obtenerse desde el sitio oficial de Elevate Software:

🔗 **Página de descarga oficial**: [https://www.elevatesoft.com/products?category=dbisam&type=other](https://www.elevatesoft.com/products?category=dbisam&type=other)

Elevate Software ofrece una **versión de prueba gratuita** que permite evaluar el producto antes de adquirir la licencia comercial.

### Licencia

El driver ODBC de DBISAM es un producto comercial de Elevate Software con un costo de **$529 USD** por licencia. Incluye distribución libre de regalías y soporte para entornos de desarrollo.

### Nota importante sobre arquitectura

En sistemas Windows de 64 bits, el driver de 32 bits debe configurarse **exclusivamente** utilizando el administrador ODBC de 32 bits:

# ArkToolsDBisam

Herramienta de mantenimiento para bases de datos DBISam vía ODBC (32 bits)

## Versión

v0.1.9Beta - Mayo 2026

## Descripción

ArkToolsDBisam es una aplicación gráfica desarrollada en Python que permite realizar tareas de mantenimiento sobre bases de datos DBISam a través de conectores ODBC de 32 bits.

## Novedades en v0.1.9Beta

- Nuevo nombre: ArkToolsDBisam (antes ManteDBIsam)
- Barra de progreso dual: general + detallada por tabla
- Mensajes de éxito con resumen de operación
- Etiquetas de detalle y porcentaje en la misma línea
- 4 columnas para distribuir tablas disponibles
- Logo corporativo integrado
- Guardado automático de conexiones previas

## Requisitos

- Windows 10/11 (64 bits)
- DBISAM ODBC Driver 4.29.1 (32 bits)
- Python 3.x 32 bits

## Instalación

1. Clonar repositorio:
   git clone https://github.com/arksoftit/ManteDBIsam.git
   cd ManteDBIsam

2. Crear entorno virtual con Python 32 bits:
   "C:\Python\Python314_32\python" -m venv venv_32

3. Activar entorno (Git Bash):
   source venv_32/Scripts/activate

4. Instalar dependencias:
   pip install pyodbc pillow pyinstaller

5. Ejecutar:
   python ArkToolsDBisam.py

## Compilación a .exe

python -m PyInstaller --onefile --windowed --name ArkToolsDBisam --icon="assets/Imagen/Logo_Juepae_00_200.ico" --add-data "assets;assets" ArkToolsDBisam.py

## Uso

1. Conectar: Seleccionar DSN, usuario y contraseña
2. Seleccionar tablas (checkboxes en 4 columnas)
3. Elegir operación: Verificar, Reparar u Optimizar
4. Ver resultados en pestaña "Resultados de operaciones"
5. Ajuste de saldos en pestaña "Ajuste de Saldos"

## Driver ODBC DBISAM 4

- Versión requerida: 4.29.1 (32 bits)
- Archivo: DBODBC.DLL
- Configuración: odbcad32.exe desde C:\Windows\SysWOW64\
- Descarga: https://www.elevatesoft.com/products?category=dbisam&type=other
- Licencia: Comercial $529 USD

## Licencia

Desarrollado por JUEPAE. Todos los derechos reservados.



