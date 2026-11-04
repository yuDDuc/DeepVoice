from datetime import datetime, timezone
from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from .config import get_settings
from .models import ModelRegistry
from .telemetry import Timer
from .security import hash_password, verify_password, create_token, decode_token
from .db import collection, ensure_indexes
from .payment import create_invoice

settings=get_settings(); registry=ModelRegistry(settings)
app=FastAPI(title=settings.app_name,version='0.2.0')
app.add_middleware(CORSMiddleware,allow_origins=['*'],allow_methods=['*'],allow_headers=['*'])
class Credentials(BaseModel): email: EmailStr; password: str
class InvoiceRequest(BaseModel): amount: int
def current_user(authorization: str|None=Header(default=None)):
    if not authorization or not authorization.startswith('Bearer '): raise HTTPException(401,'Bearer token required')
    try: return decode_token(authorization[7:],settings.jwt_secret)
    except Exception: raise HTTPException(401,'Invalid or expired token')

def inference_user(authorization: str|None=Header(default=None)):
    if not settings.auth_required:
        return {'sub': 'local-user', 'role': 'user'}
    return current_user(authorization)
@app.on_event('startup')
def startup():
    try: ensure_indexes()
    except Exception: pass
@app.get('/health')
def health(): return {'status':'ok','environment':settings.environment}
@app.get('/ready')
def ready():
    try: collection('health').database.client.admin.command('ping'); mongo='ok'
    except Exception: mongo='unavailable'
    return {'status':'ready','mongo':mongo,'models':[settings.asr_model_name,settings.mt_model_name]}
@app.post('/api/v1/auth/register')
def register(data: Credentials):
    if len(data.password)<8: raise HTTPException(400,'Password must contain at least 8 characters')
    doc={'email':data.email.lower(),'password_hash':hash_password(data.password),'role':'user','created_at':datetime.now(timezone.utc)}
    try: result=collection('users').insert_one(doc)
    except Exception as exc:
        if 'duplicate' in str(exc).lower(): raise HTTPException(409,'Email already exists')
        raise HTTPException(503,'Database unavailable')
    return {'access_token':create_token(str(result.inserted_id),'user',settings.jwt_secret),'token_type':'bearer'}
@app.post('/api/v1/auth/login')
def login(data: Credentials):
    user=collection('users').find_one({'email':data.email.lower()})
    if not user or not verify_password(data.password,user['password_hash']): raise HTTPException(401,'Invalid credentials')
    return {'access_token':create_token(str(user['_id']),user.get('role','user'),settings.jwt_secret),'token_type':'bearer'}
@app.get('/api/v1/auth/me')
def me(user=Depends(current_user)): return user
@app.get('/api/v1/models')
def models(): return {'asr':{'name':settings.asr_model_name,'model_id':settings.asr_model_id,'provider':settings.asr_provider,'device':registry.asr.device if hasattr(registry.asr,'device') else settings.asr_device,'language':settings.asr_language},'translation':{'name':settings.mt_model_name,'model_id':settings.mt_model_id,'provider':settings.mt_provider,'device':registry.mt.device if hasattr(registry.mt,'device') else settings.mt_device,'source_language':settings.mt_source_language,'target_language':settings.mt_target_language}}
@app.post('/api/v1/inference')
async def inference(file: UploadFile=File(...),user=Depends(inference_user)):
    audio=await file.read()
    if not audio: raise HTTPException(400,'Audio file is empty')
    if len(audio)>settings.max_audio_mb*1024*1024: raise HTTPException(413,'Audio file is too large')
    with Timer() as timer: asr,mt=registry.infer(audio)
    result={'user_id':user['sub'],'transcript':asr.text,'translation':mt.text,'latency_ms':timer.elapsed_ms,'asr_model':asr.name,'mt_model':mt.name,'created_at':datetime.now(timezone.utc)}
    try: collection('inference_requests').insert_one(result)
    except Exception: pass
    return {'transcript':asr.text,'translation':mt.text,'metrics':{'latency_ms':timer.elapsed_ms,'before':timer.before,'after':timer.after},'models':{'asr':{'name':asr.name,'provider':asr.provider,'device':asr.device},'translation':{'name':mt.name,'provider':mt.provider,'device':mt.device}}}
@app.get('/api/v1/inference/history')
def history(user=Depends(current_user)): return list(collection('inference_requests').find({'user_id':user['sub']},{'_id':0}).sort('created_at',-1).limit(50))
@app.post('/api/v1/payments/invoices')
def invoice(data: InvoiceRequest,user=Depends(current_user)):
    if data.amount<=0: raise HTTPException(400,'Amount must be positive')
    doc=create_invoice(user['sub'],data.amount); doc['qr_png_base64']=None
    try: collection('invoices').insert_one(doc)
    except Exception: raise HTTPException(503,'Database unavailable')
    return {k:v for k,v in doc.items() if k!='_id'}
@app.get('/api/v1/payments/invoices')
def invoices(user=Depends(current_user)): return list(collection('invoices').find({'user_id':user['sub']},{'_id':0,'qr_png_base64':0}).sort('created_at',-1).limit(50))
