from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from .models import Project, OptimizeRequest
from .geometry import calculate, GeometryError
from .sample import sample_project
from .optimizer import optimize
from .glass_optimizer import optimize_glass
from .auth import User, require_user, ensure_super_admin
from . import business_service
from .business_models import WindowInput
from .business_routes import router as business_router
from .auth_routes import router as auth_router
from .admin_routes import router as admin_router

@asynccontextmanager
async def lifespan(app):
    ensure_super_admin()
    yield


app=FastAPI(title='窗序 · 精密下料',version='1.0.0', lifespan=lifespan)
app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(business_router)


@app.exception_handler(GeometryError)
async def geometry_error(request, exc):
    return JSONResponse(status_code=422,content={'detail':str(exc)})


@app.get('/api/health')
def health():return {'status':'ok'}


@app.get('/api/sample')
def sample(user: User = Depends(require_user)):return sample_project()


@app.post('/api/calculate')
def calculation(project: Project, user: User = Depends(require_user)):return calculate(project)


@app.post('/api/optimize')
def optimization(request: OptimizeRequest, user: User = Depends(require_user)):return optimize(request)


@app.post('/api/optimize-glass')
def glass_optimization(project: Project, user: User = Depends(require_user)):return optimize_glass(project)


@app.post('/api/validate')
def validation(request: OptimizeRequest, user: User = Depends(require_user)):
    calculate(request.project)
    return request


@app.get('/api/projects')
def projects(user: User = Depends(require_user)):
    return business_service.list_records('windows', user.id)['items']


@app.post('/api/projects')
def save(project: Project, user: User = Depends(require_user)):
    raise HTTPException(409, '请在客户的房屋项目中创建窗型')


@app.put('/api/projects/{id}')
def update(id: str, project: Project, user: User = Depends(require_user)):
    current = business_service.get_record('windows', id, user.id)
    data = {key: current[key] for key in WindowInput.model_fields}
    data['project'] = project
    return business_service.save_record('windows', WindowInput(**data), user.id, id)


@app.get('/api/projects/{id}')
def read(id: str, user: User = Depends(require_user)):
    return business_service.get_record('windows', id, user.id)['project']


dist=Path(__file__).resolve().parents[1]/'dist'
if dist.exists():app.mount('/',StaticFiles(directory=dist,html=True),name='frontend')
