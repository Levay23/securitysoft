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
def generate_key(note: str = None, bot_name: str = "Generic Bot", duration_days: int = 0, db: Session = Depends(get_db)):
    """
    duration_days: 0 = Indefinida, 30 = 1 Mes, etc.
    """
    new_key = str(uuid.uuid4()).upper()
    
    expires_at = None
    if duration_days > 0:
        expires_at = datetime.datetime.utcnow() + datetime.timedelta(days=duration_days)

    license_entry = models.License(key=new_key, note=note, bot_name=bot_name, expires_at=expires_at)
    db.add(license_entry)
    db.commit()
    db.refresh(license_entry)
    return {"status": "success", "key": new_key}

@app.post("/activate")
def activate_license(key: str, hwid: str, db: Session = Depends(get_db)):
    print(f"[DEBUG] Intento de activar Key: {key} para HWID: {hwid}")
    license_entry = db.query(models.License).filter(models.License.key == key).first()
    
    if not license_entry:
        raise HTTPException(status_code=404, detail="Key no encontrada")
    
    if license_entry.is_active is False:
        raise HTTPException(status_code=403, detail="Key desactivada")
        
    if license_entry.hwid and license_entry.hwid != hwid:
         raise HTTPException(status_code=403, detail="Key ya usada en otra maquina")

    # Verificar expiración
    if license_entry.expires_at and license_entry.expires_at < datetime.datetime.utcnow():
        raise HTTPException(status_code=403, detail="Key expirada")

    license_entry.hwid = hwid
    license_entry.activated_at = datetime.datetime.utcnow()
    db.commit()
    
    print(f"[DEBUG] Key {key} vinculada exitosamente a {hwid}")
    return {"status": "success", "message": "Clave activada"}

@app.get("/validate")
def validate_license(key: str, hwid: str, db: Session = Depends(get_db)):
    """Verifica la clave y la vincula de forma automática si es nueva (Auto-Activation)."""
    # print(f"[DEBUG] Validando Key: {key} ...") # Reduce spam log
    license_entry = db.query(models.License).filter(models.License.key == key).first()
    
    if not license_entry:
        raise HTTPException(status_code=403, detail={"reason": "invalid_key", "message": "Clave inexistente"})
    
    if not license_entry.is_active:
        raise HTTPException(status_code=403, detail={"reason": "key_disabled", "message": "Clave bloqueada comercialmente"})

    # Check Expiration
    if license_entry.expires_at and license_entry.expires_at < datetime.datetime.utcnow():
        raise HTTPException(status_code=403, detail={"reason": "expired", "message": "Tu licencia ha expirado. Renueva tu suscripción."})

    # AUTO-ACTIVACIÓN
    if license_entry.hwid is None:
        print(f"[DEBUG] Activando Key {key} por primera vez para HWID: {hwid}")
        license_entry.hwid = hwid
        license_entry.activated_at = datetime.datetime.utcnow()
        db.commit()
        return {"valid": True, "message": "Clave activada y vinculada exitosamente"}

    if license_entry.hwid != hwid:
        raise HTTPException(status_code=403, detail={"reason": "hwid_mismatch", "message": "Esta clave pertenece a otro equipo"})

    return {"valid": True, "message": "Acceso concedido"}

@app.get("/licenses/list")
def list_licenses(db: Session = Depends(get_db)):
    return db.query(models.License).order_by(models.License.created_at.desc()).all()

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
                --warning: #f59e0b;
                --input-bg: #334155;
            }
            body { font-family: 'Inter', sans-serif; background-color: var(--bg); color: var(--text); margin: 0; padding: 40px; display: flex; flex-direction: column; align-items: center; }
            .container { max-width: 1200px; width: 100%; }
            header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 40px; }
            h1 { font-size: 2rem; margin: 0; }
            
            button { background: var(--primary); color: white; border: none; padding: 10px 20px; border-radius: 8px; font-weight: 600; cursor: pointer; transition: opacity 0.2s; }
            button:hover { opacity: 0.9; }
            
            .card { background: var(--card); border-radius: 12px; padding: 24px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); overflow-x: auto; }
            
            table { width: 100%; border-collapse: collapse; margin-top: 20px; min-width: 800px; }
            th { text-align: left; color: var(--text-muted); font-weight: 400; padding: 12px; border-bottom: 1px solid #334155; }
            td { padding: 16px 12px; border-bottom: 1px solid #334155; vertical-align: middle; }
            
            .key-cell { font-family: monospace; color: var(--primary); font-size: 0.9rem; }
            .status-active { color: var(--success); font-weight: bold; }
            .status-inactive { color: var(--danger); font-weight: bold; }
            .status-expired { color: var(--warning); font-weight: bold; }
            
            .action-btn { padding: 6px 12px; font-size: 0.8rem; background: transparent; border: 1px solid var(--text-muted); color: var(--text-muted); margin-right: 5px; }
            .action-btn:hover { border-color: var(--text); color: var(--text); }
            .btn-delete { color: var(--danger); border-color: var(--danger); }
            .btn-delete:hover { background: var(--danger); color: white; }

            /* Modal Styles */
            .modal { display: none; position: fixed; z-index: 1000; left: 0; top: 0; width: 100%; height: 100%; background-color: rgba(0,0,0,0.7); align-items: center; justify-content: center; }
            .modal-content { background-color: var(--card); padding: 30px; border-radius: 12px; width: 400px; box-shadow: 0 20px 25px -5px rgba(0,0,0,0.3); border: 1px solid #334155; }
            .form-group { margin-bottom: 15px; }
            label { display: block; margin-bottom: 5px; color: var(--text-muted); font-size: 0.9rem; }
            input, select { width: 100%; padding: 10px; background: var(--input-bg); border: 1px solid #475569; border-radius: 6px; color: white; box-sizing: border-box; }
            input:focus, select:focus { outline: none; border-color: var(--primary); }
            .form-actions { display: flex; justify-content: flex-end; gap: 10px; margin-top: 20px; }
            .btn-cancel { background: transparent; border: 1px solid var(--text-muted); }
            .expired-tag { font-size: 0.75rem; background: rgba(245, 158, 11, 0.2); color: var(--warning); padding: 2px 6px; border-radius: 4px; border: 1px solid rgba(245, 158, 11, 0.5); }
        </style>
    </head>
    <body>
        <div class="container">
            <header>
                <h1>AuthKey <span style="font-weight: 400; color: var(--text-muted)">Panel</span></h1>
                <div>
                    <span id="refreshStatus" style="font-size: 0.8rem; color: var(--text-muted); margin-right: 15px;">Live</span>
                    <button onclick="openModal()">+ Nueva Licencia</button>
                </div>
            </header>
            
            <div class="card">
                <table>
                    <thead>
                        <tr>
                            <th>ID</th>
                            <th>Bot</th>
                            <th>Licencia (Key)</th>
                            <th>Cliente</th>
                            <th>HWID</th>
                            <th>Expiración</th>
                            <th>Estado</th>
                            <th>Acciones</th>
                        </tr>
                    </thead>
                    <tbody id="licenseTable"></tbody>
                </table>
            </div>
        </div>

        <!-- NEW KEY MODAL -->
        <div id="newKeyModal" class="modal">
            <div class="modal-content">
                <h2 style="margin-top:0">Crear Nueva Licencia</h2>
                
                <div class="form-group">
                    <label>Nombre del Cliente / Nota</label>
                    <input type="text" id="clientName" placeholder="Ej. Juan Pérez">
                </div>
                
                <div class="form-group">
                    <label>Bot / Producto</label>
                    <input type="text" id="botName" value="Trading Bot VIP" placeholder="Nombre del producto">
                </div>
                
                <div class="form-group">
                    <label>Duración</label>
                    <select id="duration">
                        <option value="30">1 Mes</option>
                        <option value="90">3 Meses</option>
                        <option value="180">6 Meses</option>
                        <option value="365">1 Año</option>
                        <option value="0" selected>De por vida (Indefinido)</option>
                    </select>
                </div>

                <div class="form-actions">
                    <button class="btn-cancel" onclick="closeModal()">Cancelar</button>
                    <button onclick="createKey()">Generar Key</button>
                </div>
            </div>
        </div>

        <script>
            function openModal() { document.getElementById('newKeyModal').style.display = 'flex'; }
            function closeModal() { document.getElementById('newKeyModal').style.display = 'none'; }

            async function loadLicenses() {
                try {
                    const res = await fetch('/licenses/list');
                    const licenses = await res.json();
                    const tbody = document.getElementById('licenseTable');
                    tbody.innerHTML = '';
                    
                    licenses.forEach(lic => {
                        let expirationText = "Indefinido";
                        let isExpired = false;
                        
                        if (lic.expires_at) {
                            const expDate = new Date(lic.expires_at);
                            const now = new Date();
                            expirationText = expDate.toLocaleDateString();
                            if (now > expDate) {
                                isExpired = true;
                                expirationText += " <br><span class='expired-tag'>VENCIDA</span>";
                            }
                        }

                        let statusHtml = "";
                        if (isExpired) {
                            statusHtml = "<span class='status-expired'>EXPIRADA</span>";
                        } else {
                            statusHtml = lic.is_active ? "<span class='status-active'>ACTIVA</span>" : "<span class='status-inactive'>BLOQUEADA</span>";
                        }

                        const tr = document.createElement('tr');
                        tr.innerHTML = `
                            <td>${lic.id}</td>
                            <td><strong>${lic.bot_name || 'Generic'}</strong></td>
                            <td class="key-cell" title="${lic.key}">${lic.key.substring(0,25)}...</td>
                            <td>${lic.note || '-'}</td>
                            <td>${lic.hwid ? '<span style="font-family:monospace; font-size:0.8rem">'+lic.hwid+'</span>' : '<em style="color:#64748b;">Esperando...</em>'}</td>
                            <td style="font-size:0.9rem">${expirationText}</td>
                            <td>${statusHtml}</td>
                            <td>
                                <button class="action-btn" onclick="toggleStatus(${lic.id})">
                                    ${lic.is_active ? 'Bloquear' : 'Activar'}
                                </button>
                                <button class="action-btn btn-delete" onclick="deleteLicense(${lic.id})">X</button>
                            </td>
                        `;
                        tbody.appendChild(tr);
                    });
                    document.getElementById('refreshStatus').innerText = 'Actualizado: ' + new Date().toLocaleTimeString();
                } catch (e) {
                    console.error(e);
                    document.getElementById('refreshStatus').innerText = 'Error actualizando';
                }
            }

            async function createKey() {
                const note = document.getElementById('clientName').value;
                const botName = document.getElementById('botName').value;
                const duration = document.getElementById('duration').value;
                
                if (!note) return alert("Por favor ingresa un nombre de cliente");

                await fetch(`/generate?note=${encodeURIComponent(note)}&bot_name=${encodeURIComponent(botName)}&duration_days=${duration}`, { method: 'POST' });
                closeModal();
                loadLicenses();
            }

            async function toggleStatus(id) {
                await fetch(`/licenses/toggle/${id}`, { method: 'POST' });
                loadLicenses();
            }

            async function deleteLicense(id) {
                if (!confirm("¿Eliminar esta licencia permanentemente?")) return;
                await fetch(`/licenses/delete/${id}`, { method: 'POST' });
                loadLicenses();
            }

            loadLicenses();
            setInterval(loadLicenses, 5000);
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
