from PIL import Image, ImageTk
import sys
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import pyodbc
import threading
import time
import os
import shutil
import winreg
import json 
from datetime import datetime

# ============= CLASE PROGRESS MANAGER =============
class ProgressManager:
    """Manejador de progreso para operaciones"""
    def __init__(self, app, total_tablas):
        self.app = app
        self.total_tablas = total_tablas
        self.tabla_actual = 0
        self.progreso_tabla_actual = 0
        
    def iniciar_tabla(self, nombre_tabla, pasos_esperados=100):
        """Inicia el procesamiento de una nueva tabla"""
        self.tabla_actual += 1
        self.progreso_tabla_actual = 0
        self.app.detalle_label.config(text=f"Procesando: {nombre_tabla}", foreground="blue")
        
        # Actualizar barra principal
        porcentaje_general = int((self.tabla_actual / self.total_tablas) * 100)
        self.app.progreso['value'] = porcentaje_general
        self.app.porcentaje_label.config(text=f"{porcentaje_general}%")
        
    def actualizar_tabla(self, progreso, mensaje=None):
        """Actualiza el progreso dentro de la tabla actual (0-100)"""
        self.progreso_tabla_actual = progreso
        self.app.progreso_detalle['value'] = progreso
        self.app.porcentaje_detalle_label.config(text=f"{progreso}%")
        
        if mensaje:
            self.app.detalle_label.config(text=mensaje, foreground="blue")
        
        self.app.root.update_idletasks()
        
    def completar_tabla(self):
        """Marca la tabla actual como completada"""
        self.actualizar_tabla(100)
        self.app.detalle_label.config(text=f"Tabla completada", foreground="green")
        self.app.root.update_idletasks()
        time.sleep(0.1)  # Pequeña pausa para mostrar el 100%
        
    def resetear_tabla(self):
        """Resetea la barra de detalle para la siguiente tabla"""
        self.actualizar_tabla(0)

# ============= CLASE PRINCIPAL =============

class ArkToolsDBisam:
    def __init__(self, root):
        self.root = root
        # self.root.title("Mantenimiento de Tablas BDIsam")
        self.root.title("ArkToolsDBisam")
        self.root.geometry("800x700")
        
        self.conexion = None
        self.tablas_vars = {}
        self.operacion_en_curso = False
        self.detalles_conexion = {}
        self.ruta_data_actual = None
        self.dsn_actual = None
        
        # Determinar carpetas
        self.ruta_base = os.path.dirname(os.path.abspath(__file__))
        self.ruta_logs = os.path.join(self.ruta_base, "logs")
        self.ruta_backups = os.path.join(self.ruta_base, "backupsdata")
        self.ruta_conexiones = self.resource_path("conexiones.json", for_writing=True)
                
        # Crear carpetas si no existen
        for ruta in [self.ruta_logs, self.ruta_backups]:
            if not os.path.exists(ruta):
                os.makedirs(ruta)
        
        self.crear_interfaz()
        self.cargar_conexiones_previas()
    
    def cargar_conexiones_previas(self):
        try:
            if os.path.exists(self.ruta_conexiones):
                with open(self.ruta_conexiones, 'r', encoding='utf-8') as f:
                    conexiones = json.load(f)
                    
                if conexiones:
                    # Obtener lista única de DSNs
                    dsns = list(set([conn['dsn'] for conn in conexiones]))
                    self.dsn_combo['values'] = dsns
                    
                    # Cargar la última conexión
                    ultima = conexiones[-1]
                    self.dsn_var.set(ultima.get('dsn', ''))
                    self.usuario_var.set(ultima.get('usuario', ''))
                    self.password_var.set(ultima.get('password', ''))
                    
                    self.resultado_text.insert(tk.END, "📂 Conexiones previas cargadas\n")
        except Exception as e:
            print(f"Error cargando conexiones: {e}")
    
    def obtener_ruta_desde_registro(self, dsn_name):
        """
        Lee la ruta del DSN directamente del registro de Windows
        Para DBISAM ODBC Driver 32 bits en Windows 64 bits
        """
        try:
            # Rutas del registro para DSN de sistema 32 bits en Windows 64
            rutas_registro = [
                f"SOFTWARE\\WOW6432Node\\ODBC\\ODBC.INI\\{dsn_name}",  # System DSN 32 bits
                f"SOFTWARE\\ODBC\\ODBC.INI\\{dsn_name}",                 # System DSN 64 bits
                f"SOFTWARE\\WOW6432Node\\ODBC\\ODBC.INI\\{dsn_name}",   # User DSN 32 bits
                f"SOFTWARE\\ODBC\\ODBC.INI\\{dsn_name}",                 # User DSN 64 bits
            ]
            
            for ruta in rutas_registro:
                try:
                    # Abrir la clave del registro
                    with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, ruta) as key:
                        # Intentar leer CatalogName (para DBISAM local)
                        try:
                            valor, _ = winreg.QueryValueEx(key, "CatalogName")
                            if valor and os.path.exists(valor):
                                return valor
                        except FileNotFoundError:
                            pass
                        
                        # Intentar leer Database (para otros formatos)
                        try:
                            valor, _ = winreg.QueryValueEx(key, "Database")
                            if valor and os.path.exists(valor):
                                return valor
                        except FileNotFoundError:
                            pass
                        
                        # Intentar leer DatabaseFile
                        try:
                            valor, _ = winreg.QueryValueEx(key, "DatabaseFile")
                            if valor and os.path.exists(os.path.dirname(valor)):
                                return os.path.dirname(valor)
                        except FileNotFoundError:
                            pass
                
                except FileNotFoundError:
                    continue
                except PermissionError:
                    continue
            
            # Si no encuentra en HKLM, buscar en HKCU
            for ruta in rutas_registro:
                try:
                    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, ruta) as key:
                        try:
                            valor, _ = winreg.QueryValueEx(key, "CatalogName")
                            if valor and os.path.exists(valor):
                                return valor
                        except FileNotFoundError:
                            pass
                except FileNotFoundError:
                    continue
                except PermissionError:
                    continue
            
            return None
            
        except Exception as e:
            print(f"Error leyendo registro: {e}")
            return None
    
    def guardar_conexion(self, dsn, usuario, password):
        """Guarda la conexión actual en el archivo JSON"""
        try:
            conexiones = []
            
            # Leer conexiones existentes si el archivo ya existe
            if os.path.exists(self.ruta_conexiones):
                with open(self.ruta_conexiones, 'r', encoding='utf-8') as f:
                    conexiones = json.load(f)
            
            # Crear nuevo registro de conexión
            nueva_conexion = {
                'dsn': dsn,
                'usuario': usuario,
                'password': password,
                'fecha': datetime.now().strftime('%d/%m/%Y %H:%M:%S')
            }
            
            # Agregar nueva conexión
            conexiones.append(nueva_conexion)
            
            # Mantener solo las últimas 10 conexiones (opcional)
            if len(conexiones) > 10:
                conexiones = conexiones[-10:]
            
            # Guardar en archivo
            with open(self.ruta_conexiones, 'w', encoding='utf-8') as f:
                json.dump(conexiones, f, indent=2, ensure_ascii=False)
                
            self.resultado_text.insert(tk.END, f"💾 Conexión guardada: {dsn}\n")
            
        except Exception as e:
            print(f"Error guardando conexión: {e}")
    
    def resource_path(self, relative_path, for_writing=False):
        """
        Obtiene la ruta absoluta de un recurso.
        for_writing=True: retorna ruta en el directorio del ejecutable (para archivos que se modifican)
        for_writing=False: retorna ruta en _MEIPASS (para recursos de solo lectura)
        """
        if for_writing:
            # Para archivos que se escriben (JSON, logs), usar directorio del ejecutable
            if getattr(sys, 'frozen', False):
                # Estamos en un ejecutable
                base_path = os.path.dirname(sys.executable)
            else:
                # Estamos en desarrollo
                base_path = os.path.dirname(os.path.abspath(__file__))
        else:
            # Para recursos de solo lectura (imágenes)
            try:
                base_path = sys._MEIPASS
            except AttributeError:
                base_path = os.path.dirname(os.path.abspath(__file__))
        
        return os.path.join(base_path, relative_path)
    
    def crear_interfaz(self):
        # Marco superior
        marco_superior = ttk.Frame(self.root)
        marco_superior.pack(fill="x", padx=10, pady=5)

        # Columna izquierda: Conexión
        marco_conexion = ttk.LabelFrame(marco_superior, text="Conexión a Base de Datos", padding=10)
        marco_conexion.pack(side="left", fill="x", expand=True)

        ttk.Label(marco_conexion, text="DSN:").grid(row=0, column=0, sticky="w")
        self.dsn_var = tk.StringVar()
        self.dsn_combo = ttk.Combobox(marco_conexion, textvariable=self.dsn_var, width=27)
        self.dsn_combo.grid(row=0, column=1, padx=5)
        self.dsn_combo.bind('<<ComboboxSelected>>', self.cargar_conexion_seleccionada)

        ttk.Label(marco_conexion, text="Usuario:").grid(row=1, column=0, sticky="w")
        self.usuario_var = tk.StringVar()
        ttk.Entry(marco_conexion, textvariable=self.usuario_var).grid(row=1, column=1, padx=5)

        ttk.Label(marco_conexion, text="Contraseña:").grid(row=2, column=0, sticky="w")
        self.password_var = tk.StringVar()
        ttk.Entry(marco_conexion, textvariable=self.password_var, show="*").grid(row=2, column=1, padx=5)

        self.conectar_btn = ttk.Button(marco_conexion, text="Conectar", command=self.conectar)
        self.conectar_btn.grid(row=3, column=0, columnspan=2, pady=10)

        # Columna derecha: Grupo (Acerca de + Logo)
        marco_derecho = ttk.Frame(marco_superior)
        marco_derecho.pack(side="right", padx=(10, 0))

        # 1. Botón Acerca de...
        marco_acerca = ttk.Frame(marco_derecho)
        marco_acerca.pack(fill="x", pady=(0, 5))
        self.acerca_btn = ttk.Button(marco_acerca, text="Acerca de...", command=self.mostrar_acerca)
        self.acerca_btn.pack(pady=5, padx=10)

        # 2. Logo (debajo del botón, redimensionado a 80x80)
        marco_logo = ttk.Frame(marco_derecho)
        marco_logo.pack(fill="x", pady=(0, 5))
        try:
            ruta_logo = self.resource_path(os.path.join("assets", "Imagen", "Logo_Juepae_00_200.png"), for_writing=False)
            print(f"Cargando logo desde: {ruta_logo}")
            if os.path.exists(ruta_logo):
                imagen_pil = Image.open(ruta_logo)
                imagen_pil.thumbnail((80, 80), Image.Resampling.LANCZOS)
                self.logo_image = ImageTk.PhotoImage(imagen_pil)
                lbl_logo = ttk.Label(marco_logo, image=self.logo_image)
                lbl_logo.pack(pady=5)
                lbl_logo.bind("<Button-1>", lambda e: messagebox.showinfo(
                    "Logo", "JUEPAE - Desarrollo de Software\nArkToolsDBisam v0.1.9Beta"
                ))
            else:
                lbl_logo = ttk.Label(marco_logo, text="[Logo] JUEPAE", font=("Arial", 8, "bold"))
                lbl_logo.pack()
        except Exception as e:
            print(f"Error cargando logo: {e}")
            lbl_logo = ttk.Label(marco_logo, text="[Logo] JUEPAE", font=("Arial", 8, "bold"))
            lbl_logo.pack()

        # Marco para la ruta y botón de estado
        marco_ruta_estado = ttk.LabelFrame(self.root, text="Ruta de conexión ODBC y Estado", padding=10)
        marco_ruta_estado.pack(fill="x", padx=10, pady=5)

        frame_ruta = ttk.Frame(marco_ruta_estado)
        frame_ruta.pack(fill="x")

        ttk.Label(frame_ruta, text="Ruta de conexión:").pack(side="left", padx=5)
        self.ruta_label = ttk.Label(frame_ruta, text="[No conectado]", foreground="gray")
        self.ruta_label.pack(side="left", padx=5)

        self.estado_btn = ttk.Button(frame_ruta, text="Ver estado de conexión",
                                   command=self.mostrar_estado_conexion, state="disabled")
        self.estado_btn.pack(side="right", padx=5)

         # Barra de progreso
        marco_progreso = ttk.LabelFrame(self.root, text="Progreso", padding=5)
        marco_progreso.pack(fill="x", padx=10, pady=5)

        # Barra principal (avance general)
        self.progreso = ttk.Progressbar(marco_progreso, orient="horizontal", length=100, mode="determinate")
        self.progreso.pack(fill="x", padx=5, pady=(5, 0))
        
        # Frame para porcentaje principal
        frame_porcentaje = ttk.Frame(marco_progreso)
        frame_porcentaje.pack(fill="x", padx=5)
        self.porcentaje_label = ttk.Label(frame_porcentaje, text="0%", anchor="e")
        self.porcentaje_label.pack(side="right")
        
        # Segunda barra (avance detallado por tabla)
        self.progreso_detalle = ttk.Progressbar(marco_progreso, orient="horizontal", length=100, mode="determinate")
        self.progreso_detalle.pack(fill="x", padx=5, pady=(5, 0))
        
        # Frame combinado: texto de detalle y porcentaje en la misma línea
        frame_detalle_linea = ttk.Frame(marco_progreso)
        frame_detalle_linea.pack(fill="x", padx=5, pady=(5, 5))
        
        self.detalle_label = ttk.Label(frame_detalle_linea, text="Esperando operación...", foreground="gray", anchor="w")
        self.detalle_label.pack(side="left", fill="x", expand=True)
        
        self.porcentaje_detalle_label = ttk.Label(frame_detalle_linea, text="0%", foreground="blue", anchor="e")
        self.porcentaje_detalle_label.pack(side="right")
        
        # Estilo para las pestañas
        style = ttk.Style()
        style.theme_use('xpnative')
        style.configure('TNotebook.Tab',
                       padding=[12, 4],
                       font=('Arial', '10', 'bold'),
                       borderwidth=2,
                       relief='solid',
                       background="#8dcbe7")
        style.map('TNotebook.Tab',
                 background=[('selected', '#e1e1e1')],
                 foreground=[('selected', 'black')])

        # Marco de pestañas
        self.notebook = ttk.Notebook(self.root, style='TNotebook')
        self.notebook.pack(fill="both", expand=True, padx=10, pady=5)

        # Pestaña 1: Tablas disponibles
        self.tab_tablas = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_tablas, text="Tablas disponibles")

        # Pestaña 2: Resultados de operaciones
        self.tab_resultados = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_resultados, text="Resultados de operaciones")

        # Pestaña 3: Ajuste de Saldos
        self.tab_ajuste = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_ajuste, text="Ajuste de Saldos")

        # --- Contenido de pestaña Tablas disponibles ---
        marco_seleccion = ttk.Frame(self.tab_tablas)
        marco_seleccion.pack(fill="x", pady=5)

        ttk.Label(marco_seleccion, text="Seleccionar tablas:").pack(side="left", padx=5)
        self.seleccionar_todo_btn = ttk.Button(marco_seleccion, text="Seleccionar todo",
                                             command=self.seleccionar_todas, state="disabled")
        self.seleccionar_todo_btn.pack(side="left", padx=5)
        self.deseleccionar_todo_btn = ttk.Button(marco_seleccion, text="Deseleccionar todo",
                                               command=self.deseleccionar_todas, state="disabled")
        self.deseleccionar_todo_btn.pack(side="left", padx=5)

        self.generar_log_var = tk.BooleanVar(value=True)
        self.log_check = ttk.Checkbutton(marco_seleccion, text="Generar archivo de log",
                                        variable=self.generar_log_var)
        self.log_check.pack(side="left", padx=20)

        self.mover_backups_var = tk.BooleanVar(value=True)
        self.backup_check = ttk.Checkbutton(marco_seleccion, text="Mover backups a carpeta backupsdata",
                                           variable=self.mover_backups_var)
        self.backup_check.pack(side="left", padx=20)

        marco_botones = ttk.Frame(self.tab_tablas)
        marco_botones.pack(fill="x", pady=5)

        self.verificar_btn = ttk.Button(marco_botones, text="Verificar seleccionadas",
                                       command=self.verificar_seleccionadas, state="disabled")
        self.verificar_btn.pack(side="left", padx=5)
        self.reparar_btn = ttk.Button(marco_botones, text="Reparar seleccionadas",
                                     command=self.reparar_seleccionadas, state="disabled")
        self.reparar_btn.pack(side="left", padx=5)
        self.optimizar_btn = ttk.Button(marco_botones, text="Optimizar seleccionadas",
                                       command=self.optimizar_seleccionadas, state="disabled")
        self.optimizar_btn.pack(side="left", padx=5)

        marco_tablas = ttk.LabelFrame(self.tab_tablas, text="Tablas disponibles", padding=5)
        marco_tablas.pack(fill="both", expand=True, pady=5)

        self.canvas_tablas = tk.Canvas(marco_tablas, borderwidth=0, highlightthickness=0)
        scrollbar_tablas = ttk.Scrollbar(marco_tablas, orient="vertical", command=self.canvas_tablas.yview)
        self.frame_tablas = ttk.Frame(self.canvas_tablas)
        self.frame_tablas.bind("<Configure>", lambda e: self.canvas_tablas.configure(scrollregion=self.canvas_tablas.bbox("all")))
        self.canvas_tablas.create_window((0, 0), window=self.frame_tablas, anchor="nw")
        self.canvas_tablas.configure(yscrollcommand=scrollbar_tablas.set)
        self.canvas_tablas.pack(side="left", fill="both", expand=True)
        scrollbar_tablas.pack(side="right", fill="y")

        # --- Contenido de pestaña Resultados ---
        self.resultado_text = scrolledtext.ScrolledText(self.tab_resultados, height=20, width=80)
        self.resultado_text.pack(fill="both", expand=True, pady=5)
        ttk.Button(self.tab_resultados, text="Limpiar resultados",
                  command=self.limpiar_resultados).pack(pady=5)

        # --- Contenido de pestaña Ajuste de Saldos ---
        marco_ajuste = ttk.Frame(self.tab_ajuste)
        marco_ajuste.pack(fill="both", expand=True, padx=10, pady=10)

        ttk.Label(marco_ajuste, text="Ajuste de saldos menores a 0.01",
                 font=("Arial", 12, "bold")).pack(anchor="w", pady=10)
        ttk.Label(marco_ajuste, text="Esta función pondrá a cero los saldos de documentos con valores "
                 "entre -0.01 y 0.01 (excluyendo cero exacto) en las tablas de "
                 "Cuentas por Cobrar y Cuentas por Pagar.").pack(anchor="w", pady=5)

        opciones_frame = ttk.LabelFrame(marco_ajuste, text="Opciones", padding=10)
        opciones_frame.pack(fill="x", pady=10)

        self.ajustar_cxc_var = tk.BooleanVar(value=True)
        self.ajustar_cxp_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(opciones_frame, text="Cuentas por Cobrar",
                       variable=self.ajustar_cxc_var).pack(anchor="w", pady=2)
        ttk.Checkbutton(opciones_frame, text="Cuentas por Pagar",
                       variable=self.ajustar_cxp_var).pack(anchor="w", pady=2)

        boton_frame = ttk.Frame(marco_ajuste)
        boton_frame.pack(pady=20)
        self.ejecutar_ajuste_btn = ttk.Button(boton_frame, text="Ejecutar Ajuste de Saldos",
                                             command=self.ejecutar_ajuste_saldos)
        self.ejecutar_ajuste_btn.pack()

        # Área de resultados específica para ajustes
        # ttk.Label(marco_ajuste, text="Resultados del ajuste:").pack(anchor="w", pady=(10,0))
        # self.ajuste_resultado = scrolledtext.ScrolledText(marco_ajuste, height=10)
        # self.ajuste_resultado.pack(fill="both", expand=True, pady=5)
    
    def mostrar_acerca(self):
        info_acerca = """ArkToolsDBisam v0.1.9Beta

Desarrollado por Juan E. Páez M.
JUEPAE
Fecha: Marzo 2026

Herramienta de mantenimiento
para bases de datos DBISam
vía ODBC 32 bits"""
        
        messagebox.showinfo("Acerca de ArkToolsDBisam", info_acerca)
    
    def mostrar_estado_conexion(self):
        if not self.conexion:
            messagebox.showwarning("Sin conexión", "No hay una conexión activa")
            return
        
        info = f"""=== ESTADO DE CONEXIÓN ===

DSN: {self.dsn_actual}
Usuario: {self.usuario_var.get()}
Ruta de datos: {self.ruta_data_actual if self.ruta_data_actual else 'No disponible'}

Detalles técnicos:
• Driver: {self.detalles_conexion.get('driver', 'N/A')}
• Base de datos: {self.detalles_conexion.get('db_name', 'N/A')}
• Versión: {self.detalles_conexion.get('version', 'N/A')}
• Conexión activa desde: {self.detalles_conexion.get('connected_since', 'N/A')}

Tablas disponibles: {len(self.tablas_vars)}"""
        
        messagebox.showinfo("Estado de conexión", info)
    
    def mover_archivos_respaldo(self, tabla):
        if not self.mover_backups_var.get() or not self.ruta_data_actual:
            return
        
        extensiones = ['.dbk', '.ibk', '.bbk']
        movidos = []
        
        for ext in extensiones:
            archivo_origen = os.path.join(self.ruta_data_actual, f"{tabla}{ext}")
            if os.path.exists(archivo_origen):
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                nombre_destino = f"{tabla}_{timestamp}{ext}"
                archivo_destino = os.path.join(self.ruta_backups, nombre_destino)
                
                try:
                    shutil.move(archivo_origen, archivo_destino)
                    movidos.append(f"{tabla}{ext} -> {nombre_destino}")
                except Exception as e:
                    self.resultado_text.insert(tk.END, f"   ⚠️ Error moviendo {archivo_origen}: {e}\n")
        
        if movidos:
            self.resultado_text.insert(tk.END, f"   📦 Respaldos movidos a: {self.ruta_backups}\n")
            for m in movidos:
                self.resultado_text.insert(tk.END, f"      {m}\n")
    
    def conectar(self):
        try:
            dsn = self.dsn_var.get().strip()
            if not dsn:
                messagebox.showwarning("Advertencia", "Debes ingresar un nombre de DSN")
                return
            
            self.dsn_actual = dsn
            usuario = self.usuario_var.get()
            password = self.password_var.get()
            
            cadena_conexion = f'DSN={dsn};UID={usuario};PWD={password}'
            self.conexion = pyodbc.connect(cadena_conexion)
            
            # OBTENER RUTA DEL REGISTRO DE WINDOWS
            ruta_registro = self.obtener_ruta_desde_registro(dsn)
            
            if ruta_registro:
                self.ruta_data_actual = ruta_registro
                self.ruta_label.config(text=self.ruta_data_actual, foreground="green")
            else:
                # Si no encuentra en registro, intentar con consulta SQL
                try:
                    cursor = self.conexion.cursor()
                    cursor.execute("SELECT DB_DIRECTORY()")
                    resultado = cursor.fetchone()
                    if resultado and resultado[0]:
                        self.ruta_data_actual = resultado[0]
                    else:
                        self.ruta_data_actual = f"[Ruta configurada en DSN: {dsn}]"
                    cursor.close()
                except:
                    self.ruta_data_actual = f"[Ruta configurada en DSN: {dsn}]"
                
                self.ruta_label.config(text=self.ruta_data_actual, foreground="blue")
            
            # Guardar detalles de conexión
            self.detalles_conexion = {
                'driver': 'DBISAM 4 ODBC',
                'db_name': dsn,
                'version': '4.35',
                'connected_since': datetime.now().strftime('%d/%m/%Y %H:%M:%S')
            }
            
            # Habilitar botón de estado
            self.estado_btn.config(state="normal")
            
            # Habilitar botones de operaciones
            self.verificar_btn.config(state="normal")
            self.reparar_btn.config(state="normal")
            self.optimizar_btn.config(state="normal")
            self.seleccionar_todo_btn.config(state="normal")
            self.deseleccionar_todo_btn.config(state="normal")
            
            self.listar_tablas()
            
             # GUARDAR CONEXIÓN - AGREGAR ESTAS LÍNEAS
            self.guardar_conexion(dsn, usuario, password)
            
        except Exception as e:
            self.ruta_label.config(text="[Error de conexión]", foreground="red")
            self.estado_btn.config(state="disabled")
            messagebox.showerror("Error", f"No se pudo conectar: {e}")
    
    def listar_tablas(self):
        try:
            cursor = self.conexion.cursor()
            tablas = cursor.tables()
            
            for widget in self.frame_tablas.winfo_children():
                widget.destroy()
            
            self.tablas_vars = {}
            
            lista_tablas = []
            for tabla in tablas:
                nombre_tabla = tabla.table_name
                if nombre_tabla not in lista_tablas and nombre_tabla.isidentifier():
                    lista_tablas.append(nombre_tabla)
            
            # Actualizar contador en detalles
            self.detalles_conexion['tablas_count'] = len(lista_tablas)
            
            columnas = 4
            for i, nombre_tabla in enumerate(sorted(lista_tablas)):
                var = tk.BooleanVar()
                self.tablas_vars[nombre_tabla] = var
                
                chk = ttk.Checkbutton(self.frame_tablas, text=nombre_tabla, variable=var)
                chk.grid(row=i//columnas, column=i%columnas, sticky="w", padx=10, pady=2)
                        
        except Exception as e:
            self.resultado_text.insert(tk.END, f"Error al listar tablas: {e}")
    
    def seleccionar_todas(self):
        for var in self.tablas_vars.values():
            var.set(True)
    
    def deseleccionar_todas(self):
        for var in self.tablas_vars.values():
            var.set(False)
    
    def obtener_tablas_seleccionadas(self):
        return [nombre for nombre, var in self.tablas_vars.items() if var.get()]
    
    def actualizar_progreso(self, valor, total):
        if total > 0:
            porcentaje = int((valor / total) * 100)
            self.progreso['value'] = porcentaje
            self.porcentaje_label.config(text=f"{porcentaje}%")
            self.root.update_idletasks()
    
    def escribir_log(self, tipo_operacion, contenido):
        if not self.generar_log_var.get():
            return
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        nombre_archivo = f"log{tipo_operacion}_{timestamp}.txt"
        ruta_completa = os.path.join(self.ruta_logs, nombre_archivo)
        
        try:
            with open(ruta_completa, 'w', encoding='utf-8') as f:
                f.write(f"=== {tipo_operacion.upper()} - {datetime.now().strftime('%d/%m/%Y %H:%M:%S')} ===\n\n")
                f.write(contenido)
            
            self.resultado_text.insert(tk.END, f"\n📁 Log guardado: {nombre_archivo}\n")
        except Exception as e:
            self.resultado_text.insert(tk.END, f"\n❌ Error al guardar log: {e}\n")
    
    def limpiar_resultados(self):
        self.resultado_text.delete(1.0, tk.END)
    
    # ================== MÉTODOS PUENTE PARA OPERACIONES =====================

     # ================== MÉTODOS PUENTE PARA OPERACIONES =====================
    
    def verificar_seleccionadas(self):
        """Método puente para iniciar verificación desde el botón"""
        if self.operacion_en_curso:
            messagebox.showwarning("Atención", "Ya hay una operación en curso")
            return
        
        tablas = self.obtener_tablas_seleccionadas()
        if not tablas:
            messagebox.showwarning("Advertencia", "No hay tablas seleccionadas")
            return
        
        thread = threading.Thread(target=self._verificar_multiples, args=(tablas,))
        thread.daemon = True
        thread.start()
    
    def reparar_seleccionadas(self):
        """Método puente para iniciar reparación desde el botón"""
        if self.operacion_en_curso:
            messagebox.showwarning("Atención", "Ya hay una operación en curso")
            return
        
        tablas = self.obtener_tablas_seleccionadas()
        if not tablas:
            messagebox.showwarning("Advertencia", "No hay tablas seleccionadas")
            return
        
        respuesta = messagebox.askyesno("Confirmar", 
                                       f"¿Reparar {len(tablas)} tablas?")
        if not respuesta:
            return
        
        thread = threading.Thread(target=self._reparar_multiples, args=(tablas,))
        thread.daemon = True
        thread.start()
    
    # ================== OPERACIONES EN TABLAS =====================
    #===================== VERIFICAR MÚLTIPLES =====================
    def _verificar_multiples(self, tablas):
        self.operacion_en_curso = True
        self.resultado_text.delete(1.0, tk.END)
        
        encabezado = f"VERIFICACIÓN INICIADA - {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n"
        encabezado += "="*60 + "\n"
        encabezado += f"Tablas a verificar: {len(tablas)}\n"
        encabezado += "-"*60 + "\n"
        self.resultado_text.insert(tk.END, encabezado)
        
        # Inicializar manejador de progreso
        progress = ProgressManager(self, len(tablas))
        
        total = len(tablas)
        contenido_log = encabezado
        exitos = 0
        errores = 0
        
        for i, tabla in enumerate(tablas):
            # Iniciar procesamiento de tabla
            progress.iniciar_tabla(tabla)
            
            # Simular diferentes etapas de verificación
            etapas = [
                (10, f"Conectando a tabla {tabla}..."),
                (30, f"Analizando estructura de {tabla}..."),
                (50, f"Verificando índices de {tabla}..."),
                (70, f"Validando integridad de {tabla}..."),
                (90, f"Finalizando verificación de {tabla}...")
            ]
            
            linea_resultado = f"[{i+1}/{total}] Verificando {tabla}... "
            self.resultado_text.insert(tk.END, linea_resultado)
            
            try:
                cursor = self.conexion.cursor()
                
                # Actualizar progreso en diferentes etapas
                for progreso, mensaje in etapas:
                    progress.actualizar_tabla(progreso, mensaje)
                    time.sleep(0.2)  # Simular trabajo (ajusta según necesidad real)
                
                # Ejecutar verificación real
                cursor.execute(f"VERIFY TABLE IF EXISTS {tabla}")
                try:
                    resultados = cursor.fetchall()
                    if resultados:
                        linea_resultado += f"✅ {len(resultados)} advertencias\n"
                        progress.actualizar_tabla(100, f"Verificación completada - {len(resultados)} advertencias")
                        for r in resultados:
                            self.resultado_text.insert(tk.END, f"   {r}\n")
                    else:
                        linea_resultado += "✅ OK\n"
                        progress.actualizar_tabla(100, "Verificación completada - OK")
                except pyodbc.ProgrammingError:
                    linea_resultado += "✅ OK\n"
                    progress.actualizar_tabla(100, "Verificación completada - OK")
                self.conexion.commit()
                exitos += 1
                
            except Exception as e:
                linea_resultado += f"❌ Error\n"
                progress.actualizar_tabla(0, f"Error en verificación: {str(e)[:50]}")
                self.resultado_text.insert(tk.END, f"   Error: {e}\n")
                self.conexion.rollback()
                errores += 1
            finally:
                cursor.close()
            
            progress.completar_tabla()
            progress.resetear_tabla()
            
            self.resultado_text.insert(tk.END, linea_resultado + "\n")
            contenido_log += linea_resultado + "\n"
            self.root.update()
        
        # Resetear barras al finalizar
        self.progreso_detalle['value'] = 0
        self.porcentaje_detalle_label.config(text="0%")
        self.detalle_label.config(text="Operación completada", foreground="green")
        
        resumen = f"\n{'-'*60}\n"
        resumen += f"VERIFICACIÓN FINALIZADA - {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n"
        resumen += f"Total: {total} | Exitosas: {exitos} | Errores: {errores}\n"
        self.resultado_text.insert(tk.END, resumen)
        contenido_log += resumen
        self.escribir_log("verificacion", contenido_log)
        self.root.after(0, lambda: self.mostrar_mensaje_exito("Verificación", tablas, exitos, errores))
        self.operacion_en_curso = False
    
    #===================== REPARAR MÚLTIPLES =====================
    
    def _reparar_multiples(self, tablas):
        self.operacion_en_curso = True
        self.resultado_text.delete(1.0, tk.END)
        
        encabezado = f"REPARACIÓN INICIADA - {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n"
        encabezado += "="*60 + "\n"
        encabezado += f"Tablas a reparar: {len(tablas)}\n"
        encabezado += "-"*60 + "\n\n"
        self.resultado_text.insert(tk.END, encabezado)
        
        progress = ProgressManager(self, len(tablas))
        total = len(tablas)
        contenido_log = encabezado
        exitos = 0
        errores = 0
        
        for i, tabla in enumerate(tablas):
            progress.iniciar_tabla(tabla)
            
            linea_resultado = f"[{i+1}/{total}] Reparando {tabla}... "
            self.resultado_text.insert(tk.END, linea_resultado)
            
            # Simular progreso de reparación
            for p in [20, 40, 60, 80, 100]:
                progress.actualizar_tabla(p, f"Reparando {tabla}... {p}%")
                time.sleep(0.1)
            
            try:
                cursor = self.conexion.cursor()
                cursor.execute(f"REPAIR TABLE IF EXISTS {tabla}")
                self.conexion.commit()
                
                linea_resultado += "✅ Completada\n"
                progress.actualizar_tabla(100, f"Reparación completada")
                exitos += 1
                
            except Exception as e:
                linea_resultado += f"❌ Error\n"
                progress.actualizar_tabla(0, f"Error: {str(e)[:50]}")
                self.resultado_text.insert(tk.END, f"   Error: {e}\n")
                self.conexion.rollback()
                errores += 1
            finally:
                cursor.close()
            
            progress.completar_tabla()
            progress.resetear_tabla()
            
            self.resultado_text.insert(tk.END, linea_resultado + "\n")
            contenido_log += linea_resultado + "\n"
            self.root.update()
        
        # Resetear barras
        self.progreso_detalle['value'] = 0
        self.porcentaje_detalle_label.config(text="0%")
        self.detalle_label.config(text="Reparación completada", foreground="green")
        
        resumen = f"\n{'-'*60}\n"
        resumen += f"REPARACIÓN FINALIZADA - {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n"
        resumen += f"Total: {total} | Exitosas: {exitos} | Errores: {errores}\n"
        
        self.resultado_text.insert(tk.END, resumen)
        contenido_log += resumen
        self.escribir_log("reparacion", contenido_log)
        self.root.after(0, lambda: self.mostrar_mensaje_exito("Reparación", tablas, exitos, errores))
        self.operacion_en_curso = False
    
    #===================== OPTIMIZAR MÚLTIPLES =====================
    
    def optimizar_seleccionadas(self):
        if self.operacion_en_curso:
            messagebox.showwarning("Atención", "Ya hay una operación en curso")
            return
        
        tablas = self.obtener_tablas_seleccionadas()
        if not tablas:
            messagebox.showwarning("Advertencia", "No hay tablas seleccionadas")
            return
        
        respuesta = messagebox.askyesno("Confirmar", 
                                       f"¿Optimizar {len(tablas)} tablas?\n\n"
                                       "Se crearán archivos de respaldo.")
        if not respuesta:
            return
        
        thread = threading.Thread(target=self._optimizar_multiples, args=(tablas,))
        thread.daemon = True
        thread.start()
    
    def _optimizar_multiples(self, tablas):
        self.operacion_en_curso = True
        self.resultado_text.delete(1.0, tk.END)
        
        encabezado = f"OPTIMIZACIÓN INICIADA - {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n"
        encabezado += "="*60 + "\n"
        encabezado += f"Tablas a optimizar: {len(tablas)}\n"
        encabezado += "-"*60 + "\n\n"
        self.resultado_text.insert(tk.END, encabezado)
        
        # Inicializar manejador de progreso
        progress = ProgressManager(self, len(tablas))
        
        total = len(tablas)
        contenido_log = encabezado
        exitos = 0
        errores = 0
        
        for i, tabla in enumerate(tablas):
            progress.iniciar_tabla(tabla)
            
            linea_resultado = f"[{i+1}/{total}] Optimizando {tabla}... "
            self.resultado_text.insert(tk.END, linea_resultado)
            
            # Simular progreso de optimización
            etapas = [
                (20, f"Preparando optimización de {tabla}..."),
                (40, f"Analizando índices de {tabla}..."),
                (60, f"Reorganizando datos de {tabla}..."),
                (80, f"Generando respaldos de {tabla}..."),
                (95, f"Finalizando optimización de {tabla}...")
            ]
            
            for progreso, mensaje in etapas:
                progress.actualizar_tabla(progreso, mensaje)
                time.sleep(0.1)
            
            try:
                cursor = self.conexion.cursor()
                cursor.execute(f"OPTIMIZE TABLE {tabla}")
                self.conexion.commit()
                
                linea_resultado += "✅ Completada\n"
                linea_resultado += f"   Respaldos generados: {tabla}.dbk, {tabla}.ibk, {tabla}.bbk\n"
                progress.actualizar_tabla(100, f"Optimización completada - {tabla}")
                exitos += 1
                
                # Mover archivos de respaldo si está activado
                self.mover_archivos_respaldo(tabla)
                
            except Exception as e:
                linea_resultado += f"❌ Error\n"
                progress.actualizar_tabla(0, f"Error en optimización: {str(e)[:50]}")
                self.resultado_text.insert(tk.END, f"   Error: {e}\n")
                self.conexion.rollback()
                errores += 1
            finally:
                cursor.close()
            
            progress.completar_tabla()
            progress.resetear_tabla()
            
            self.resultado_text.insert(tk.END, linea_resultado + "\n")
            contenido_log += linea_resultado + "\n"
            self.root.update()
        
        # Resetear barras
        self.progreso_detalle['value'] = 0
        self.porcentaje_detalle_label.config(text="0%")
        self.detalle_label.config(text="Optimización completada", foreground="green")
        
        resumen = f"\n{'-'*60}\n"
        resumen += f"OPTIMIZACIÓN FINALIZADA - {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n"
        resumen += f"Total: {total} | Exitosas: {exitos} | Errores: {errores}\n"
        
        self.resultado_text.insert(tk.END, resumen)
        contenido_log += resumen
        
        self.escribir_log("optimizacion", contenido_log)
        
        # Mostrar mensaje de éxito
        self.root.after(0, lambda: self.mostrar_mensaje_exito("Optimización", tablas, exitos, errores))
        self.operacion_en_curso = False
    
    def ejecutar_ajuste_saldos(self):
        if not self.conexion:
            messagebox.showwarning("Sin conexión", "Debe conectarse primero")
            return
        
        if not self.ajustar_cxc_var.get() and not self.ajustar_cxp_var.get():
            messagebox.showwarning("Advertencia", "Debe seleccionar al menos una opción")
            return
        
        respuesta = messagebox.askyesno(
            "Confirmar", 
            "¿Está seguro de ajustar saldos menores a 0.01 a cero?\n\n"
            "Se actualizarán:\n" +
            ("• Cuentas por Cobrar\n" if self.ajustar_cxc_var.get() else "") +
            ("• Cuentas por Pagar" if self.ajustar_cxp_var.get() else "")
        )
        
        if not respuesta:
            return
        
        self.resultado_text.delete(1.0, tk.END)
        self.resultado_text.insert(tk.END, f"\n--- INICIANDO AJUSTE DE SALDOS ---\n")
        
        thread = threading.Thread(target=self._ejecutar_ajuste_saldos)
        thread.daemon = True
        thread.start()

    def _ejecutar_ajuste_saldos(self):
        try:
            cursor = self.conexion.cursor()
            total_actualizados = 0
            
            # Lista de consultas
            consultas = [
                "UPDATE SCUENTASXCOBRAR SET FCC_SALDODOCUMENTO = 0 WHERE FCC_SALDODOCUMENTO BETWEEN -0.01 AND 0.01 AND FCC_SALDODOCUMENTO <> 0.00000",
                "UPDATE SCUENTASXCOBRAR SET FCC_SALDOMONEDAEXT = 0 WHERE FCC_SALDOMONEDAEXT BETWEEN -0.01 AND 0.01 AND FCC_SALDOMONEDAEXT <> 0.00000",
                "UPDATE SCUENTASXPAGAR SET FCP_SALDODOCUMENTO = 0 WHERE FCP_SALDODOCUMENTO BETWEEN -0.01 AND 0.01 AND FCP_SALDODOCUMENTO <> 0.00000",
                "UPDATE SCUENTASXPAGAR SET FCP_SALDOMONEDAEXT = 0 WHERE FCP_SALDOMONEDAEXT BETWEEN -0.01 AND 0.01 AND FCP_SALDOMONEDAEXT <> 0.00000"
            ]
            
            total_consultas = len(consultas)
            self.progreso['value'] = 0
            self.porcentaje_label.config(text="0%")
            
            for i, consulta in enumerate(consultas):
                # Actualizar barra de progreso
                porcentaje = int((i / total_consultas) * 100)
                self.progreso['value'] = porcentaje
                self.porcentaje_label.config(text=f"{porcentaje}%")
                
                self.resultado_text.insert(tk.END, f"Ejecutando consulta {i+1}/{total_consultas}...\n")
                self.root.update()
                
                cursor.execute(consulta)
                filas_afectadas = cursor.rowcount
                total_actualizados += filas_afectadas
                self.conexion.commit()
                
                self.resultado_text.insert(tk.END, f"  → {filas_afectadas} registros actualizados\n")
            
            # Barra al 100% al finalizar
            self.progreso['value'] = 100
            self.porcentaje_label.config(text="100%")
            cursor.close()
            
            self.resultado_text.insert(tk.END, f"\n✅ AJUSTE COMPLETADO: {total_actualizados} registros actualizados\n")
            
            # Desmarcar checkbox
            # self.ajustar_saldos_var.set(False)
           
        except Exception as e:
            self.progreso['value'] = 0
            self.porcentaje_label.config(text="0%")
            self.resultado_text.insert(tk.END, f"\n❌ ERROR: {e}\n")
            self.conexion.rollback()
            
    def cargar_conexion_seleccionada(self, event):
        """Carga los datos de la conexión seleccionada en el combobox"""
        try:
            if os.path.exists(self.ruta_conexiones):
                with open(self.ruta_conexiones, 'r', encoding='utf-8') as f:
                    conexiones = json.load(f)
                
                dsn_seleccionado = self.dsn_var.get()
                for conn in conexiones:
                    if conn['dsn'] == dsn_seleccionado:
                        self.usuario_var.set(conn.get('usuario', ''))
                        self.password_var.set(conn.get('password', ''))
                        break
        except Exception as e:
            print(f"Error cargando conexión seleccionada: {e}")
    
    #------------------- MÉTODOS AUXILIARES --------------------
    def mostrar_mensaje_exito(self, operacion, tablas, exitos, errores):
        """Muestra mensaje de éxito y restaura las barras de progreso"""
        mensaje = f"{operacion} culminada con éxito\n\n"
        mensaje += f"Tablas procesadas: {len(tablas)}\n"
        mensaje += f"Exitosas: {exitos}\n"
        mensaje += f"Errores: {errores}"
        
        messagebox.showinfo(f"{operacion} completada", mensaje)
        
        # Restaurar barras de progreso a valores iniciales
        self.progreso['value'] = 0
        self.porcentaje_label.config(text="0%")
        self.progreso_detalle['value'] = 0
        self.porcentaje_detalle_label.config(text="0%")
        self.detalle_label.config(text="Esperando operación...", foreground="gray")

if __name__ == "__main__":
    root = tk.Tk()
    app = ArkToolsDBisam(root)
    root.mainloop()