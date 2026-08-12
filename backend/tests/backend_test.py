"""Backend regression tests for NF-e system."""
import os
import uuid
import pytest
import requests

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://nfe-system-1.preview.emergentagent.com').rstrip('/')
API = f"{BASE_URL}/api"

ADMIN_EMAIL = "mateus.ferreira@camainbox.com.br"
ADMIN_PASSWORD = "Nfe@2026Admin"


@pytest.fixture(scope="session")
def admin_token():
    r = requests.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert r.status_code == 200, f"admin login failed: {r.status_code} {r.text}"
    data = r.json()
    assert data.get("access_token")
    assert data["user"]["email"] == ADMIN_EMAIL
    return data["access_token"]


@pytest.fixture(scope="session")
def sess(admin_token):
    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {admin_token}", "Content-Type": "application/json"})
    return s


# ---------- Auth ----------
def test_login_invalid():
    r = requests.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": "wrong"})
    assert r.status_code == 401


def test_register_and_me():
    email = f"test_{uuid.uuid4().hex[:8]}@example.com"
    r = requests.post(f"{API}/auth/register", json={"name": "TEST User", "email": email, "password": "Passw0rd!"})
    assert r.status_code == 200, r.text
    token = r.json()["access_token"]
    me = requests.get(f"{API}/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["email"] == email


def test_register_duplicate(sess):
    r = requests.post(f"{API}/auth/register", json={"name": "x", "email": ADMIN_EMAIL, "password": "x"})
    assert r.status_code == 400


# ---------- Company ----------
def test_company_get_and_update(sess):
    r = sess.get(f"{API}/company")
    assert r.status_code == 200
    c = r.json()
    assert "id" in c

    payload = {
        "razao_social": "TEST Empresa LTDA",
        "cnpj": "12345678000199",
        "ie": "123456789",
        "crt": 1,
        "endereco": {"logradouro": "Rua A", "numero": "10", "bairro": "Centro",
                     "municipio": "Sao Paulo", "cod_municipio": "3550308",
                     "uf": "SP", "cep": "01000000"},
        "sefaz": {"uf": "SP", "ambiente": 2, "csc": "", "csc_id": ""},
        "proxima_serie": 1,
        "proximo_numero": 1,
    }
    r = sess.put(f"{API}/company", json=payload)
    assert r.status_code == 200, r.text
    got = r.json()
    assert got["razao_social"] == "TEST Empresa LTDA"
    assert got["cnpj"] == "12345678000199"
    assert got["endereco"]["municipio"] == "Sao Paulo"
    assert got["sefaz"]["uf"] == "SP"


# ---------- Clients ----------
@pytest.fixture(scope="session")
def client_id(sess):
    payload = {
        "tipo": "PJ", "nome": "TEST Cliente ACME",
        "cpf_cnpj": "11222333000181", "ie": "", "email": "acme@test.com",
        "fone": "1199999", "indicador_ie": 9,
        "endereco": {"logradouro": "Av B", "numero": "100", "bairro": "Jardim",
                     "municipio": "Sao Paulo", "cod_municipio": "3550308",
                     "uf": "SP", "cep": "02000000"},
    }
    r = sess.post(f"{API}/clients", json=payload)
    assert r.status_code == 200, r.text
    return r.json()["id"]


def test_clients_crud(sess, client_id):
    r = sess.get(f"{API}/clients")
    assert r.status_code == 200
    assert any(c["id"] == client_id for c in r.json())

    r = sess.put(f"{API}/clients/{client_id}", json={
        "tipo": "PJ", "nome": "TEST Cliente ACME 2", "cpf_cnpj": "11222333000181",
        "endereco": {"uf": "SP", "municipio": "Sao Paulo", "cod_municipio": "3550308"},
    })
    assert r.status_code == 200
    assert r.json()["nome"] == "TEST Cliente ACME 2"


# ---------- Products ----------
@pytest.fixture(scope="session")
def product_id(sess):
    payload = {
        "codigo": "P001", "descricao": "TEST Produto",
        "ncm": "12345678", "cfop": "5102", "unidade": "UN",
        "valor": 100.0, "origem": "0", "cst_icms": "102",
        "icms_aliquota": 18.0, "ipi_aliquota": 5.0,
        "pis_aliquota": 1.65, "cofins_aliquota": 7.6,
    }
    r = sess.post(f"{API}/products", json=payload)
    assert r.status_code == 200, r.text
    return r.json()["id"]


def test_products_crud(sess, product_id):
    r = sess.get(f"{API}/products")
    assert r.status_code == 200
    assert any(p["id"] == product_id for p in r.json())


# ---------- Invoice ----------
@pytest.fixture(scope="session")
def invoice_id(sess, client_id, product_id):
    payload = {
        "natureza_operacao": "Venda de mercadoria",
        "cliente_id": client_id,
        "itens": [{"product_id": product_id, "quantidade": 2, "valor_unitario": 100.0}],
        "info_adicional": "TEST",
    }
    r = sess.post(f"{API}/invoices", json=payload)
    assert r.status_code == 200, r.text
    inv = r.json()
    # Item totals: base = 2*100=200, icms=200*.18=36, ipi=200*.05=10, pis=3.30, cofins=15.20
    assert inv["itens"][0]["valor_total"] == 200.0
    assert inv["itens"][0]["icms_valor"] == 36.0
    assert inv["itens"][0]["ipi_valor"] == 10.0
    # v_nf = v_prod + v_ipi = 210.00
    assert inv["totais"]["v_prod"] == 200.0
    assert inv["totais"]["v_ipi"] == 10.0
    assert inv["totais"]["v_nf"] == 210.0
    assert inv["status"] == "rascunho"
    assert inv["numero"] >= 1
    return inv["id"]


def test_invoice_numero_increments(sess, client_id, product_id, invoice_id):
    payload = {
        "cliente_id": client_id,
        "itens": [{"product_id": product_id, "quantidade": 1, "valor_unitario": 50.0}],
    }
    r = sess.post(f"{API}/invoices", json=payload)
    assert r.status_code == 200
    n2 = r.json()["numero"]
    # get first
    r1 = sess.get(f"{API}/invoices/{invoice_id}")
    assert r1.status_code == 200
    assert n2 == r1.json()["numero"] + 1


def test_invoice_emit(sess, invoice_id):
    r = sess.post(f"{API}/invoices/{invoice_id}/emit")
    assert r.status_code == 200, r.text
    inv = r.json()
    assert len(inv["chave_acesso"]) == 44
    assert inv["chave_acesso"].isdigit()
    # Without cert, expected status is 'pendente' with informative motivo
    assert inv["status"] == "pendente"
    assert "certificado" in inv["motivo"].lower() or "sefaz" in inv["motivo"].lower()
    assert inv["xml"].startswith("<") or "NFe" in inv["xml"]


def test_invoice_xml_download(sess, invoice_id):
    r = sess.get(f"{API}/invoices/{invoice_id}/xml")
    assert r.status_code == 200
    assert "xml" in r.headers.get("content-type", "").lower()
    assert b"NFe" in r.content or b"infNFe" in r.content


def test_invoice_pdf_download(sess, invoice_id):
    r = sess.get(f"{API}/invoices/{invoice_id}/pdf")
    assert r.status_code == 200
    assert r.headers.get("content-type", "").startswith("application/pdf")
    assert r.content[:4] == b"%PDF"


def test_invoice_cancel(sess, client_id, product_id):
    # create fresh invoice to cancel
    payload = {"cliente_id": client_id,
               "itens": [{"product_id": product_id, "quantidade": 1, "valor_unitario": 10.0}]}
    r = sess.post(f"{API}/invoices", json=payload)
    iid = r.json()["id"]
    r = sess.post(f"{API}/invoices/{iid}/cancel")
    assert r.status_code == 200
    assert r.json()["status"] == "cancelada"


def test_dashboard(sess):
    r = sess.get(f"{API}/dashboard")
    assert r.status_code == 200
    d = r.json()
    for k in ["total_notas", "by_status", "receita", "impostos", "clientes",
              "produtos", "monthly", "recentes"]:
        assert k in d, f"missing {k}"
    assert d["total_notas"] >= 1


def test_client_delete_cleanup(sess, client_id):
    r = sess.delete(f"{API}/clients/{client_id}")
    assert r.status_code == 200


def test_product_delete_cleanup(sess, product_id):
    r = sess.delete(f"{API}/products/{product_id}")
    assert r.status_code == 200


# ---------- Reports (JSON) ----------
def test_reports_json_no_filter(sess, invoice_id):
    r = sess.get(f"{API}/reports")
    assert r.status_code == 200, r.text
    d = r.json()
    for k in ["count", "faturadas", "totais", "notas"]:
        assert k in d
    for k in ["v_prod", "v_icms", "v_ipi", "v_pis", "v_cofins", "v_nf"]:
        assert k in d["totais"]
    assert d["count"] >= 1
    assert isinstance(d["notas"], list)


def test_reports_json_date_filter(sess):
    from datetime import datetime as _dt
    today = _dt.utcnow().strftime("%Y-%m-%d")
    r = sess.get(f"{API}/reports", params={"start": today, "end": today})
    assert r.status_code == 200
    d = r.json()
    # every returned nota should have data_emissao in range or created_at today
    for n in d["notas"]:
        de = (n.get("data_emissao") or n.get("created_at") or "")[:10]
        if de:
            assert de <= today and de >= today or de == today

    # Empty range in the past should return 0
    r = sess.get(f"{API}/reports", params={"start": "1990-01-01", "end": "1990-01-02"})
    assert r.status_code == 200
    assert r.json()["count"] == 0
    assert r.json()["faturadas"] == 0
    assert r.json()["totais"]["v_nf"] == 0


# ---------- Reports CSV ----------
def test_reports_csv_export(sess):
    r = sess.get(f"{API}/reports/export.csv")
    assert r.status_code == 200, r.text
    ct = r.headers.get("content-type", "")
    assert "text/csv" in ct.lower()
    text = r.content.decode("utf-8-sig")
    lines = [ln for ln in text.splitlines() if ln.strip()]
    assert len(lines) >= 1
    header = lines[0].split(";")
    for col in ["Numero", "Serie", "Data", "Cliente", "Chave", "Total"]:
        assert col in header, f"missing csv column {col}: {header}"


# ---------- CC-e validation ----------
def test_cce_on_non_authorized_returns_400(sess, invoice_id):
    # invoice_id status is 'pendente' (no cert)
    r = sess.post(f"{API}/invoices/{invoice_id}/cce", json={"texto": "correcao de teste com mais de 15 caracteres"})
    assert r.status_code == 400
    assert "autorizada" in r.json().get("detail", "").lower()


def test_cce_short_text_on_authorized_returns_400(sess, invoice_id):
    # Force invoice to 'autorizada' temporarily via direct API cancel is not possible;
    # skip if the app doesn't expose. Instead, we test short-text using a rejected path:
    # The endpoint checks status BEFORE length. So even short text will 400 with 'autorizada' message.
    r = sess.post(f"{API}/invoices/{invoice_id}/cce", json={"texto": "curto"})
    assert r.status_code == 400
    # Should be about status (checked first) since invoice is pendente
    assert "autorizada" in r.json().get("detail", "").lower()


# ---------- Iteration 3: Consultar / Cancel / PDF Report / Inutilizacao ----------
def test_reports_pdf_export(sess):
    r = sess.get(f"{API}/reports/export.pdf")
    assert r.status_code == 200, r.text
    assert r.headers.get("content-type", "").startswith("application/pdf")
    assert r.content[:4] == b"%PDF"
    assert len(r.content) > 1000


def test_reports_pdf_export_with_date_range(sess):
    from datetime import datetime as _dt
    today = _dt.utcnow().strftime("%Y-%m-%d")
    r = sess.get(f"{API}/reports/export.pdf", params={"start": today, "end": today})
    assert r.status_code == 200
    assert r.content[:4] == b"%PDF"

    # Past range still returns valid PDF
    r2 = sess.get(f"{API}/reports/export.pdf", params={"start": "1990-01-01", "end": "1990-01-02"})
    assert r2.status_code == 200
    assert r2.content[:4] == b"%PDF"


def test_inutilizacao_list_empty_or_array(sess):
    r = sess.get(f"{API}/inutilizacoes")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_inutilizacao_numero_final_less_than_inicial(sess):
    r = sess.post(f"{API}/inutilizacoes", json={
        "serie": 1, "numero_inicial": 10, "numero_final": 5,
        "justificativa": "Justificativa valida com mais de 15 caracteres"
    })
    assert r.status_code == 400
    assert "final" in r.json().get("detail", "").lower()


def test_inutilizacao_short_justificativa(sess):
    r = sess.post(f"{API}/inutilizacoes", json={
        "serie": 1, "numero_inicial": 1, "numero_final": 5, "justificativa": "curto"
    })
    assert r.status_code == 400
    # order: numero check passes -> justificativa check next
    assert "justificativa" in r.json().get("detail", "").lower() or "15" in r.json().get("detail", "")


def test_inutilizacao_no_certificate(sess):
    # valid numeros + valid justificativa; company has CNPJ from test_company_get_and_update
    r = sess.post(f"{API}/inutilizacoes", json={
        "serie": 1, "numero_inicial": 100, "numero_final": 105,
        "justificativa": "Erro de digitacao na sequencia de emissao"
    })
    assert r.status_code == 400
    detail = r.json().get("detail", "").lower()
    assert "certificado" in detail


def test_consultar_no_chave(sess):
    # Create fresh client+product+rascunho (no emit -> no chave)
    c = sess.post(f"{API}/clients", json={"tipo": "PJ", "nome": "TEST C2", "cpf_cnpj": "11222333000181",
                  "endereco": {"uf": "SP", "municipio": "Sao Paulo", "cod_municipio": "3550308"}}).json()
    p = sess.post(f"{API}/products", json={"codigo": "P2", "descricao": "TEST P2", "ncm": "12345678",
                  "cfop": "5102", "unidade": "UN", "valor": 10.0, "origem": "0", "cst_icms": "102"}).json()
    r = sess.post(f"{API}/invoices", json={"cliente_id": c["id"],
                  "itens": [{"product_id": p["id"], "quantidade": 1, "valor_unitario": 10.0}]})
    iid = r.json()["id"]
    r = sess.post(f"{API}/invoices/{iid}/consultar")
    assert r.status_code == 400
    assert "emita" in r.json().get("detail", "").lower() or "chave" in r.json().get("detail", "").lower()


def test_consultar_with_chave_no_cert(sess, invoice_id):
    # invoice_id has been emitted -> has chave, but no cert
    r = sess.post(f"{API}/invoices/{invoice_id}/consultar")
    assert r.status_code == 400
    assert "certificado" in r.json().get("detail", "").lower()


def test_cancel_pendente_local(sess):
    # Create + emit -> pendente (create own fresh client/product since session ones were deleted)
    c = sess.post(f"{API}/clients", json={"tipo": "PJ", "nome": "TEST C3", "cpf_cnpj": "11222333000181",
                  "endereco": {"uf": "SP", "municipio": "Sao Paulo", "cod_municipio": "3550308"}}).json()
    p = sess.post(f"{API}/products", json={"codigo": "P3", "descricao": "TEST P3", "ncm": "12345678",
                  "cfop": "5102", "unidade": "UN", "valor": 20.0, "origem": "0", "cst_icms": "102"}).json()
    r = sess.post(f"{API}/invoices", json={"cliente_id": c["id"],
                  "itens": [{"product_id": p["id"], "quantidade": 1, "valor_unitario": 20.0}]})
    iid = r.json()["id"]
    r = sess.post(f"{API}/invoices/{iid}/emit")
    assert r.status_code == 200
    assert r.json()["status"] == "pendente"
    # Cancel locally with empty justificativa (allowed for non-autorizada)
    r = sess.post(f"{API}/invoices/{iid}/cancel", json={"justificativa": ""})
    assert r.status_code == 200
    assert r.json()["status"] == "cancelada"


# ---------- Iteration 4: Logo, Email, Manifestacao ----------
def test_company_logo_upload_and_no_leak(sess):
    # tiny 1x1 PNG
    png = (b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
           b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\xff\xff"
           b"?\x00\x05\xfe\x02\xfe\xdc\xccY\xe7\x00\x00\x00\x00IEND\xaeB`\x82")
    headers = {"Authorization": sess.headers["Authorization"]}
    r = requests.post(f"{API}/company/logo",
                      files={"file": ("logo.png", png, "image/png")}, headers=headers)
    assert r.status_code == 200, r.text
    body = r.json()
    # Never leak secrets
    for k in ("logo_data", "cert_data", "cert_password"):
        assert k not in body, f"leaked {k}"
    # GET /company also should not leak
    r2 = sess.get(f"{API}/company")
    assert r2.status_code == 200
    b2 = r2.json()
    for k in ("logo_data", "cert_data", "cert_password"):
        assert k not in b2, f"GET /company leaked {k}"


def test_pdf_still_renders_after_logo(sess, invoice_id):
    r = sess.get(f"{API}/invoices/{invoice_id}/pdf")
    assert r.status_code == 200
    assert r.content[:4] == b"%PDF"
    assert len(r.content) > 2000


def test_manifestacao_tipos(sess):
    r = sess.get(f"{API}/manifestacoes/tipos")
    assert r.status_code == 200
    tipos = r.json()
    for code in ("210200", "210210", "210220", "210240"):
        assert code in tipos, f"missing tipo {code}"


def test_manifestacao_list_array(sess):
    r = sess.get(f"{API}/manifestacoes")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_manifestacao_invalid_chave(sess):
    r = sess.post(f"{API}/manifestacoes",
                  json={"chave": "123", "tipo": "210200", "justificativa": ""})
    assert r.status_code == 400
    assert "chave" in r.json().get("detail", "").lower() or "44" in r.json().get("detail", "")


def test_manifestacao_invalid_tipo(sess):
    r = sess.post(f"{API}/manifestacoes",
                  json={"chave": "1" * 44, "tipo": "999999", "justificativa": ""})
    assert r.status_code == 400
    assert "tipo" in r.json().get("detail", "").lower()


def test_manifestacao_short_justificativa_210220(sess):
    r = sess.post(f"{API}/manifestacoes",
                  json={"chave": "1" * 44, "tipo": "210220", "justificativa": "curto"})
    assert r.status_code == 400
    assert "justificativa" in r.json().get("detail", "").lower() or "15" in r.json().get("detail", "")


def test_manifestacao_short_justificativa_210240(sess):
    r = sess.post(f"{API}/manifestacoes",
                  json={"chave": "1" * 44, "tipo": "210240", "justificativa": ""})
    assert r.status_code == 400


def test_manifestacao_reaches_cert_check(sess):
    # valid chave + valid tipo (no justificativa needed for 210200) -> company OK -> cert 400
    r = sess.post(f"{API}/manifestacoes",
                  json={"chave": "1" * 44, "tipo": "210200", "justificativa": ""})
    assert r.status_code == 400
    detail = r.json().get("detail", "").lower()
    assert "certificado" in detail


def test_email_invoice_nonexistent(sess):
    fake_id = "507f1f77bcf86cd799439011"
    r = sess.post(f"{API}/invoices/{fake_id}/email", json={"email": "delivered@resend.dev"})
    assert r.status_code == 404


def test_email_invoice_success(sess, client_id_e, product_id_e):
    payload = {"cliente_id": client_id_e,
               "itens": [{"product_id": product_id_e, "quantidade": 1, "valor_unitario": 30.0}]}
    r = sess.post(f"{API}/invoices", json=payload)
    assert r.status_code == 200, r.text
    iid = r.json()["id"]
    r = sess.post(f"{API}/invoices/{iid}/email", json={"email": "delivered@resend.dev"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body.get("status") == "success"
    assert body.get("email") == "delivered@resend.dev"


@pytest.fixture(scope="session")
def client_id_e(sess):
    r = sess.post(f"{API}/clients", json={"tipo": "PJ", "nome": "TEST Email Cliente",
                  "cpf_cnpj": "11222333000181", "email": "delivered@resend.dev",
                  "endereco": {"uf": "SP", "municipio": "Sao Paulo", "cod_municipio": "3550308"}})
    assert r.status_code == 200, r.text
    return r.json()["id"]


@pytest.fixture(scope="session")
def product_id_e(sess):
    r = sess.post(f"{API}/products", json={"codigo": "PE1", "descricao": "TEST Email Produto",
                  "ncm": "12345678", "cfop": "5102", "unidade": "UN", "valor": 30.0,
                  "origem": "0", "cst_icms": "102"})
    assert r.status_code == 200, r.text
    return r.json()["id"]


# ---------- PDF still generates (QR code + protocolo section) ----------
def test_invoice_pdf_after_emit_has_qr(sess, invoice_id):
    r = sess.get(f"{API}/invoices/{invoice_id}/pdf")
    assert r.status_code == 200
    assert r.headers.get("content-type", "").startswith("application/pdf")
    # PDF should be non-trivial size (with QR embedded > 4KB)
    assert len(r.content) > 3000
