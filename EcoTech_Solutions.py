import sqlite3
import hashlib
import re
import urllib.request
import urllib.error
import json
from typing import Optional, Dict, List, Any

TEXTO_OPCION = "Opción: "
OPCION_NO_VALIDA = "Opción no válida."


# -------------------------- UNIDAD 2: POO y Base de Datos --------------------------

class Persona:
    """Clase base que representa una persona (aplicación de herencia)"""
    def __init__(self, nombre: str, correo: str):
        self._nombre = nombre.strip()
        self._correo = correo.strip()

    @property
    def nombre(self) -> str:
        return self._nombre

    @property
    def correo(self) -> str:
        return self._correo


class Empleado(Persona):
    """Clase derivada: Empleado hereda de Persona"""
    def __init__(self, nombre: str, correo: str, cargo: str, sueldo: float):
        super().__init__(nombre, correo)
        self._cargo = cargo.strip()
        self._sueldo = sueldo

    @property
    def cargo(self) -> str:
        return self._cargo

    @property
    def sueldo(self) -> float:
        return self._sueldo


class BaseDeDatos:
    """Gestiona la conexión y operaciones con SQLite"""
    EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$')

    def __init__(self, archivo="ecotech.db"):
        self.archivo = archivo
        self.conexion = None
        self.cursor = None
        self.conectar()
        self.crear_tablas()
        self.crear_usuario_admin()

    def conectar(self) -> None:
        try:
            self.conexion = sqlite3.connect(self.archivo)
            self.conexion.row_factory = sqlite3.Row
            self.cursor = self.conexion.cursor()
        except sqlite3.Error as error:
            print(f" Error al conectar: {error}")
            raise

    def desconectar(self) -> None:
        if hasattr(self, 'cursor') and self.cursor:
            self.cursor.close()
        if hasattr(self, 'conexion') and self.conexion:
            self.conexion.close()

    def cerrar(self) -> None:
        self.desconectar()

    def _cifrar_contrasena(self, contrasena: str) -> str:
        """Cifra contraseña con SHA-256. Decisión: se eligió este método por simplicidad y compatibilidad."""
        return hashlib.sha256(contrasena.encode('utf-8')).hexdigest()

    def crear_tablas(self) -> None:
        try:
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS usuarios (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nombre TEXT NOT NULL,
                    correo TEXT NOT NULL UNIQUE,
                    usuario TEXT NOT NULL UNIQUE,
                    contrasena TEXT NOT NULL
                )
            """)
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS empleados (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nombre TEXT NOT NULL,
                    correo TEXT NOT NULL UNIQUE,
                    cargo TEXT NOT NULL,
                    sueldo REAL NOT NULL
                )
            """)
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS proyectos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nombre TEXT NOT NULL,
                    descripcion TEXT,
                    ciudad TEXT NOT NULL,
                    fecha_inicio TEXT,
                    estado TEXT DEFAULT 'Activo'
                )
            """)
            self.conexion.commit()
        except sqlite3.Error as error:
            print(f" Error al crear tablas: {error}")
            raise

    def crear_usuario_admin(self) -> None:
        try:
            self.cursor.execute("SELECT id FROM usuarios WHERE usuario = ?", ("admin",))
            if not self.cursor.fetchone():
                hash_pass = self._cifrar_contrasena("1234")
                self.cursor.execute("""
                    INSERT INTO usuarios (nombre, correo, usuario, contrasena)
                    VALUES (?, ?, ?, ?)
                """, ("Administrador EcoTech", "admin@ecotech.cl", "admin", hash_pass))
                self.conexion.commit()
        except sqlite3.Error as error:
            print(f"Error al crear administrador: {error}")

    def validar_correo(self, correo: str) -> bool:
        return bool(self.EMAIL_REGEX.match(correo.strip()))

    # --- CRUD Empleados ---
    def agregar_empleado(self, nombre: str, correo: str, cargo: str, sueldo: float) -> bool:
        if not all([nombre.strip(), correo.strip(), cargo.strip()]):
            print(" Todos los campos son obligatorios.")
            return False
        if not self.validar_correo(correo):
            print(" Formato de correo inválido.")
            return False
        if sueldo <= 0:
            print("El sueldo debe ser mayor a cero.")
            return False
        try:
            self.cursor.execute("""
                INSERT INTO empleados (nombre, correo, cargo, sueldo)
                VALUES (?, ?, ?, ?)
            """, (nombre.strip(), correo.strip(), cargo.strip(), sueldo))
            self.conexion.commit()
            print(" Empleado registrado correctamente.")
            return True
        except sqlite3.IntegrityError:
            print(" El correo ya está registrado.")
            return False
        except sqlite3.Error as error:
            print(f" Error: {error}")
            return False

    def listar_empleados(self) -> List[sqlite3.Row]:
        self.cursor.execute("SELECT * FROM empleados ORDER BY id")
        return self.cursor.fetchall()

    def existe_empleado_id(self, emp_id: int) -> bool:
        self.cursor.execute("SELECT 1 FROM empleados WHERE id = ?", (emp_id,))
        return self.cursor.fetchone() is not None

    def actualizar_empleado(self, emp_id: int, nombre: str, correo: str, cargo: str, sueldo: float) -> bool:
        if not self.existe_empleado_id(emp_id):
            print("Empleado no encontrado.")
            return False
        if not all([nombre.strip(), correo.strip(), cargo.strip()]):
            print(" Todos los campos son obligatorios.")
            return False
        if not self.validar_correo(correo):
            print(" Formato de correo inválido.")
            return False
        try:
            self.cursor.execute("""
                UPDATE empleados
                SET nombre = ?, correo = ?, cargo = ?, sueldo = ?
                WHERE id = ?
            """, (nombre.strip(), correo.strip(), cargo.strip(), sueldo, emp_id))
            self.conexion.commit()
            print(" Empleado actualizado.")
            return True
        except sqlite3.IntegrityError:
            print(" El correo pertenece a otro empleado.")
            return False
        except sqlite3.Error as error:
            print(f" Error: {error}")
            return False

    def eliminar_empleado(self, emp_id: int) -> bool:
        if not self.existe_empleado_id(emp_id):
            print(" Empleado no encontrado.")
            return False
        self.cursor.execute("DELETE FROM empleados WHERE id = ?", (emp_id,))
        self.conexion.commit()
        print("✅ Empleado eliminado.")
        return True

    def login(self, usuario: str, contrasena: str) -> Optional[sqlite3.Row]:
        hash_pass = self._cifrar_contrasena(contrasena)
        self.cursor.execute("""
            SELECT id, nombre, usuario FROM usuarios
            WHERE usuario = ? AND contrasena = ?
        """, (usuario.strip(), hash_pass))
        return self.cursor.fetchone()

    def agregar_proyecto(self, nombre: str, descripcion: str, ciudad: str, fecha: str) -> bool:
        if not all([nombre.strip(), ciudad.strip()]):
            print(" Nombre y ciudad son obligatorios.")
            return False
        try:
            self.cursor.execute("""
                INSERT INTO proyectos (nombre, descripcion, ciudad, fecha_inicio)
                VALUES (?, ?, ?, ?)
            """, (nombre.strip(), descripcion.strip(), ciudad.strip(), fecha.strip()))
            self.conexion.commit()
            print(" Proyecto creado.")
            return True
        except sqlite3.Error as error:
            print(f" Error: {error}")
            return False

    def listar_proyectos(self) -> List[sqlite3.Row]:
        self.cursor.execute("SELECT * FROM proyectos ORDER BY id")
        return self.cursor.fetchall()

    def eliminar_proyecto(self, proyecto_id: int) -> bool:
        self.cursor.execute(
            "SELECT 1 FROM proyectos WHERE id = ?", (proyecto_id,)
        )
        if not self.cursor.fetchone():
            print(" Proyecto no encontrado.")
            return False

        self.cursor.execute(
            "DELETE FROM proyectos WHERE id = ?", (proyecto_id,)
        )

        self.conexion.commit()
        print("✅ Proyecto eliminado.")
        return True
# -------------------------- UNIDAD 3: Consumo de APIs SIN librerías externas --------------------------

class ServiciosExternos:
    """Consumo de APIs usando urllib (incluida en Python estándar)"""

    @staticmethod
    def _hacer_peticion(url: str) -> Dict[str, Any]:
        """Método auxiliar con manejo de errores de red"""
        try:
            with urllib.request.urlopen(url, timeout=10) as respuesta:
                return json.loads(respuesta.read().decode())
        except urllib.error.HTTPError as e:
            return {"error": f"Error del servicio: código {e.code}"}
        except urllib.error.URLError:
            return {"error": "Sin conexión a internet o servicio no disponible."}
        except json.JSONDecodeError:
            return {"error": "El servicio devolvió información inválida."}
        except Exception:
            return {"error": "Error al consultar el servicio."}

    @staticmethod
    def consultar_clima(ciudad: str) -> Dict[str, Any]:
        if not ciudad.strip():
            return {"error": "El nombre de la ciudad es obligatorio."}

        # 1. Obtener coordenadas
        url_geo = f"https://geocoding-api.open-meteo.com/v1/search?name={ciudad.strip()}&count=1&language=es"
        datos_geo = ServiciosExternos._hacer_peticion(url_geo)

        if "error" in datos_geo:
            return datos_geo
        if not datos_geo.get("results"):
            return {"error": f"No se encontró la ciudad: {ciudad}"}

        ubicacion = datos_geo["results"][0]
        lat = ubicacion["latitude"]
        lon = ubicacion["longitude"]
        nombre_ciudad = ubicacion["name"]

        # 2. Obtener clima
        url_clima = (
            f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
            "&current=temperature_2m,relative_humidity_2m,weather_code"
            "&timezone=auto"
        )
        datos_clima = ServiciosExternos._hacer_peticion(url_clima)

        if "error" in datos_clima:
            return datos_clima

        clima_actual = datos_clima["current"]
        return {
            "ciudad": nombre_ciudad,
            "temperatura": clima_actual["temperature_2m"],
            "humedad": clima_actual["relative_humidity_2m"],
            "codigo_clima": clima_actual["weather_code"],
            "exitoso": True
        }

    @staticmethod
    def consultar_tasa_cambio(moneda_base: str, moneda_destino: str, monto: float) -> Dict[str, Any]:
        moneda_base = moneda_base.strip().upper()
        moneda_destino = moneda_destino.strip().upper()

        if len(moneda_base) != 3 or len(moneda_destino) != 3:
            return {"error": "Códigos de moneda deben de 3 caracteres (ej: USD, EUR, CLP)."}
        if monto <= 0:
            return {"error": "El monto debe ser mayor a cero."}

        url = f"https://open.er-api.com/v6/latest/{moneda_base}"
        datos = ServiciosExternos._hacer_peticion(url)

        if "error" in datos:
            return datos
        if datos.get("result") != "success":
            return {"error": "El servicio de cambio no respondió correctamente."}

        tasa = datos["rates"].get(moneda_destino)
        if tasa is None:
            return {"error": f"No hay tasa disponible para {moneda_destino}."}

        return {
            "base": moneda_base,
            "destino": moneda_destino,
            "tasa": tasa,
            "monto_original": monto,
            "monto_convertido": round(monto * tasa, 2),
            "actualizado": datos["time_last_update_utc"],
            "exitoso": True
        }


# -------------------------- Interfaz de Usuario --------------------------

def iniciar_sesion(bd: BaseDeDatos) -> bool:
    print("\n" + "="*40)
    print("   INICIO DE SESIÓN — EcoTech Solutions")
    print("="*40)
    for intento in range(3, 0, -1):
        usuario = input("Usuario: ").strip()
        contrasena = input("Contraseña: ").strip()
        res = bd.login(usuario, contrasena)
        if res:
            print(f"\n✅ Bienvenido, {res['nombre']}!")
            return True
        print(f" Credenciales incorrectas. Intentos restantes: {intento - 1}")
    print("🔒 Acceso bloqueado.")
    return False


def agregar_empleado_menu(bd: BaseDeDatos):
    print("\nAgregar Empleado")
    nombre = input("Nombre: ")
    correo = input("Correo: ")
    cargo = input("Cargo: ")

    try:
        sueldo = float(input("Sueldo: "))
    except ValueError:
        print(" El sueldo debe ser un número.")
        return

    bd.agregar_empleado(nombre, correo, cargo, sueldo)


def listar_empleados_menu(bd: BaseDeDatos):
    empleados = bd.listar_empleados()

    if not empleados:
        print(" No hay empleados registrados.")
        return

    print("\nLista de Empleados:")

    for empleado in empleados:
        print(
            f"ID: {empleado['id']} | {empleado['nombre']} | "
            f"{empleado['correo']} | {empleado['cargo']} | "
            f"${empleado['sueldo']:,.2f}"
        )


def actualizar_empleado_menu(bd: BaseDeDatos):
    try:
        id_empleado = int(input("ID del empleado: "))
        sueldo = float(input("Nuevo sueldo: "))
    except ValueError:
        print(" ID y sueldo deben ser números válidos.")
        return

    bd.actualizar_empleado(
        id_empleado,
        input("Nuevo nombre: "),
        input("Nuevo correo: "),
        input("Nuevo cargo: "),
        sueldo
    )


def eliminar_empleado_menu(bd: BaseDeDatos):
    try:
        id_empleado = int(input("ID del empleado: "))
    except ValueError:
        print(" ID debe ser un número.")
        return

    confirmacion = input(
        f"¿Eliminar empleado {id_empleado}? (s/n): "
    ).strip().lower()

    if confirmacion == "s":
        bd.eliminar_empleado(id_empleado)
    elif confirmacion == "n":
        print(" Eliminación cancelada.")
    else:
        print(" Opción no válida.")  # No hacer nada si la respuesta no es válida


def menu_empleados(bd: BaseDeDatos):
    acciones = {
        "1": agregar_empleado_menu,
        "2": listar_empleados_menu,
        "3": actualizar_empleado_menu,
        "4": eliminar_empleado_menu
    }

    while True:
        print("\n--- Gestión de Empleados ---")
        print("1. Agregar empleado")
        print("2. Listar empleados")
        print("3. Actualizar empleado")
        print("4. Eliminar empleado")
        print("5. Volver al menú principal")

        opcion = input(TEXTO_OPCION).strip()

        if opcion == "5":
            break

        accion = acciones.get(opcion)

        if accion:
            accion(bd)
        else:
            print(OPCION_NO_VALIDA)


def consultar_clima_menu():
    ciudad = input("\nNombre de la ciudad: ")
    clima = ServiciosExternos.consultar_clima(ciudad)

    if clima.get("exitoso"):
        print(f"\n Clima en {clima['ciudad']}:")
        print(f"   Temperatura: {clima['temperatura']}°C")
        print(f"   Humedad: {clima['humedad']}%")
    else:
        print(f" {clima['error']}")


def convertir_moneda_menu():
    print("\nConversión de Moneda")
    base = input("Moneda base (3 letras, ej: USD): ")
    destino = input("Moneda destino (ej: EUR): ")

    try:
        monto = float(input("Monto a convertir: "))
    except ValueError:
        print(" El monto debe ser un número.")
        return

    resultado = ServiciosExternos.consultar_tasa_cambio(
        base,
        destino,
        monto
    )

    if resultado.get("exitoso"):
        print(
            f"\n {resultado['monto_original']} "
            f"{resultado['base']} = "
            f"{resultado['monto_convertido']} "
            f"{resultado['destino']}"
        )
        print(
            f"   Tasa: 1 {resultado['base']} = "
            f"{resultado['tasa']} {resultado['destino']}"
        )
    else:
        print(f" {resultado['error']}")


def menu_servicios_externos():
    acciones = {
        "1": consultar_clima_menu,
        "2": convertir_moneda_menu
    }

    while True:
        print("\n--- Servicios Externos ---")
        print("1. Consultar clima por ciudad")
        print("2. Convertir monto a moneda extranjera")
        print("3. Volver al menú principal")

        opcion = input(TEXTO_OPCION).strip()

        if opcion == "3":
            break

        accion = acciones.get(opcion)

        if accion:
            accion()
        else:
            print(OPCION_NO_VALIDA)


def agregar_proyecto_menu(bd: BaseDeDatos):
    print("\nNuevo Proyecto")
    bd.agregar_proyecto(
        input("Nombre del proyecto: "),
        input("Descripción: "),
        input("Ciudad de ejecución: "),
        input("Fecha de inicio (AAAA-MM-DD): ")
    )


def listar_proyectos_menu(bd: BaseDeDatos):
    proyectos = bd.listar_proyectos()

    if not proyectos:
        print(" No hay proyectos registrados.")
        return

    print("\nLista de Proyectos:")

    for numero, proyecto in enumerate(proyectos, start=1):
        print(f"ID: {numero} | {proyecto['nombre']} | "
            f"Ciudad: {proyecto['ciudad']} | "
            f"Inicio: {proyecto['fecha_inicio']} | "
            f"Estado: {proyecto['estado']}"
        )

def eliminar_proyecto_menu(bd: BaseDeDatos):
    proyectos = bd.listar_proyectos()

    if not proyectos:
        print(" No hay proyectos registrados.")
        return

    print("\nLista de Proyectos:")
    for numero, proyecto in enumerate(proyectos, start=1):
        print(
            f"{numero}. {proyecto['nombre']} | "
            f"Ciudad: {proyecto['ciudad']} | "
            f"Inicio: {proyecto['fecha_inicio']} | "
            f"Estado: {proyecto['estado']}"
        )

    try:
        numero = int(input("\n¿Qué número de proyecto deseas eliminar?: "))

        if numero < 1 or numero > len(proyectos):
            print(" Opción no válida.")
            return

    except ValueError:
        print(" Opción no válida. Debes ingresar un número.")
        return

    proyecto = proyectos[numero - 1]

    confirmacion = input(
        f"¿Estás seguro de eliminar el proyecto "
        f"'{proyecto['nombre']}'? (s/n): "
    ).strip().lower()

    if confirmacion == "s":
        bd.eliminar_proyecto(proyecto["id"])
    elif confirmacion == "n":
        print(" Eliminación cancelada.")
    else:
        print(" Opción no válida. Debes ingresar s o n.")
        

def menu_proyectos(bd: BaseDeDatos):
    acciones = {
        "1": agregar_proyecto_menu,
        "2": listar_proyectos_menu,
        "3": eliminar_proyecto_menu  # Esta función se puede implementar si se desea
    }

    while True:
        print("\n--- Gestión de Proyectos ---")
        print("1. Crear proyecto")
        print("2. Listar proyectos")
        print("3. Eliminar proyecto")
        print("4. Volver al menú principal")

        opcion = input(TEXTO_OPCION).strip()

        if opcion == "4":
            break

        accion = acciones.get(opcion)

        if accion:
            accion(bd)
        else:
            print(OPCION_NO_VALIDA)


def menu_principal(bd: BaseDeDatos):
    acciones = {
        "1": lambda: menu_empleados(bd),
        "2": lambda: menu_proyectos(bd),
        "3": menu_servicios_externos
    }

    while True:
        print("\n" + "=" * 40)
        print("   ECOTECH SOLUTIONS — SISTEMA DE GESTIÓN")
        print("=" * 40)
        print("1. Gestión de Empleados")
        print("2. Gestión de Proyectos")
        print("3. Consultas Externas (Clima y Monedas)")
        print("4. Cerrar sesión y salir")
        print("=" * 40)

        opcion = input(
            "Selecciona una opción [1-4]: "
        ).strip()

        if opcion == "4":
            print(" Sesión cerrada. ¡Hasta luego!")
            break

        accion = acciones.get(opcion)

        if accion:
            accion()
        else:
            print(f" {OPCION_NO_VALIDA} Elige entre 1 y 4.")




if __name__ == "__main__":
    print("EcoTech Solutions — Sistema de Gestión")
    print("Cargando sistema...")
    try:
        bd = BaseDeDatos()
        if iniciar_sesion(bd):
            menu_principal(bd)
    except Exception as e:
        print(f"\n Error crítico del sistema: {e}")
    finally:
        if 'bd' in locals():
            bd.cerrar()
        print("Sistema finalizado.")
