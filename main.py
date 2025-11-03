from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from plutocontrol import pluto  
from fastapi.middleware.cors import CORSMiddleware

drone = pluto()
app = FastAPI()
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/connect")
def connect():
    drone.connect()
    return {"status": "connected"}

@app.post("/disconnect")
def connect():
    drone.disconnect()
    return {"status": "disconnected"}

@app.post("/arm")
def arm():
    drone.arm()
    return {"status": "armed"}

@app.post("/disarm")
def arm():
    drone.disarm()
    return {"status": "disarmed"}

@app.post("/takeoff")
def takeoff():
    drone.take_off()
    return {"status": "taking off"}

@app.post("/land")
def land():
    drone.land()
    return {"status": "landing"}
