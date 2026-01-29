# Sistema de Seguridad para Bots (Guía de Uso)

Este sistema permite proteger tus bots vinculando cada licencia al hardware (HWID) del comprador.

## 1. Instalación
Asegúrate de tener instaladas las dependencias:
```bash
pip install -r requirements.txt
```

## 2. Iniciar el Servidor de Licencias
El servidor debe estar corriendo para validar las claves. Ábrelo en una terminal:
```bash
python server/main.py
```
*Esto creará un archivo `licenses.db` donde se guardará todo.*

## 3. Generar una Clave para un Cliente
Usa el script generador:
```bash
python generate_keys.py
```
Ingresa el nombre del cliente y te dará una clave (ejemplo: `550E8400-E29B-41D4-A716-446655440000`).

## 4. Proteger tu Bot
Para cada bot que hagas, debes importar el módulo de seguridad al inicio.
Mira el ejemplo en `client/security.py`. Básicamente es:

```python
from client.security import protect_bot

# Al inicio de tu código
MI_CLAVE = "CLAVE-QUE-LE-VENDISTE" 
protect_bot(MI_CLAVE)

# ... El resto de tu bot aquí ...
```

## 5. Próximos Pasos (Seguridad Avanzada)
Para que no puedan modificar tu código y saltarse la seguridad:
1. **Obfuscación**: Usar herramientas como `PyArmor`.
2. **Compilación**: Convertir el `.py` en `.exe`.
