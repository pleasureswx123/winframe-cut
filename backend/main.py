from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from .models import Project, OptimizeRequest
from .geometry import calculate, GeometryError
from .sample import sample_project
from .optimizer import optimize
from .glass_optimizer import optimize_glass
from . import storage

app=FastAPI(title='窗序 · 精密下料',version='1.0.0')


@app.exception_handler(GeometryError)
async def geometry_error(request, exc):
    return JSONResponse(status_code=422,content={'detail':str(exc)})


@app.get('/api/health')
def health():return {'status':'ok'}


@app.get('/api/sample')
def sample():return sample_project()


@app.post('/api/calculate')
def calculation(project: Project):return calculate(project)


@app.post('/api/optimize')
def optimization(request: OptimizeRequest):return optimize(request)


@app.post('/api/optimize-glass')
def glass_optimization(project: Project):return optimize_glass(project)


@app.post('/api/validate')
def validation(request: OptimizeRequest):
    calculate(request.project)
    return request


@app.get('/api/projects')
def projects():return storage.list_projects()


@app.post('/api/projects')
def save(project: Project):
    calculate(project)
    return storage.save_project(project)


@app.put('/api/projects/{id}')
def update(id: str, project: Project):
    if not storage.read_project(id):raise HTTPException(404,'项目不存在')
    calculate(project)
    return storage.save_project(project,id)


@app.get('/api/projects/{id}')
def read(id: str):
    project=storage.read_project(id)
    if project is None:raise HTTPException(404,'项目不存在')
    return project


dist=Path(__file__).resolve().parents[1]/'dist'
if dist.exists():app.mount('/',StaticFiles(directory=dist,html=True),name='frontend')
