import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import pyodbc
import threading
import time
import os
import shutil
import winreg
from datetime import datetime

class MantenimientoBDIsam:
    def __init__(self, root):
        self.root = root
        self.root.title("Mantenimiento de Tablas BDIsam")
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
        
        # Crear carpetas si no existen
        for ruta in [self.ruta_logs, self.ruta_backups]:
            if not os.path.exists(ruta):
                os.makedirs(ruta)
        
        self.crear_interfaz()
    
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
    
    def crear_interfaz(self):
        # Marco superior con dos columnas: Conexión y Acerca de
        marco_superior = ttk.Frame(self.root)
        marco_superior.pack(fill="x", padx=10, pady=5)
        
        # Columna izquierda: Conexión
        marco_conexion = ttk.LabelFrame(marco_superior, text="Conexión a Base de Datos", padding=10)
        marco_conexion.pack(side="left", fill="x", expand=True)
        
        ttk.Label(marco_conexion, text="DSN:").grid(row=0, column=0, sticky="w")
        self.dsn_var = tk.StringVar()
        ttk.Entry(marco_conexion, textvariable=self.dsn_var, width=30).grid(row=0, column=1, padx=5)
        
        ttk.Label(marco_conexion, text="Usuario:").grid(row=1, column=0, sticky="w")
        # self.usuario_var = tk.StringVar(value="master")
        self.usuario_var = tk.StringVar() 
        ttk.Entry(marco_conexion, textvariable=self.usuario_var).grid(row=1, column=1, padx=5)
        
        ttk.Label(marco_conexion, text="Contraseña:").grid(row=2, column=0, sticky="w")
        self.password_var = tk.StringVar()
        ttk.Entry(marco_conexion, textvariable=self.password_var, show="*").grid(row=2, column=1, padx=5)
        
        self.conectar_btn = ttk.Button(marco_conexion, text="Conectar", command=self.conectar)
        self.conectar_btn.grid(row=3, column=0, columnspan=2, pady=10)
        
        # Columna derecha: Botón Acerca de
        marco_acerca = ttk.Frame(marco_superior)
        marco_acerca.pack(side="right", padx=(10,0), fill="y")
        
        self.acerca_btn = ttk.Button(marco_acerca, text="Acerca de...", command=self.mostrar_acerca)
        self.acerca_btn.pack(pady=20, padx=10)
        
        # Marco para la ruta y botón de estado
        marco_ruta_estado = ttk.LabelFrame(self.root, text="Ruta de conexión ODBC y Estado", padding=10)
        marco_ruta_estado.pack(fill="x", padx=10, pady=5)
        
        # Frame interno para organizar ruta y botón
        frame_ruta = ttk.Frame(marco_ruta_estado)
        frame_ruta.pack(fill="x")
        
        # Etiqueta para la ruta
        ttk.Label(frame_ruta, text="Ruta de conexión:").pack(side="left", padx=5)
        self.ruta_label = ttk.Label(frame_ruta, text="[No conectado]", foreground="gray")
        self.ruta_label.pack(side="left", padx=5)
        
        # Botón de estado
        self.estado_btn = ttk.Button(frame_ruta, text="Ver estado de conexión", 
                                     command=self.mostrar_estado_conexion, state="disabled")
        self.estado_btn.pack(side="right", padx=5)
        
        # Barra de progreso
        marco_progreso = ttk.LabelFrame(self.root, text="Progreso", padding=5)
        marco_progreso.pack(fill="x", padx=10, pady=5)
        
        self.progreso = ttk.Progressbar(marco_progreso, orient="horizontal", length=100, mode="determinate")
        self.progreso.pack(fill="x", padx=5, pady=5)
        
        self.porcentaje_label = ttk.Label(marco_progreso, text="0%")
        self.porcentaje_label.pack(anchor="e", padx=5)
        
        # Marco de pestañas
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Pestaña 1: Tablas disponibles
        self.tab_tablas = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_tablas, text="Tablas disponibles")
        
        # Pestaña 2: Resultados de operaciones
        self.tab_resultados = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_resultados, text="Resultados de operaciones")
        
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
        
        # Checkbox para generar archivo log
        self.generar_log_var = tk.BooleanVar(value=True)
        self.log_check = ttk.Checkbutton(marco_seleccion, text="Generar archivo de log", 
                                         variable=self.generar_log_var)
        self.log_check.pack(side="left", padx=20)
        
        # Checkbox para mover backups
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
    
    def mostrar_acerca(self):
        info_acerca = """ManteDBIsam v0.1.4Beta

Desarrollado por Juan E. Páez M.
JUEPAE
Fecha: Marzo 2026

Herramienta de mantenimiento
para bases de datos DBISam
vía ODBC 32 bits"""
        
        messagebox.showinfo("Acerca de ManteDBIsam", info_acerca)
    
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
            
            columnas = 3
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
    
    def verificar_seleccionadas(self):
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
    
    def _verificar_multiples(self, tablas):
        self.operacion_en_curso = True
        self.resultado_text.delete(1.0, tk.END)
        
        encabezado = f"VERIFICACIÓN INICIADA - {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n"
        encabezado += "="*60 + "\n"
        encabezado += f"Tablas a verificar: {len(tablas)}\n"
        encabezado += "-"*60 + "\n\n"
        self.resultado_text.insert(tk.END, encabezado)
        
        self.progreso['value'] = 0
        self.porcentaje_label.config(text="0%")
        total = len(tablas)
        
        contenido_log = encabezado
        exitos = 0
        errores = 0
        
        for i, tabla in enumerate(tablas):
            self.actualizar_progreso(i + 1, total)
            
            linea_resultado = f"[{i+1}/{total}] Verificando {tabla}... "
            self.resultado_text.insert(tk.END, linea_resultado)
            self.root.update()
            
            try:
                cursor = self.conexion.cursor()
                cursor.execute(f"VERIFY TABLE IF EXISTS {tabla}")
                
                try:
                    resultados = cursor.fetchall()
                    if resultados:
                        linea_resultado += f"✅ {len(resultados)} advertencias\n"
                        for r in resultados:
                            self.resultado_text.insert(tk.END, f"   {r}\n")
                    else:
                        linea_resultado += "✅ OK\n"
                except pyodbc.ProgrammingError:
                    linea_resultado += "✅ OK\n"
                
                self.conexion.commit()
                exitos += 1
                
            except Exception as e:
                linea_resultado += f"❌ Error\n"
                self.resultado_text.insert(tk.END, f"   Error: {e}\n")
                self.conexion.rollback()
                errores += 1
            finally:
                cursor.close()
            
            self.resultado_text.insert(tk.END, linea_resultado + "\n")
            contenido_log += linea_resultado + "\n"
            self.root.update()
            time.sleep(0.05)
        
        resumen = f"\n{'-'*60}\n"
        resumen += f"VERIFICACIÓN FINALIZADA - {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n"
        resumen += f"Total: {total} | Exitosas: {exitos} | Errores: {errores}\n"
        
        self.resultado_text.insert(tk.END, resumen)
        contenido_log += resumen
        
        self.escribir_log("verificacion", contenido_log)
        
        self.operacion_en_curso = False
    
    def reparar_seleccionadas(self):
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
    
    def _reparar_multiples(self, tablas):
        self.operacion_en_curso = True
        self.resultado_text.delete(1.0, tk.END)
        
        encabezado = f"REPARACIÓN INICIADA - {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n"
        encabezado += "="*60 + "\n"
        encabezado += f"Tablas a reparar: {len(tablas)}\n"
        encabezado += "-"*60 + "\n\n"
        self.resultado_text.insert(tk.END, encabezado)
        
        self.progreso['value'] = 0
        self.porcentaje_label.config(text="0%")
        total = len(tablas)
        
        contenido_log = encabezado
        exitos = 0
        errores = 0
        
        for i, tabla in enumerate(tablas):
            self.actualizar_progreso(i + 1, total)
            
            linea_resultado = f"[{i+1}/{total}] Reparando {tabla}... "
            self.resultado_text.insert(tk.END, linea_resultado)
            self.root.update()
            
            try:
                cursor = self.conexion.cursor()
                cursor.execute(f"REPAIR TABLE IF EXISTS {tabla}")
                self.conexion.commit()
                
                linea_resultado += "✅ Completada\n"
                exitos += 1
                
            except Exception as e:
                linea_resultado += f"❌ Error\n"
                self.resultado_text.insert(tk.END, f"   Error: {e}\n")
                self.conexion.rollback()
                errores += 1
            finally:
                cursor.close()
            
            self.resultado_text.insert(tk.END, linea_resultado + "\n")
            contenido_log += linea_resultado + "\n"
            self.root.update()
            time.sleep(0.05)
        
        resumen = f"\n{'-'*60}\n"
        resumen += f"REPARACIÓN FINALIZADA - {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n"
        resumen += f"Total: {total} | Exitosas: {exitos} | Errores: {errores}\n"
        
        self.resultado_text.insert(tk.END, resumen)
        contenido_log += resumen
        
        self.escribir_log("reparacion", contenido_log)
        
        self.operacion_en_curso = False
    
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
        
        self.progreso['value'] = 0
        self.porcentaje_label.config(text="0%")
        total = len(tablas)
        
        contenido_log = encabezado
        exitos = 0
        errores = 0
        
        for i, tabla in enumerate(tablas):
            self.actualizar_progreso(i + 1, total)
            
            linea_resultado = f"[{i+1}/{total}] Optimizando {tabla}... "
            self.resultado_text.insert(tk.END, linea_resultado)
            self.root.update()
            
            try:
                cursor = self.conexion.cursor()
                cursor.execute(f"OPTIMIZE TABLE {tabla}")
                self.conexion.commit()
                
                linea_resultado += "✅ Completada\n"
                linea_resultado += f"   Respaldos generados: {tabla}.dbk, {tabla}.ibk, {tabla}.bbk\n"
                exitos += 1
                
                # Mover archivos de respaldo si está activado
                self.mover_archivos_respaldo(tabla)
                
            except Exception as e:
                linea_resultado += f"❌ Error\n"
                self.resultado_text.insert(tk.END, f"   Error: {e}\n")
                self.conexion.rollback()
                errores += 1
            finally:
                cursor.close()
            
            self.resultado_text.insert(tk.END, linea_resultado + "\n")
            contenido_log += linea_resultado + "\n"
            self.root.update()
            time.sleep(0.05)
        
        resumen = f"\n{'-'*60}\n"
        resumen += f"OPTIMIZACIÓN FINALIZADA - {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n"
        resumen += f"Total: {total} | Exitosas: {exitos} | Errores: {errores}\n"
        
        self.resultado_text.insert(tk.END, resumen)
        contenido_log += resumen
        
        self.escribir_log("optimizacion", contenido_log)
        
        self.operacion_en_curso = False

if __name__ == "__main__":
    root = tk.Tk()
    app = MantenimientoBDIsam(root)
    root.mainloop()