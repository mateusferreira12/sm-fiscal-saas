from dotenv import load_dotenv
from pathlib import Path
import os
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

import base64
import logging
import random
import httpx
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import FastAPI, APIRouter, Request, Response, HTTPException, Depends, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
from pydantic import BaseModel, EmailStr

import auth as auth_mod
import nfe_utils
from models import (User, Company, CompanyUpdate, Client, ClientCreate, Product,
                    ProductCreate, Invoice, InvoiceCreate, InvoiceItem, now_utc)

mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

app = FastAPI(title="NF-e System")

# CORS deve ser configurado antes de incluir os roteadores
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

api_router = APIRouter(prefix="/api")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============ Auth dependency ============
async def current_user(request: Request) -> dict:
    return await auth_mod.get_user_from_request(request, db)


# ============ Auth schemas ============
class RegisterIn(BaseModel):
    name: str
    email: EmailStr
    password: str


class LoginIn(BaseModel):
    email: EmailStr
    password: str


def _set_cookie(response: Response, token: str):
    response.set_cookie(key="access_token", value=token, httponly=True,
                        secure=True, samesite="none", max_age=604800, path="/")


@api_router.post("/auth/register")
async def register(payload: RegisterIn, response: Response):
    email = payload.email.lower()
    if await db.users.find_one({"email": email}):
        raise HTTPException(status_code=400, detail="E-mail ja cadastrado")
    doc = {"email": email, "name": payload.name,
           "password_hash": auth_mod.hash_password(payload.password),
           "role": "user", "created_at": now_utc()}
    res = await db.users.insert_one(doc)
    uid = str(res.inserted_id)
    token = auth_mod.create_access_token(uid, email)
    _set_cookie(response, token)
    return {"access_token": token,
            "user": {"id": uid, "email": email, "name": payload.name, "role": "user"}}


@api_router.post("/auth/login")
async def login(payload: LoginIn, response: Response):
    email = payload.email.lower()
    user = await db.users.find_one({"email": email})
    if not user or not auth_mod.verify_password(payload.password, user.get("password_hash", "")):
        raise HTTPException(status_code=401, detail="Credenciais invalidas")
    uid = str(user["_id"])
    token = auth_mod.create_access_token(uid, email)
    _set_cookie(response, token)
    return {"access_token": token,
            "user": {"id": uid, "email": email, "name": user.get("name", ""),
                     "role": user.get("role", "user")}}


# ============ Atalhos Diretos (Compatibilidade com chamadas sem /api) ============
@app.post("/register")
async def register_direct(payload: RegisterIn, response: Response):
    return await register(payload, response)

@app.post("/login")
async def login_direct(payload: LoginIn, response: Response):
    return await login(payload, response)


@api_router.post("/auth/logout")
async def logout(response: Response):
    response.delete_cookie("access_token", path="/")
    return {"ok": True}


@api_router.get("/auth/me")
async def me(user: dict = Depends(current_user)):
    return {"id": user["_id"], "email": user["email"], "name": user.get("name", ""),
            "role": user.get("role", "user")}


# ============ Company / Settings ============
async def _get_or_create_company(uid: str) -> dict:
    comp = await db.companies.find_one({"user_id": uid})
    if not comp:
        c = Company(user_id=uid)
        doc = c.to_mongo()
        res = await db.companies.insert_one(doc)
        comp = await db.companies.find_one({"_id": res.inserted_id})
    return comp


def _clean_company(comp: dict) -> dict:
    comp = dict(comp)
    comp["id"] = str(comp.pop("_id"))
    logo_data = comp.get("logo_data")
    if logo_data:
        fn = (comp.get("logo_filename") or "").lower()
        mime = "image/jpeg" if fn.endswith((".jpg", ".jpeg")) else "image/png"
        comp["logo_url"] = f"data:{mime};base64,{logo_data}"
    comp.pop("cert_data", None)
    comp.pop("cert_password", None)
    comp.pop("logo_data", None)
    return comp


@api_router.get("/company")
async def get_company(user: dict = Depends(current_user)):
    comp = await _get_or_create_company(user["_id"])
    return _clean_company(comp)


@api_router.put("/company")
async def update_company(payload: CompanyUpdate, user: dict = Depends(current_user)):
    await _get_or_create_company(user["_id"])
    upd = {k: v for k, v in payload.model_dump(exclude_none=True).items()}
    if "endereco" in upd and upd["endereco"] is not None:
        upd["endereco"] = payload.endereco.model_dump()
    if "sefaz" in upd and upd["sefaz"] is not None:
        upd["sefaz"] = payload.sefaz.model_dump()
    await db.companies.update_one({"user_id": user["_id"]}, {"$set": upd})
    comp = await db.companies.find_one({"user_id": user["_id"]})
    return _clean_company(comp)


@api_router.post("/company/certificate")
async def upload_certificate(file: UploadFile = File(...), senha: str = Form(...),
                             user: dict = Depends(current_user)):
    await _get_or_create_company(user["_id"])
    data = await file.read()
    valid_until = None
    installed = False
    try:
        from cryptography.hazmat.primitives.serialization import pkcs12
        key, cert, _ = pkcs12.load_key_and_certificates(data, senha.encode())
        valid_until = cert.not_valid_after.isoformat()
        installed = True
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Certificado ou senha invalidos: {e}")
    await db.companies.update_one({"user_id": user["_id"]}, {"$set": {
        "cert_data": base64.b64encode(data).decode(),
        "cert_password": senha,
        "certificate": {"filename": file.filename,
                        "uploaded_at": now_utc().isoformat(),
                        "valid_until": valid_until, "installed": installed},
    }})
    comp = await db.companies.find_one({"user_id": user["_id"]})
    return _clean_company(comp)


@api_router.post("/company/logo")
async def upload_logo(file: UploadFile = File(...), user: dict = Depends(current_user)):
    await _get_or_create_company(user["_id"])
    data = await file.read()
    if len(data) > 2 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Logo muito grande (max 2MB)")
    await db.companies.update_one({"user_id": user["_id"]}, {"$set": {
        "logo_data": base64.b64encode(data).decode(),
        "logo_filename": file.filename}})
    comp = await db.companies.find_one({"user_id": user["_id"]})
    return _clean_company(comp)


# ============ Clients ============
@api_router.get("/clients")
async def list_clients(user: dict = Depends(current_user)):
    docs = await db.clients.find({"user_id": user["_id"]}).sort("created_at", -1).to_list(1000)
    return [_clean(d) for d in docs]


@api_router.post("/clients")
async def create_client(payload: ClientCreate, user: dict = Depends(current_user)):
    c = Client(user_id=user["_id"], **payload.model_dump())
    res = await db.clients.insert_one(c.to_mongo())
    return _clean(await db.clients.find_one({"_id": res.inserted_id}))


@api_router.put("/clients/{cid}")
async def update_client(cid: str, payload: ClientCreate, user: dict = Depends(current_user)):
    await db.clients.update_one({"_id": ObjectId(cid), "user_id": user["_id"]},
                                {"$set": payload.model_dump()})
    return _clean(await db.clients.find_one({"_id": ObjectId(cid)}))


@api_router.delete("/clients/{cid}")
async def delete_client(cid: str, user: dict = Depends(current_user)):
    await db.clients.delete_one({"_id": ObjectId(cid), "user_id": user["_id"]})
    return {"ok": True}


# ============ Products ============
@api_router.get("/products")
async def list_products(user: dict = Depends(current_user)):
    docs = await db.products.find({"user_id": user["_id"]}).sort("created_at", -1).to_list(1000)
    return [_clean(d) for d in docs]


@api_router.post("/products")
async def create_product(payload: ProductCreate, user: dict = Depends(current_user)):
    p = Product(user_id=user["_id"], **payload.model_dump())
    res = await db.products.insert_one(p.to_mongo())
    return _clean(await db.products.find_one({"_id": res.inserted_id}))


@api_router.put("/products/{pid}")
async def update_product(pid: str, payload: ProductCreate, user: dict = Depends(current_user)):
    await db.products.update_one({"_id": ObjectId(pid), "user_id": user["_id"]},
                                 {"$set": payload.model_dump()})
    return _clean(await db.products.find_one({"_id": ObjectId(pid)}))


@api_router.delete("/products/{pid}")
async def delete_product(pid: str, user: dict = Depends(current_user)):
    await db.products.delete_one({"_id": ObjectId(pid), "user_id": user["_id"]})
    return {"ok": True}


# ============ Invoices ============
def _clean(d: dict) -> dict:
    d = dict(d)
    d["id"] = str(d.pop("_id"))
    return d


async def _build_items(uid: str, itens_in: list) -> list:
    itens = []
    for it in itens_in:
        prod = await db.products.find_one({"_id": ObjectId(it.product_id), "user_id": uid})
        if not prod:
            raise HTTPException(status_code=400, detail="Produto nao encontrado")
        vu = it.valor_unitario if it.valor_unitario is not None else prod.get("valor", 0)
        calc = nfe_utils.calcular_item(prod, it.quantidade, vu)
        itens.append(InvoiceItem(
            product_id=str(prod["_id"]), codigo=prod.get("codigo", ""),
            descricao=prod.get("descricao", ""), ncm=prod.get("ncm", "00000000"),
            cfop=prod.get("cfop", "5102"), unidade=prod.get("unidade", "UN"),
            quantidade=it.quantidade, valor_unitario=vu,
            valor_total=calc["valor_total"], origem=prod.get("origem", "0"),
            cst_icms=prod.get("cst_icms", "102"),
            icms_aliquota=prod.get("icms_aliquota", 0), icms_valor=calc["icms_valor"],
            ipi_aliquota=prod.get("ipi_aliquota", 0), ipi_valor=calc["ipi_valor"],
            pis_aliquota=prod.get("pis_aliquota", 0), pis_valor=calc["pis_valor"],
            cofins_aliquota=prod.get("cofins_aliquota", 0), cofins_valor=calc["cofins_valor"],
        ).model_dump())
    return itens


@api_router.post("/invoices")
async def create_invoice(payload: InvoiceCreate, user: dict = Depends(current_user)):
    uid = user["_id"]
    cli = await db.clients.find_one({"_id": ObjectId(payload.cliente_id), "user_id": uid})
    if not cli:
        raise HTTPException(status_code=400, detail="Cliente nao encontrado")
    comp = await _get_or_create_company(uid)
    itens = await _build_items(uid, payload.itens)
    totais = nfe_utils.calcular_totais(itens)
    numero = comp.get("proximo_numero", 1)
    serie = payload.serie or comp.get("proxima_serie", 1)
    inv = Invoice(
        user_id=uid, numero=numero, serie=serie,
        natureza_operacao=payload.natureza_operacao,
        cliente_id=str(cli["_id"]), cliente=_clean(cli),
        itens=itens, totais=totais, info_adicional=payload.info_adicional,
        status="rascunho",
    )
    res = await db.invoices.insert_one(inv.to_mongo())
    await db.companies.update_one({"user_id": uid}, {"$set": {"proximo_numero": numero + 1}})
    return _clean(await db.invoices.find_one({"_id": res.inserted_id}))


@api_router.get("/invoices")
async def list_invoices(user: dict = Depends(current_user)):
    docs = await db.invoices.find({"user_id": user["_id"]}).sort("created_at", -1).to_list(1000)
    return [_clean(d) for d in docs]


@api_router.get("/invoices/{iid}")
async def get_invoice(iid: str, user: dict = Depends(current_user)):
    d = await db.invoices.find_one({"_id": ObjectId(iid), "user_id": user["_id"]})
    if not d:
        raise HTTPException(status_code=404, detail="Nota nao encontrada")
    return _clean(d)


@api_router.post("/invoices/{iid}/emit")
async def emit_invoice(iid: str, user: dict = Depends(current_user)):
    uid = user["_id"]
    inv = await db.invoices.find_one({"_id": ObjectId(iid), "user_id": uid})
    if not inv:
        raise HTTPException(status_code=404, detail="Nota nao encontrada")
    if inv.get("status") == "autorizada":
        raise HTTPException(status_code=400, detail="Nota ja autorizada")
    comp = await db.companies.find_one({"user_id": uid})
    if not comp.get("cnpj"):
        raise HTTPException(status_code=400, detail="Configure os dados da empresa (CNPJ) antes de emitir")

    emissao = datetime.now(timezone.utc)
    codigo_num = str(random.randint(10000000, 99999999))
    chave = nfe_utils.gerar_chave_acesso(
        comp.get("sefaz", {}).get("uf", "SP"), emissao, comp.get("cnpj", ""),
        "55", inv.get("serie", 1), inv.get("numero", 1), 1, codigo_num)

    try:
        xml = nfe_utils.build_nfe_xml(comp, inv, chave, codigo_num, emissao)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao gerar XML: {e}")

    status = "pendente"
    motivo = "XML gerado. Aguardando transmissao ao SEFAZ."
    protocolo = ""
    nprot = ""
    xml_proc = ""
    signed = xml

    cert_data = comp.get("cert_data")
    if cert_data:
        try:
            pfx = base64.b64decode(cert_data)
            senha = comp.get("cert_password", "")
            signed = nfe_utils.assinar_xml(xml, pfx, senha)
        except Exception as e:
            await db.invoices.update_one({"_id": ObjectId(iid)}, {"$set": {
                "status": "rejeitada", "chave_acesso": chave, "xml": xml,
                "motivo": f"Falha na assinatura: {e}",
                "data_emissao": emissao.isoformat()}})
            return _clean(await db.invoices.find_one({"_id": ObjectId(iid)}))
        # Transmissao real ao SEFAZ
        res = nfe_utils.transmitir_sefaz(signed, comp, pfx, senha)
        # Contingencia automatica (SVC) em caso de falha de comunicacao
        cont_ativa = comp.get("sefaz", {}).get("contingencia", True)
        if cont_ativa and "Falha na comunicacao" in res.get("motivo", ""):
            uf = comp.get("sefaz", {}).get("uf", "SP")
            _svc, tp_emis = nfe_utils.svc_for_uf(uf)
            svc_url = nfe_utils.get_svc_url(uf, comp.get("sefaz", {}).get("ambiente", 2))
            x_just = "Emissao em contingencia por indisponibilidade do webservice do SEFAZ"
            chave = nfe_utils.gerar_chave_acesso(uf, emissao, comp.get("cnpj", ""), "55",
                                                 inv.get("serie", 1), inv.get("numero", 1),
                                                 tp_emis, codigo_num)
            xml_c = nfe_utils.build_nfe_xml(comp, inv, chave, codigo_num, emissao,
                                            tp_emis=tp_emis, x_just=x_just)
            signed = nfe_utils.assinar_xml(xml_c, pfx, senha)
            res = nfe_utils.transmitir_sefaz(signed, comp, pfx, senha, url_override=svc_url)
            res["motivo"] = f"[CONTINGENCIA {_svc}] " + res.get("motivo", "")
        status = res["status"]
        motivo = res["motivo"]
        protocolo = res.get("protocolo", "")
        nprot = res.get("nprot", "")
        xml_proc = res.get("xml_proc", signed)
    else:
        motivo = ("Certificado digital A1 nao configurado. XML gerado sem assinatura. "
                  "Faca upload do certificado em Configuracoes para assinar e transmitir ao SEFAZ.")

    await db.invoices.update_one({"_id": ObjectId(iid)}, {"$set": {
        "status": status, "chave_acesso": chave, "xml": xml_proc or signed,
        "protocolo": protocolo, "nprot": nprot, "xml_proc": xml_proc,
        "motivo": motivo, "data_emissao": emissao.isoformat(),
    }})
    return _clean(await db.invoices.find_one({"_id": ObjectId(iid)}))


class CCeIn(BaseModel):
    texto: str


@api_router.post("/invoices/{iid}/cce")
async def carta_correcao(iid: str, payload: CCeIn, user: dict = Depends(current_user)):
    uid = user["_id"]
    inv = await db.invoices.find_one({"_id": ObjectId(iid), "user_id": uid})
    if not inv:
        raise HTTPException(status_code=404, detail="Nota nao encontrada")
    if inv.get("status") != "autorizada":
        raise HTTPException(status_code=400, detail="A CC-e so pode ser emitida para notas autorizadas")
    if len(payload.texto.strip()) < 15:
        raise HTTPException(status_code=400, detail="A correcao deve ter ao menos 15 caracteres")
    comp = await db.companies.find_one({"user_id": uid})
    cert_data = comp.get("cert_data")
    if not cert_data:
        raise HTTPException(status_code=400, detail="Certificado digital A1 nao configurado")
    seq = len(inv.get("eventos", [])) + 1
    ev_xml = nfe_utils.build_evento_cce(comp, inv["chave_acesso"], seq, payload.texto.strip())
    pfx = base64.b64decode(cert_data)
    senha = comp.get("cert_password", "")
    signed_ev = nfe_utils.assinar_xml(ev_xml, pfx, senha)
    res = nfe_utils.transmitir_evento(signed_ev, comp, pfx, senha)
    evento = {
        "tipo": "Carta de Correcao", "sequencia": seq, "texto": payload.texto.strip(),
        "status": res["status"], "protocolo": res.get("protocolo", ""),
        "motivo": res["motivo"], "data": datetime.now(timezone.utc).isoformat(),
        "xml": signed_ev,
    }
    await db.invoices.update_one({"_id": ObjectId(iid)}, {"$push": {"eventos": evento}})
    return _clean(await db.invoices.find_one({"_id": ObjectId(iid)}))


class CancelIn(BaseModel):
    justificativa: str = ""


@api_router.post("/invoices/{iid}/consultar")
async def consultar_invoice(iid: str, user: dict = Depends(current_user)):
    uid = user["_id"]
    inv = await db.invoices.find_one({"_id": ObjectId(iid), "user_id": uid})
    if not inv:
        raise HTTPException(status_code=404, detail="Nota nao encontrada")
    if not inv.get("chave_acesso"):
        raise HTTPException(status_code=400, detail="Emita a nota antes de consultar o status")
    comp = await db.companies.find_one({"user_id": uid})
    cert_data = comp.get("cert_data")
    if not cert_data:
        raise HTTPException(status_code=400, detail="Certificado digital A1 nao configurado")
    res = nfe_utils.consultar_protocolo(inv["chave_acesso"], comp,
                                         base64.b64decode(cert_data), comp.get("cert_password", ""))
    upd = {"motivo": res["motivo"]}
    if res["status"]:
        upd["status"] = res["status"]
        upd["protocolo"] = res.get("protocolo", "")
        upd["nprot"] = res.get("nprot", "")
    await db.invoices.update_one({"_id": ObjectId(iid)}, {"$set": upd})
    return _clean(await db.invoices.find_one({"_id": ObjectId(iid)}))


@api_router.post("/invoices/{iid}/cancel")
async def cancel_invoice(iid: str, payload: CancelIn = CancelIn(), user: dict = Depends(current_user)):
    uid = user["_id"]
    inv = await db.invoices.find_one({"_id": ObjectId(iid), "user_id": uid})
    if not inv:
        raise HTTPException(status_code=404, detail="Nota nao encontrada")
    comp = await db.companies.find_one({"user_id": uid})
    cert_data = comp.get("cert_data")
    # Cancelamento oficial via SEFAZ quando autorizada + certificado + protocolo
    if inv.get("status") == "autorizada" and cert_data and inv.get("nprot"):
        if len(payload.justificativa.strip()) < 15:
            raise HTTPException(status_code=400, detail="A justificativa deve ter ao menos 15 caracteres")
        pfx = base64.b64decode(cert_data)
        senha = comp.get("cert_password", "")
        ev_xml = nfe_utils.build_evento_cancelamento(comp, inv["chave_acesso"],
                                                      inv["nprot"], payload.justificativa.strip())
        signed_ev = nfe_utils.assinar_xml(ev_xml, pfx, senha)
        res = nfe_utils.transmitir_evento(signed_ev, comp, pfx, senha)
        novo_status = "cancelada" if res["status"] == "registrado" else "autorizada"
        evento = {"tipo": "Cancelamento", "sequencia": len(inv.get("eventos", [])) + 1,
                  "texto": payload.justificativa.strip(), "status": res["status"],
                  "protocolo": res.get("protocolo", ""), "motivo": res["motivo"],
                  "data": datetime.now(timezone.utc).isoformat(), "xml": signed_ev}
        await db.invoices.update_one({"_id": ObjectId(iid)}, {
            "$push": {"eventos": evento},
            "$set": {"status": novo_status, "motivo": res["motivo"]}})
        return _clean(await db.invoices.find_one({"_id": ObjectId(iid)}))
    # Cancelamento local (rascunho/pendente sem transmissao)
    await db.invoices.update_one({"_id": ObjectId(iid)}, {"$set": {
        "status": "cancelada", "motivo": "Nota cancelada pelo usuario."}})
    return _clean(await db.invoices.find_one({"_id": ObjectId(iid)}))


@api_router.delete("/invoices/{iid}")
async def delete_invoice(iid: str, user: dict = Depends(current_user)):
    await db.invoices.delete_one({"_id": ObjectId(iid), "user_id": user["_id"]})
    return {"ok": True}


@api_router.get("/invoices/{iid}/xml")
async def download_xml(iid: str, user: dict = Depends(current_user)):
    inv = await db.invoices.find_one({"_id": ObjectId(iid), "user_id": user["_id"]})
    if not inv or not inv.get("xml"):
        raise HTTPException(status_code=404, detail="XML nao disponivel. Emita a nota primeiro.")
    return StreamingResponse(iter([inv["xml"].encode()]), media_type="application/xml",
                             headers={"Content-Disposition": f"attachment; filename=NFe-{inv.get('numero',0)}.xml"})


@api_router.get("/invoices/{iid}/pdf")
async def download_pdf(iid: str, user: dict = Depends(current_user)):
    inv = await db.invoices.find_one({"_id": ObjectId(iid), "user_id": user["_id"]})
    if not inv:
        raise HTTPException(status_code=404, detail="Nota nao encontrada")
    comp = await db.companies.find_one({"user_id": user["_id"]})
    pdf = nfe_utils.gerar_danfe_pdf(comp or {}, inv)
    return StreamingResponse(iter([pdf]), media_type="application/pdf",
                             headers={"Content-Disposition": f"inline; filename=DANFE-{inv.get('numero',0)}.pdf"})


# ============ Dashboard ============
@api_router.get("/dashboard")
async def dashboard(user: dict = Depends(current_user)):
    uid = user["_id"]
    invoices = await db.invoices.find({"user_id": uid}).to_list(2000)
    total = len(invoices)
    by_status = {"rascunho": 0, "pendente": 0, "autorizada": 0, "rejeitada": 0, "cancelada": 0}
    receita = 0.0
    impostos = 0.0
    monthly = {}
    for inv in invoices:
        st = inv.get("status", "rascunho")
        by_status[st] = by_status.get(st, 0) + 1
        tot = inv.get("totais", {})
        if st in ("autorizada", "pendente"):
            receita += tot.get("v_nf", 0)
            impostos += (tot.get("v_icms", 0) + tot.get("v_ipi", 0) +
                         tot.get("v_pis", 0) + tot.get("v_cofins", 0))
        de = inv.get("data_emissao") or (inv.get("created_at").isoformat()
                                         if isinstance(inv.get("created_at"), datetime) else "")
        if de:
            m = de[:7]
            monthly[m] = monthly.get(m, 0) + tot.get("v_nf", 0)
    monthly_list = [{"mes": k, "valor": round(v, 2)} for k, v in sorted(monthly.items())][-6:]
    clientes = await db.clients.count_documents({"user_id": uid})
    produtos = await db.products.count_documents({"user_id": uid})
    recent = await db.invoices.find({"user_id": uid}).sort("created_at", -1).to_list(5)
    return {
        "total_notas": total, "by_status": by_status,
        "receita": round(receita, 2), "impostos": round(impostos, 2),
        "clientes": clientes, "produtos": produtos,
        "monthly": monthly_list, "recentes": [_clean(r) for r in recent],
    }


async def _reports_data(uid: str, start: Optional[str], end: Optional[str]):
    invoices = await db.invoices.find({"user_id": uid}).sort("created_at", -1).to_list(5000)
    rows = []
    for inv in invoices:
        de = inv.get("data_emissao") or (inv.get("created_at").isoformat()
             if isinstance(inv.get("created_at"), datetime) else "")
        d = de[:10]
        if start and d and d < start:
            continue
        if end and d and d > end:
            continue
        rows.append(inv)
    return rows


@api_router.get("/reports")
async def reports(start: Optional[str] = None, end: Optional[str] = None,
                  user: dict = Depends(current_user)):
    rows = await _reports_data(user["_id"], start, end)
    tot = {"v_prod": 0.0, "v_icms": 0.0, "v_ipi": 0.0, "v_pis": 0.0,
           "v_cofins": 0.0, "v_nf": 0.0}
    considered = 0
    for inv in rows:
        if inv.get("status") in ("autorizada", "pendente"):
            considered += 1
            t = inv.get("totais", {})
            for k in tot:
                tot[k] += t.get(k, 0)
    for k in tot:
        tot[k] = round(tot[k], 2)
    return {"count": len(rows), "faturadas": considered, "totais": tot,
            "notas": [_clean(r) for r in rows]}


@api_router.get("/reports/export.csv")
async def reports_csv(start: Optional[str] = None, end: Optional[str] = None,
                      user: dict = Depends(current_user)):
    import csv, io as _io
    rows = await _reports_data(user["_id"], start, end)
    buf = _io.StringIO()
    w = csv.writer(buf, delimiter=";")
    w.writerow(["Numero", "Serie", "Data", "Cliente", "CNPJ/CPF", "Status",
                "Chave", "Produtos", "ICMS", "IPI", "PIS", "COFINS", "Total"])
    for inv in rows:
        t = inv.get("totais", {})
        w.writerow([inv.get("numero"), inv.get("serie"),
                    (inv.get("data_emissao") or "")[:10],
                    inv.get("cliente", {}).get("nome", ""),
                    inv.get("cliente", {}).get("cpf_cnpj", ""),
                    inv.get("status"), inv.get("chave_acesso", ""),
                    f"{t.get('v_prod',0):.2f}", f"{t.get('v_icms',0):.2f}",
                    f"{t.get('v_ipi',0):.2f}", f"{t.get('v_pis',0):.2f}",
                    f"{t.get('v_cofins',0):.2f}", f"{t.get('v_nf',0):.2f}"])
    return StreamingResponse(iter([buf.getvalue().encode("utf-8-sig")]),
                             media_type="text/csv",
                             headers={"Content-Disposition": "attachment; filename=relatorio-nfe.csv"})


class InutilizacaoIn(BaseModel):
    serie: int
    numero_inicial: int
    numero_final: int
    justificativa: str


@api_router.post("/inutilizacoes")
async def criar_inutilizacao(payload: InutilizacaoIn, user: dict = Depends(current_user)):
    uid = user["_id"]
    if payload.numero_final < payload.numero_inicial:
        raise HTTPException(status_code=400, detail="Numero final menor que o inicial")
    if len(payload.justificativa.strip()) < 15:
        raise HTTPException(status_code=400, detail="A justificativa deve ter ao menos 15 caracteres")
    comp = await db.companies.find_one({"user_id": uid})
    if not comp or not comp.get("cnpj"):
        raise HTTPException(status_code=400, detail="Configure os dados da empresa antes de inutilizar")
    cert_data = comp.get("cert_data")
    if not cert_data:
        raise HTTPException(status_code=400, detail="Certificado digital A1 nao configurado")
    ano = str(datetime.now(timezone.utc).year)
    xml = nfe_utils.build_inutilizacao_xml(comp, ano, payload.serie,
                                           payload.numero_inicial, payload.numero_final,
                                           payload.justificativa.strip())
    pfx = base64.b64decode(cert_data)
    senha = comp.get("cert_password", "")
    signed = nfe_utils.assinar_xml(xml, pfx, senha)
    res = nfe_utils.transmitir_inutilizacao(signed, comp, pfx, senha)
    rec = {"user_id": uid, "serie": payload.serie, "numero_inicial": payload.numero_inicial,
           "numero_final": payload.numero_final, "justificativa": payload.justificativa.strip(),
           "status": res["status"], "protocolo": res.get("protocolo", ""),
           "motivo": res["motivo"], "xml": signed,
           "created_at": datetime.now(timezone.utc).isoformat()}
    r = await db.inutilizacoes.insert_one(rec)
    return _clean(await db.inutilizacoes.find_one({"_id": r.inserted_id}))


@api_router.get("/inutilizacoes")
async def listar_inutilizacoes(user: dict = Depends(current_user)):
    docs = await db.inutilizacoes.find({"user_id": user["_id"]}).sort("created_at", -1).to_list(500)
    return [_clean(d) for d in docs]


@api_router.get("/reports/export.pdf")
async def reports_pdf(start: Optional[str] = None, end: Optional[str] = None,
                      user: dict = Depends(current_user)):
    rows = await _reports_data(user["_id"], start, end)
    tot = {"v_prod": 0.0, "v_icms": 0.0, "v_ipi": 0.0, "v_pis": 0.0, "v_cofins": 0.0, "v_nf": 0.0}
    considered = 0
    for inv in rows:
        if inv.get("status") in ("autorizada", "pendente"):
            considered += 1
            t = inv.get("totais", {})
            for k in tot:
                tot[k] += t.get(k, 0)
    for k in tot:
        tot[k] = round(tot[k], 2)
    data = {"count": len(rows), "faturadas": considered, "totais": tot,
            "notas": [_clean(r) for r in rows]}
    comp = await db.companies.find_one({"user_id": user["_id"]}) or {}
    pdf = nfe_utils.gerar_relatorio_pdf(comp, data, start, end)
    return StreamingResponse(iter([pdf]), media_type="application/pdf",
                             headers={"Content-Disposition": "inline; filename=relatorio-nfe.pdf"})


EMAIL_BASE_URL = "https://integrations.emergentagent.com"


class EmailIn(BaseModel):
    email: EmailStr


@api_router.post("/invoices/{iid}/email")
async def email_invoice(iid: str, payload: EmailIn, user: dict = Depends(current_user)):
    uid = user["_id"]
    inv = await db.invoices.find_one({"_id": ObjectId(iid), "user_id": uid})
    if not inv:
        raise HTTPException(status_code=404, detail="Nota nao encontrada")
    comp = await db.companies.find_one({"user_id": uid}) or {}
    numero = inv.get("numero", 0)
    logo_bytes = base64.b64decode(comp["logo_data"]) if comp.get("logo_data") else None
    pdf = nfe_utils.gerar_danfe_pdf(comp, inv, logo_bytes)
    attachments = [{"filename": f"DANFE-{numero}.pdf",
                    "content": base64.b64encode(pdf).decode()}]
    if inv.get("xml"):
        attachments.append({"filename": f"NFe-{numero}.xml",
                            "content": base64.b64encode(inv["xml"].encode()).decode()})
    html = (f"<div style='font-family:Arial,sans-serif;color:#0f172a'>"
            f"<h2>Nota Fiscal Eletronica Nº {numero}</h2>"
            f"<p>Ola, segue em anexo a DANFE (PDF) e o XML da NF-e emitida por "
            f"<b>{comp.get('razao_social','')}</b>.</p>"
            f"<p>Chave de acesso: <code>{inv.get('chave_acesso','')}</code></p>"
            f"<p>Valor total: R$ {inv.get('totais',{}).get('v_nf',0):.2f}</p></div>")
    email_key = os.environ.get("EMERGENT_EMAIL_KEY")
    from_name = os.environ.get("EMAIL_FROM_NAME", "NF-e System")
    if not email_key:
        raise HTTPException(status_code=500, detail="Servico de e-mail nao configurado")
    body = {"to": [payload.email], "subject": f"NF-e Nº {numero} - {comp.get('razao_social','')}",
            "html": html, "from_name": from_name, "attachments": attachments}
    try:
        async with httpx.AsyncClient(timeout=45) as cliente:
            resp = await cliente.post(f"{EMAIL_BASE_URL}/api/v1/email/send",
                                      headers={"X-Email-Key": email_key}, json=body)
            resp.raise_for_status()
    except httpx.HTTPStatusError as e:
        logger.error(f"Email falhou: {e.response.status_code} {e.response.text}")
        raise HTTPException(status_code=502, detail="Falha ao enviar o e-mail")
    except Exception as e:
        logger.error(f"Email erro: {e}")
        raise HTTPException(status_code=500, detail="Falha ao enviar o e-mail")
    await db.invoices.update_one({"_id": ObjectId(iid)}, {"$set": {"email_enviado": payload.email}})
    return {"status": "success", "email": payload.email}


class ManifestoIn(BaseModel):
    chave: str
    tipo: str
    justificativa: str = ""


@api_router.post("/manifestacoes")
async def criar_manifestacao(payload: ManifestoIn, user: dict = Depends(current_user)):
    uid = user["_id"]
    chave = "".join(ch for ch in payload.chave if ch.isdigit())
    if len(chave) != 44:
        raise HTTPException(status_code=400, detail="Chave de acesso deve ter 44 digitos")
    if payload.tipo not in nfe_utils.MANIFESTO_TIPOS:
        raise HTTPException(status_code=400, detail="Tipo de manifestacao invalido")
    if payload.tipo in ("210220", "210240") and len(payload.justificativa.strip()) < 15:
        raise HTTPException(status_code=400, detail="Justificativa deve ter ao menos 15 caracteres")
    comp = await db.companies.find_one({"user_id": uid}) or {}
    if not comp.get("cnpj"):
        raise HTTPException(status_code=400, detail="Configure o CNPJ da empresa antes de manifestar")
    cert_data = comp.get("cert_data")
    if not cert_data:
        raise HTTPException(status_code=400, detail="Certificado digital A1 nao configurado")
    amb = int(comp.get("sefaz", {}).get("ambiente", 2))
    ev = nfe_utils.build_evento_manifestacao(comp["cnpj"], chave, payload.tipo,
                                             payload.justificativa.strip(), amb)
    pfx = base64.b64decode(cert_data)
    senha = comp.get("cert_password", "")
    signed = nfe_utils.assinar_xml(ev, pfx, senha)
    res = nfe_utils.transmitir_evento_nacional(signed, amb, pfx, senha)
    rec = {"user_id": uid, "chave": chave, "tipo": payload.tipo,
           "descricao": nfe_utils.MANIFESTO_TIPOS[payload.tipo],
           "justificativa": payload.justificativa.strip(), "status": res["status"],
           "protocolo": res.get("protocolo", ""), "motivo": res["motivo"],
           "created_at": datetime.now(timezone.utc).isoformat()}
    r = await db.manifestacoes.insert_one(rec)
    return _clean(await db.manifestacoes.find_one({"_id": r.inserted_id}))


@api_router.get("/manifestacoes")
async def listar_manifestacoes(user: dict = Depends(current_user)):
    docs = await db.manifestacoes.find({"user_id": user["_id"]}).sort("created_at", -1).to_list(500)
    return [_clean(d) for d in docs]


@api_router.get("/manifestacoes/tipos")
async def manifesto_tipos(user: dict = Depends(current_user)):
    return nfe_utils.MANIFESTO_TIPOS


# Inclusão do roteador de rotas prefixadas /api
app.include_router(api_router)


@app.on_event("startup")
async def startup():
    await auth_mod.seed_admin(db)
    await db.users.create_index("email", unique=True)
