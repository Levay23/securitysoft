from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
import datetime
import webbrowser
from threading import Timer
import sys
import os

# Asegurar que el servidor pueda encontrar models.py sin importar desde dónde se ejecute
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import models
import uuid

app = FastAPI(title="AuthKey System Dashboard")

# Inicializar base de datos
models.init_db()

# Dependencia para la sesión de DB
def get_db():
    db = models.SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- API ENDPOINTS ---

@app.post("/generate")
def generate_key(note: str = None, db: Session = Depends(get_db)):
    new_key = str(uuid.uuid4()).upper()
    license_entry = models.License(key=new_key, note=note)
    db.add(license_entry)
    db.commit()
    db.refresh(license_entry)
    return {"status": "success", "key": new_key}

@app.post("/activate")
def activate_license(key: str, hwid: str, db: Session = Depends(get_db)):
    """Vincula una clave a un HWID específico."""
    print(f"[DEBUG] Intentando activar Key: {key} con HWID: {hwid}")
    license_entry = db.query(models.License).filter(models.License.key == key).first()
    
    if not license_entry:
        print(f"[DEBUG] Error: Key {key} no encontrada.")
        raise HTTPException(status_code=404, detail="Key no encontrada")
    
    if license_entry.hwid:
        print(f"[DEBUG] Key ya tiene HWID: {license_entry.hwid}")
        if license_entry.hwid == hwid:
            return {"status": "already_activated", "message": "Clave ya vinculada"}
        else:
            raise HTTPException(status_code=403, detail="Esta clave ya está en uso")

    # Vincular HWID
    license_entry.hwid = hwid
    license_entry.activated_at = datetime.datetime.utcnow()
    db.commit()
    print(f"[DEBUG] Key {key} vinculada exitosamente a {hwid}")
    return {"status": "success", "message": "Clave activada"}

@app.get("/validate")
def validate_license(key: str, hwid: str, db: Session = Depends(get_db)):
    """Verifica la clave y la vincula de forma automática si es nueva (Auto-Activation)."""
    print(f"[DEBUG] Validando Key: {key} para HWID: {hwid}")
    license_entry = db.query(models.License).filter(models.License.key == key).first()
    
    if not license_entry:
        print(f"[DEBUG] Key no existe")
        raise HTTPException(status_code=403, detail={"reason": "invalid_key", "message": "Clave inexistente"})
    
    if not license_entry.is_active:
        print(f"[DEBUG] Key desactivada")
        raise HTTPException(status_code=403, detail={"reason": "key_disabled", "message": "Clave bloqueada comercialmente"})

    # AUTO-ACTIVACIÓN: Si es el primer uso, la vinculamos directamente
    if license_entry.hwid is None:
        print(f"[DEBUG] Activando Key {key} por primera vez para HWID: {hwid}")
        license_entry.hwid = hwid
        license_entry.activated_at = datetime.datetime.utcnow()
        db.commit()
        return {"valid": True, "message": "Clave activada y vinculada exitosamente"}

    # Si ya tiene HWID, comprobamos que sea el mismo
    if license_entry.hwid != hwid:
        print(f"[DEBUG] HWID MISMATCH: DB={license_entry.hwid}, Recibido={hwid}")
        raise HTTPException(status_code=403, detail={"reason": "hwid_mismatch", "message": "Esta clave pertenece a otro equipo"})

    print(f"[DEBUG] Acceso concedido para HWID: {hwid}")
    return {"valid": True, "message": "Acceso concedido"}

@app.get("/licenses/list")
def list_licenses(db: Session = Depends(get_db)):
    return db.query(models.License).all()

@app.post("/licenses/toggle/{license_id}")
def toggle_license(license_id: int, db: Session = Depends(get_db)):
    lic = db.query(models.License).filter(models.License.id == license_id).first()
    if lic:
        lic.is_active = not lic.is_active
        db.commit()
        return {"status": "success", "new_state": lic.is_active}
    return {"status": "error"}

@app.post("/licenses/delete/{license_id}")
def delete_license(license_id: int, db: Session = Depends(get_db)):
    lic = db.query(models.License).filter(models.License.id == license_id).first()
    if lic:
        db.delete(lic)
        db.commit()
        return {"status": "success"}
    return {"status": "error"}

# --- DASHBOARD UI ---

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    html_content = """
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>AuthKey - Panel de Control</title>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
        <style>
            :root {
                --primary: #6366f1;
                --bg: #0f172a;
                --card: #1e293b;
                --text: #f8fafc;
                --text-muted: #94a3b8;
                --success: #22c55e;
                --danger: #ef4444;
            }
            body {
                font-family: 'Inter', sans-serif;
                background-color: var(--bg);
                color: var(--text);
                margin: 0;
                padding: 40px;
                display: flex;
                flex-direction: column;
                align-items: center;
            }
            .container {
                max-width: 1000px;
                width: 100%;
            }
            header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 40px;
            }
            h1 { font-size: 2rem; margin: 0; }
            button {
                background: var(--primary);
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 8px;
                font-weight: 600;
                cursor: pointer;
                transition: opacity 0.2s;
            }
            button:hover { opacity: 0.9; }
            .card {
                background: var(--card);
                border-radius: 12px;
                padding: 24px;
                box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);
            }
            table {
                width: 100%;
                border-collapse: collapse;
                margin-top: 20px;
            }
            th {
                text-align: left;
                color: var(--text-muted);
                font-weight: 400;
                padding: 12px;
                border-bottom: 1px solid #334155;
            }
            td {
                padding: 16px 12px;
                border-bottom: 1px solid #334155;
            }
            .key-cell { font-family: monospace; color: var(--primary); }
            .status-active { color: var(--success); font-weight: bold; }
            .status-inactive { color: var(--danger); font-weight: bold; }
            .action-btn {
                padding: 6px 12px;
                font-size: 0.8rem;
                background: transparent;
                border: 1px solid var(--text-muted);
                color: var(--text-muted);
                margin-right: 5px;
            }
            .action-btn:hover { border-color: var(--text); color: var(--text); }
            .btn-delete { color: var(--danger); border-color: var(--danger); }
            .btn-delete:hover { background: var(--danger); color: white; }
        </style>
    </head>
    <body>
        <div class="container">
            <header>
                <h1>AuthKey <span style="font-weight: 400; color: var(--text-muted)">Security</span></h1>
                <div>
                    <span id="refreshStatus" style="font-size: 0.8rem; color: var(--text-muted); margin-right: 15px;">Actualizando...</span>
                    <button onclick="generateKey()">+ Nueva Clave</button>
                </div>
            </header>
            <div class="card">
                <table>
                    <thead>
                        <tr>
                            <th>ID</th>
                            <th>Clave de Licencia</th>
                            <th>Nota / Cliente</th>
                            <th>HWID Vinculado</th>
                            <th>Estado</th>
                            <th>Acciones</th>
                        </tr>
                    </thead>
                    <tbody id="licenseTable">
                        <!-- Se llena con JS -->
                    </tbody>
                </table>
            </div>
        </div>

        <script>
            async function loadLicenses() {
                try {
                    const res = await fetch('/licenses/list');
                    const licenses = await res.json();
                    const tbody = document.getElementById('licenseTable');
                    tbody.innerHTML = '';
                    
                    licenses.forEach(lic => {
                        const tr = document.createElement('tr');
                        tr.innerHTML = `
                            <td>${lic.id}</td>
                            <td class="key-cell">${lic.key}</td>
                            <td>${lic.note || '-'}</td>
                            <td>${lic.hwid ? '<span style="color:var(--text); font-family:monospace;">'+lic.hwid+'</span>' : '<em style="color:orange;">Esperando activación</em>'}</td>
                            <td class="${lic.is_active ? 'status-active' : 'status-inactive'}">${lic.is_active ? 'ACTIVA' : 'BLOQUEADA'}</td>
                            <td>
                                <button class="action-btn" onclick="toggleStatus(${lic.id})">
                                    ${lic.is_active ? 'Desactivar' : 'Activar'}
                                </button>
                                <button class="action-btn btn-delete" onclick="deleteLicense(${lic.id})">Eliminar</button>
                            </td>
                        `;
                        tbody.appendChild(tr);
                    });
                    document.getElementById('refreshStatus').innerText = 'Actualizado: ' + new Date().toLocaleTimeString();
                } catch (e) {
                    document.getElementById('refreshStatus').innerText = 'Error actualizando';
                }
            }

            async function generateKey() {
                const note = prompt("Nombre del cliente para esta clave:");
                if (note === null) return;
                await fetch(`/generate?note=${encodeURIComponent(note)}`, { method: 'POST' });
                loadLicenses();
            }

            async function toggleStatus(id) {
                await fetch(`/licenses/toggle/${id}`, { method: 'POST' });
                loadLicenses();
            }

            async function deleteLicense(id) {
                if (!confirm("¿Seguro que quieres eliminar esta licencia permanentemente?")) return;
                await fetch(`/licenses/delete/${id}`, { method: 'POST' });
                loadLicenses();
            }

            // Carga inicial
            loadLicenses();
            // Auto refresco cada 3 segundos
            setInterval(loadLicenses, 3000);
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

def open_browser():
    webbrowser.open("http://localhost:8000")

if __name__ == "__main__":
    import uvicorn
    # Timer para abrir el navegador después de 1.5 segundos
    Timer(1.5, open_browser).start()
    try:
        uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
    except KeyboardInterrupt:
        print("\n[!] Servidor detenido por el usuario.")
        sys.exit(0)
