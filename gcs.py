from fastapi import FastAPI, WebSocket, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import signal
import sys
from plutocontrol import pluto  # drone control class

app = FastAPI()
dr = pluto()

print("GCS running... press Ctrl+C to exit safely")

# Mount static and template dirs
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# CORS (allow frontend access)
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)

# Serve the frontend
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# --- Control Endpoints ---
@app.post("/connect")
def connect(): 
    dr.connect()
    return {"status": "connected"}

@app.post("/disconnect")
def disconnect(): 
    dr.disconnect()
    return {"status": "disconnected"}

@app.post("/arm")
def arm(): 
    dr.arm()
    return {"status": "armed"}

@app.post("/disarm")
def disarm(): 
    dr.disarm()
    return {"status": "disarmed"}

@app.post("/takeoff")
def takeoff(): 
    dr.take_off()
    return {"status": "takeoff"}

@app.post("/land")
def land(): 
    dr.land()
    return {"status": "landing"}

@app.post("/forward")
def forward(): 
    dr.forward()
    return {"status": "forward"}

@app.post("/backward")
def backward(): 
    dr.backward()
    return {"status": "backward"}

@app.post("/left")
def left(): 
    dr.left()
    return {"status": "left"}

@app.post("/right")
def right(): 
    dr.right()
    return {"status": "right"}

# --- Telemetry via WebSocket ---
@app.websocket("/ws/telemetry")
async def telemetry(websocket: WebSocket):
    await websocket.accept()
    while True:
        try:
            data = {
                "roll": dr.get_roll() or 0,
                "pitch": dr.get_pitch() or 0,
                "yaw": dr.get_yaw() or 0,
                "height": dr.get_height() or 0,
                "battery": dr.get_battery() or 0,
                "rc": dr.rc_values()
            }
            await websocket.send_json(data)
        except Exception as e:
            await websocket.send_json({"error": str(e)})
        await asyncio.sleep(0.5)

# --- Safe shutdown logic ---
def safe_shutdown():
    try:
        print("\n⚠️ Shutting down... landing, disarming, disconnecting")
        dr.land()
        asyncio.sleep(1)
        dr.disarm()
        asyncio.sleep(1)
        dr.disconnect()
        print("Drone safely shut down.")
    except Exception as e:
        print("Shutdown error:", e)

# --- FastAPI shutdown event ---
@app.on_event("shutdown")
def on_shutdown():
    safe_shutdown()

# --- Handle Ctrl+C or system kill ---
def handle_exit(sig, frame):
    safe_shutdown()
    sys.exit(0)

signal.signal(signal.SIGINT, handle_exit)   # Ctrl+C
signal.signal(signal.SIGTERM, handle_exit)  # kill / docker stop

# --- Optional: local run helper ---
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("web_gcs:app", host="0.0.0.0", port=8000, reload=True)
