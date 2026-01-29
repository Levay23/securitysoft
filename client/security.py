import subprocess
import requests
import sys

# URL del servidor local (cambiar a la IP del VPS en producción)
SERVER_URL = "https://securitysoft.onrender.com"

def get_hwid():
    """Genera un ID único para la PC basado en el Serial Number del disco principal."""
    try:
        # Usamos wmic para obtener el serial del disco de Windows
        cmd = "wmic diskdrive get serialnumber"
        output = subprocess.check_output(cmd, shell=True).decode().split()
        # Retornamos el primer serial que encontremos después del encabezado "SerialNumber"
        for item in output:
            if item.strip() and item != "SerialNumber":
                return item.strip()
    except Exception as e:
        print(f"Error generando HWID: {e}")
        return "UNKNOWN_HWID"

def check_license(license_key):
    """Valida la licencia con el servidor de forma estricta."""
    hwid = get_hwid()
    
    try:
        response = requests.get(f"{SERVER_URL}/validate", params={"key": license_key, "hwid": hwid}, timeout=10)
        
        # Si el status es 200, la licencia es válida o se acaba de auto-activar
        if response.status_code == 200:
            data = response.json()
            print(f"[+] {data.get('message')}")
            print(f"[+] HWID Vinculado: {hwid}")
            return True
        
        # Si el status NO es 200 (ej: 403), la licencia es inválida o está bloqueada
        if response.status_code == 403:
            error_data = response.json().get("detail", {})
            reason = error_data.get("reason")
            message = error_data.get("message", "Acceso denegado")
            
            if reason == "key_disabled":
                print(f"[-] LICENCIA BLOQUEADA: {message}")
                print("[-] Tu acceso ha sido suspendido. Contacta a SOPORTE.")
            elif reason == "expired":
                print(f"[-] LICENCIA VENCIDA: {message}")
                print("[-] Tu tiempo de suscripción ha terminado. Por favor renueva tu licencia.")
            elif reason == "hwid_mismatch":
                print(f"[-] ERROR DE HARDWARE: {message}")
                print("[-] Esta licencia no pertenece a este equipo.")
            else:
                print(f"[-] ERROR: {message}")
            return False

        print(f"[-] Error inesperado del servidor (Status {response.status_code})")
        return False

    except requests.exceptions.ConnectionError:
        print("[-] Error: No se pudo conectar con el servidor de licencias. Verifica tu internet.")
        return False
    except Exception as e:
        print(f"[-] Error inesperado en validación: {e}")
        return False

def protect_bot(license_key):
    """Función para llamar al inicio de tus bots."""
    if not check_license(license_key):
        print("[-] Acceso denegado. El programa se cerrará.")
        input("Presiona Enter para salir...")
        sys.exit()

# Ejemplo de uso (esto iría al inicio de tu bot real)
if __name__ == "__main__":
    print("--- INICIANDO BOT PROTEGIDO ---")
    MI_CLAVE = input("Ingresa tu clave de licencia: ")
    protect_bot(MI_CLAVE)
    
    # Si pasa de aquí, el bot funciona normalmente
    print("\n[!] EL BOT ESTÁ CORRIENDO... (Tu código principal iría aquí)")
