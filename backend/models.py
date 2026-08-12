from pydantic import BaseModel, Field, ConfigDict, BeforeValidator, EmailStr
from typing import List, Optional, Annotated, Any
from datetime import datetime, timezone
from bson import ObjectId


def _to_str_id(v: Any) -> Any:
    if isinstance(v, ObjectId):
        return str(v)
    return v


PyObjectId = Annotated[str, BeforeValidator(_to_str_id)]


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


class BaseDocument(BaseModel):
    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)

    id: Optional[PyObjectId] = Field(default=None, alias="_id")

    @classmethod
    def from_mongo(cls, doc: dict):
        if not doc:
            return None
        return cls(**doc)

    def to_mongo(self, exclude_id: bool = True) -> dict:
        data = self.model_dump(by_alias=True, exclude_none=False)
        if exclude_id and "_id" in data:
            data.pop("_id", None)
        if data.get("_id") is None:
            data.pop("_id", None)
        return data


# ---------- Address ----------
class Endereco(BaseModel):
    logradouro: str = ""
    numero: str = ""
    complemento: str = ""
    bairro: str = ""
    municipio: str = ""
    cod_municipio: str = ""
    uf: str = ""
    cep: str = ""
    fone: str = ""


# ---------- User ----------
class User(BaseDocument):
    email: str
    name: str = ""
    role: str = "user"
    password_hash: Optional[str] = None
    created_at: datetime = Field(default_factory=now_utc)


# ---------- Company / Emitente ----------
class Certificate(BaseModel):
    filename: str = ""
    uploaded_at: Optional[str] = None
    valid_until: Optional[str] = None
    installed: bool = False


class SefazConfig(BaseModel):
    uf: str = "SP"
    ambiente: int = 2  # 1=producao, 2=homologacao
    csc: str = ""
    csc_id: str = ""


class Company(BaseDocument):
    user_id: str
    razao_social: str = ""
    nome_fantasia: str = ""
    cnpj: str = ""
    ie: str = ""
    im: str = ""
    crt: int = 1  # 1=Simples Nacional, 2=SN excesso, 3=Regime Normal
    endereco: Endereco = Field(default_factory=Endereco)
    certificate: Certificate = Field(default_factory=Certificate)
    sefaz: SefazConfig = Field(default_factory=SefazConfig)
    proxima_serie: int = 1
    proximo_numero: int = 1
    auto_email: bool = False
    email_subject: str = ""
    email_body: str = ""
    created_at: datetime = Field(default_factory=now_utc)


class CompanyUpdate(BaseModel):
    razao_social: Optional[str] = None
    nome_fantasia: Optional[str] = None
    cnpj: Optional[str] = None
    ie: Optional[str] = None
    im: Optional[str] = None
    crt: Optional[int] = None
    endereco: Optional[Endereco] = None
    sefaz: Optional[SefazConfig] = None
    proxima_serie: Optional[int] = None
    proximo_numero: Optional[int] = None
    auto_email: Optional[bool] = None
    email_subject: Optional[str] = None
    email_body: Optional[str] = None


# ---------- Client / Destinatario ----------
class Client(BaseDocument):
    user_id: str
    tipo: str = "PJ"  # PF or PJ
    nome: str
    cpf_cnpj: str = ""
    ie: str = ""
    email: str = ""
    fone: str = ""
    indicador_ie: int = 9  # 1=Contribuinte, 2=Isento, 9=Nao contribuinte
    endereco: Endereco = Field(default_factory=Endereco)
    created_at: datetime = Field(default_factory=now_utc)


class ClientCreate(BaseModel):
    tipo: str = "PJ"
    nome: str
    cpf_cnpj: str = ""
    ie: str = ""
    email: str = ""
    fone: str = ""
    indicador_ie: int = 9
    endereco: Endereco = Field(default_factory=Endereco)


# ---------- Product ----------
class Product(BaseDocument):
    user_id: str
    codigo: str
    descricao: str
    ncm: str = "00000000"
    cest: str = ""
    cfop: str = "5102"
    unidade: str = "UN"
    valor: float = 0.0
    origem: str = "0"
    cst_icms: str = "102"  # for Simples Nacional (CSOSN)
    icms_aliquota: float = 0.0
    ipi_cst: str = "53"
    ipi_aliquota: float = 0.0
    pis_cst: str = "01"
    pis_aliquota: float = 0.0
    cofins_cst: str = "01"
    cofins_aliquota: float = 0.0
    created_at: datetime = Field(default_factory=now_utc)


class ProductCreate(BaseModel):
    codigo: str
    descricao: str
    ncm: str = "00000000"
    cest: str = ""
    cfop: str = "5102"
    unidade: str = "UN"
    valor: float = 0.0
    origem: str = "0"
    cst_icms: str = "102"
    icms_aliquota: float = 0.0
    ipi_cst: str = "53"
    ipi_aliquota: float = 0.0
    pis_cst: str = "01"
    pis_aliquota: float = 0.0
    cofins_cst: str = "01"
    cofins_aliquota: float = 0.0


# ---------- Invoice / NF-e ----------
class InvoiceItem(BaseModel):
    product_id: str = ""
    codigo: str
    descricao: str
    ncm: str = "00000000"
    cfop: str = "5102"
    unidade: str = "UN"
    quantidade: float = 1.0
    valor_unitario: float = 0.0
    valor_total: float = 0.0
    origem: str = "0"
    cst_icms: str = "102"
    icms_aliquota: float = 0.0
    icms_valor: float = 0.0
    ipi_aliquota: float = 0.0
    ipi_valor: float = 0.0
    pis_aliquota: float = 0.0
    pis_valor: float = 0.0
    cofins_aliquota: float = 0.0
    cofins_valor: float = 0.0


class InvoiceTotais(BaseModel):
    v_prod: float = 0.0
    v_icms: float = 0.0
    v_ipi: float = 0.0
    v_pis: float = 0.0
    v_cofins: float = 0.0
    v_desc: float = 0.0
    v_frete: float = 0.0
    v_nf: float = 0.0


class Invoice(BaseDocument):
    user_id: str
    numero: int = 0
    serie: int = 1
    natureza_operacao: str = "Venda de mercadoria"
    tipo_operacao: int = 1  # 0=entrada, 1=saida
    finalidade: int = 1  # 1=normal
    cliente_id: str = ""
    cliente: dict = Field(default_factory=dict)
    itens: List[InvoiceItem] = Field(default_factory=list)
    totais: InvoiceTotais = Field(default_factory=InvoiceTotais)
    info_adicional: str = ""
    status: str = "rascunho"  # rascunho, pendente, autorizada, rejeitada, cancelada
    chave_acesso: str = ""
    protocolo: str = ""
    nprot: str = ""
    xml_proc: str = ""
    eventos: List[dict] = Field(default_factory=list)
    motivo: str = ""
    xml: str = ""
    data_emissao: Optional[str] = None
    created_at: datetime = Field(default_factory=now_utc)


class InvoiceItemCreate(BaseModel):
    product_id: str = ""
    quantidade: float = 1.0
    valor_unitario: Optional[float] = None


class InvoiceCreate(BaseModel):
    natureza_operacao: str = "Venda de mercadoria"
    cliente_id: str
    itens: List[InvoiceItemCreate]
    info_adicional: str = ""
    serie: Optional[int] = None
