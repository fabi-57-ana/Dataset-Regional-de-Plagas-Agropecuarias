# Dataset Regional de Plagas Agropecuarias (Plataforma Plagas)

Un sistema integral diseñado para la **captura, categorización, validación agronómica y exportación** de imágenes de plagas agrícolas en cultivos regionales (extensivos e intensivos). 

El objetivo principal de esta plataforma es recolectar y curar un dataset limpio y verificado por expertos para el posterior entrenamiento de modelos de Inteligencia Artificial aplicados al agro.

---

## Arquitectura del Sistema

* **Backend:** FastAPI (Python 3) - API RESTful asíncrona.
* **Base de Datos:** Supabase (PostgreSQL con soporte RLS).
* **Almacenamiento de Multimedia:** Cloudinary (para optimización y hosting de imágenes).
* **Autenticación & Seguridad:** JWT (JSON Web Tokens) con cifrado de contraseñas mediante Passlib/Bcrypt.
* **Despliegue / Frontend Provisorio:** Cliente web interactivo (HTML5/JavaScript) para pruebas de integración previa al desarrollo en React + Vite.

---

## Estructura del Proyecto

```text
Dataset_Regional_de_Plagas_Agropecuarias/
├── app/
│   ├── config.py         # Configuración de variables de entorno (Pydantic Settings)
│   ├── database.py       # Inicialización de clientes Supabase y Cloudinary
│   ├── dependencies.py   # Inyección de dependencias (Verificación de Token JWT y Roles)
│   ├── schemas.py        # Modelos y esquemas de validación Pydantic
│   └── security.py       # Utilidades de encriptación (Bcrypt) y generación de Tokens
├── frontend/
│   └── index.html        # Panel interactivo de pruebas de la API (Vanilla JS)
├── main.py               # Punto de entrada de FastAPI y definición de Endpoints
├── requirements.txt      # Archivo de dependencias del proyecto
└── README.md             # Documentación del repositorio
```
git clone https://github.com/fabi-57-ana/Dataset-Regional-de-Plagas-Agropecuarias.git

cd Dataset_Regional_de_Plagas_Agropecuarias

# Windows
python -m venv venv

.\venv\Scripts\activate

# Linux/macOS
python3 -m venv venv

source venv/bin/activate

pip install -r requirements.txt

APP_NAME="Dataset Regional de Plagas Agropecuarias"

DEBUG=True

# Configuración Supabase
SUPABASE_URL="[https://tu-proyecto.supabase.co](https://tu-proyecto.supabase.co)"

SUPABASE_KEY="tu-anon-key-de-supabase"

# Configuración Cloudinary
CLOUDINARY_CLOUD_NAME="tu-cloud-name"

CLOUDINARY_API_KEY="tu-api-key"

CLOUDINARY_API_SECRET="tu-api-secret"

# Configuración JWT Seguridad
SECRET_KEY="tu_clave_secreta_super_segura"

ALGORITHM="HS256"

ACCESS_TOKEN_EXPIRE_MINUTES=480

uvicorn main:app --reload


