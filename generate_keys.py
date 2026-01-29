import requests

# URL del servidor local
SERVER_URL = "http://localhost:8000"

def generate(note):
    try:
        response = requests.post(f"{SERVER_URL}/generate", params={"note": note})
        if response.status_code == 200:
            data = response.json()
            print(f"[+] Clave generada para '{note}': {data['key']}")
        else:
            print(f"[-] Error al generar clave: {response.text}")
    except Exception as e:
        print(f"[-] Error de conexión: {e}. ¿Está corriendo el servidor?")

if __name__ == "__main__":
    print("--- GENERADOR DE CLAVES DE SEGURIDAD ---")
    cliente = input("Nombre del cliente o nota: ")
    generate(cliente)
