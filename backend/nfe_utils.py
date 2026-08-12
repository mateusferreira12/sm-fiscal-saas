"""NF-e utilities: chave de acesso, tax calculation, XML (layout 4.00),
digital signature (A1 certificate) and DANFE PDF generation."""
import io
import os
import re
from datetime import datetime, timezone, timedelta

UF_CODES = {
    "RO": "11", "AC": "12", "AM": "13", "RR": "14", "PA": "15", "AP": "16",
    "TO": "17", "MA": "21", "PI": "22", "CE": "23", "RN": "24", "PB": "25",
    "PE": "26", "AL": "27", "SE": "28", "BA": "29", "MG": "31", "ES": "32",
    "RJ": "33", "SP": "35", "PR": "41", "SC": "42", "RS": "43", "MS": "50",
    "MT": "51", "GO": "52", "DF": "53",
}

# ---- SEFAZ Web Service endpoints (NFe 4.00) ----
# UFs com autorizador proprio + fallback SVRS/SVAN.
_SVRS = {
    "NFeAutorizacao4": {
        1: "https://nfe.svrs.rs.gov.br/ws/NfeAutorizacao/NFeAutorizacao4.asmx",
        2: "https://nfe-homologacao.svrs.rs.gov.br/ws/NfeAutorizacao/NFeAutorizacao4.asmx",
    },
    "NFeRetAutorizacao4": {
        1: "https://nfe.svrs.rs.gov.br/ws/NfeRetAutorizacao/NFeRetAutorizacao4.asmx",
        2: "https://nfe-homologacao.svrs.rs.gov.br/ws/NfeRetAutorizacao/NFeRetAutorizacao4.asmx",
    },
    "NFeRecepcaoEvento4": {
        1: "https://nfe.svrs.rs.gov.br/ws/recepcaoevento/recepcaoevento4.asmx",
        2: "https://nfe-homologacao.svrs.rs.gov.br/ws/recepcaoevento/recepcaoevento4.asmx",
    },
    "NFeConsultaProtocolo4": {
        1: "https://nfe.svrs.rs.gov.br/ws/NfeConsulta/NfeConsulta4.asmx",
        2: "https://nfe-homologacao.svrs.rs.gov.br/ws/NfeConsulta/NfeConsulta4.asmx",
    },
    "NFeInutilizacao4": {
        1: "https://nfe.svrs.rs.gov.br/ws/nfeinutilizacao/nfeinutilizacao4.asmx",
        2: "https://nfe-homologacao.svrs.rs.gov.br/ws/nfeinutilizacao/nfeinutilizacao4.asmx",
    },
}
_SP = {
    "NFeAutorizacao4": {
        1: "https://nfe.fazenda.sp.gov.br/ws/nfeautorizacao4.asmx",
        2: "https://homologacao.nfe.fazenda.sp.gov.br/ws/nfeautorizacao4.asmx",
    },
    "NFeRecepcaoEvento4": {
        1: "https://nfe.fazenda.sp.gov.br/ws/nferecepcaoevento4.asmx",
        2: "https://homologacao.nfe.fazenda.sp.gov.br/ws/nferecepcaoevento4.asmx",
    },
    "NFeConsultaProtocolo4": {
        1: "https://nfe.fazenda.sp.gov.br/ws/nfeconsultaprotocolo4.asmx",
        2: "https://homologacao.nfe.fazenda.sp.gov.br/ws/nfeconsultaprotocolo4.asmx",
    },
    "NFeInutilizacao4": {
        1: "https://nfe.fazenda.sp.gov.br/ws/nfeinutilizacao4.asmx",
        2: "https://homologacao.nfe.fazenda.sp.gov.br/ws/nfeinutilizacao4.asmx",
    },
}
# UFs atendidas por autorizadores proprios (demais usam SVRS)
SEFAZ_WS = {
    "SP": _SP, "RS": _SVRS, "PR": _SVRS, "MG": {
        "NFeAutorizacao4": {
            1: "https://nfe.fazenda.mg.gov.br/nfe2/services/NFeAutorizacao4",
            2: "https://hnfe.fazenda.mg.gov.br/nfe2/services/NFeAutorizacao4",
        }},
}


def get_ws_url(uf: str, ambiente: int, servico: str) -> str:
    uf = (uf or "SP").upper()
    reg = SEFAZ_WS.get(uf, _SVRS)
    servico_map = reg.get(servico) or _SVRS.get(servico, {})
    return servico_map.get(int(ambiente), "")


# ---- QR Code (consulta publica por chave de acesso) ----
QRCODE_BASE = {
    "SP": "https://www.nfe.fazenda.sp.gov.br/consultanfe/consulta/publica_view.aspx",
    "RS": "https://www.sefaz.rs.gov.br/NFE/NFE-COM.aspx",
    "PR": "https://www.fazenda.pr.gov.br/nfe/consulta",
    "MG": "https://nfe.fazenda.mg.gov.br/portalnfe/sistema/consultaarg.xhtml",
}
QRCODE_NACIONAL = "https://www.nfe.fazenda.gov.br/portal/consultaRecaptcha.aspx"


def build_qrcode_url(chave: str, uf: str) -> str:
    base = QRCODE_BASE.get((uf or "SP").upper(), QRCODE_NACIONAL)
    return f"{base}?chNFe={chave}&tpConteudo=XML"


def gerar_qrcode_png(url: str) -> bytes:
    import qrcode
    img = qrcode.make(url)
    bio = io.BytesIO()
    img.save(bio, format="PNG")
    return bio.getvalue()


def only_digits(v: str) -> str:
    return re.sub(r"\D", "", v or "")


def _mod11_dv(key43: str) -> str:
    weights = [2, 3, 4, 5, 6, 7, 8, 9]
    total = 0
    wi = 0
    for ch in reversed(key43):
        total += int(ch) * weights[wi % 8]
        wi += 1
    resto = total % 11
    dv = 0 if resto in (0, 1) else 11 - resto
    return str(dv)


def gerar_chave_acesso(uf: str, emissao: datetime, cnpj: str, modelo: str,
                       serie: int, numero: int, tp_emis: int, codigo_num: str) -> str:
    cuf = UF_CODES.get(uf.upper(), "35")
    aamm = emissao.strftime("%y%m")
    cnpj = only_digits(cnpj).rjust(14, "0")[:14]
    mod = str(modelo).rjust(2, "0")
    ser = str(serie).rjust(3, "0")
    num = str(numero).rjust(9, "0")
    cnf = only_digits(codigo_num).rjust(8, "0")[:8]
    tpemis = str(tp_emis)
    key43 = f"{cuf}{aamm}{cnpj}{mod}{ser}{num}{tpemis}{cnf}"
    return key43 + _mod11_dv(key43)


def calcular_item(prod: dict, quantidade: float, valor_unitario: float) -> dict:
    """Calcula impostos de um item. Retorna dict com valores."""
    base = round(quantidade * valor_unitario, 2)
    icms_aliq = float(prod.get("icms_aliquota", 0) or 0)
    ipi_aliq = float(prod.get("ipi_aliquota", 0) or 0)
    pis_aliq = float(prod.get("pis_aliquota", 0) or 0)
    cofins_aliq = float(prod.get("cofins_aliquota", 0) or 0)
    icms_v = round(base * icms_aliq / 100, 2)
    ipi_v = round(base * ipi_aliq / 100, 2)
    pis_v = round(base * pis_aliq / 100, 2)
    cofins_v = round(base * cofins_aliq / 100, 2)
    return {
        "valor_total": base,
        "icms_valor": icms_v,
        "ipi_valor": ipi_v,
        "pis_valor": pis_v,
        "cofins_valor": cofins_v,
    }


def calcular_totais(itens: list) -> dict:
    t = {"v_prod": 0.0, "v_icms": 0.0, "v_ipi": 0.0, "v_pis": 0.0,
         "v_cofins": 0.0, "v_desc": 0.0, "v_frete": 0.0, "v_nf": 0.0}
    for it in itens:
        t["v_prod"] += it.get("valor_total", 0)
        t["v_icms"] += it.get("icms_valor", 0)
        t["v_ipi"] += it.get("ipi_valor", 0)
        t["v_pis"] += it.get("pis_valor", 0)
        t["v_cofins"] += it.get("cofins_valor", 0)
    for k in t:
        t[k] = round(t[k], 2)
    t["v_nf"] = round(t["v_prod"] + t["v_ipi"] - t["v_desc"] + t["v_frete"], 2)
    return t


def _f(v) -> str:
    return f"{float(v or 0):.2f}"


def build_nfe_xml(company: dict, invoice: dict, chave: str, codigo_num: str,
                  emissao: datetime, tp_emis: int = 1, x_just: str = None) -> str:
    """Constroi o XML da NF-e (layout 4.00) - infNFe."""
    from lxml import etree
    ns = "http://www.portalfiscal.inf.br/nfe"
    E = lambda tag: etree.SubElement
    nfe = etree.Element("{%s}NFe" % ns, nsmap={None: ns})
    infNFe = etree.SubElement(nfe, "infNFe", Id="NFe" + chave, versao="4.00")

    end = company.get("endereco", {})
    sef = company.get("sefaz", {})
    uf = sef.get("uf", "SP")
    cuf = UF_CODES.get(uf.upper(), "35")

    ide = etree.SubElement(infNFe, "ide")
    for tag, val in [
        ("cUF", cuf), ("cNF", only_digits(codigo_num).rjust(8, "0")),
        ("natOp", invoice.get("natureza_operacao", "Venda")),
        ("mod", "55"), ("serie", str(invoice.get("serie", 1))),
        ("nNF", str(invoice.get("numero", 1))),
        ("dhEmi", emissao.strftime("%Y-%m-%dT%H:%M:%S-03:00")),
        ("tpNF", str(invoice.get("tipo_operacao", 1))),
        ("idDest", "1"), ("cMunFG", end.get("cod_municipio", "3550308")),
        ("tpImp", "1"), ("tpEmis", str(tp_emis)), ("cDV", chave[-1]),
        ("tpAmb", str(sef.get("ambiente", 2))),
        ("finNFe", str(invoice.get("finalidade", 1))),
        ("indFinal", "1"), ("indPres", "1"),
        ("procEmi", "0"), ("verProc", "NFeSystem1.0"),
    ]:
        etree.SubElement(ide, tag).text = str(val)

    if tp_emis in (6, 7) and x_just:
        etree.SubElement(ide, "dhCont").text = emissao.strftime("%Y-%m-%dT%H:%M:%S-03:00")
        etree.SubElement(ide, "xJust").text = x_just

    emit = etree.SubElement(infNFe, "emit")
    etree.SubElement(emit, "CNPJ").text = only_digits(company.get("cnpj", ""))
    etree.SubElement(emit, "xNome").text = company.get("razao_social", "")
    if company.get("nome_fantasia"):
        etree.SubElement(emit, "xFant").text = company.get("nome_fantasia")
    enderEmit = etree.SubElement(emit, "enderEmit")
    for tag, val in [
        ("xLgr", end.get("logradouro", "")), ("nro", end.get("numero", "")),
        ("xBairro", end.get("bairro", "")),
        ("cMun", end.get("cod_municipio", "3550308")),
        ("xMun", end.get("municipio", "")), ("UF", uf),
        ("CEP", only_digits(end.get("cep", ""))), ("cPais", "1058"),
        ("xPais", "BRASIL"),
    ]:
        etree.SubElement(enderEmit, tag).text = str(val)
    etree.SubElement(emit, "IE").text = only_digits(company.get("ie", ""))
    etree.SubElement(emit, "CRT").text = str(company.get("crt", 1))

    cli = invoice.get("cliente", {})
    cli_end = cli.get("endereco", {})
    dest = etree.SubElement(infNFe, "dest")
    doc = only_digits(cli.get("cpf_cnpj", ""))
    if len(doc) == 14:
        etree.SubElement(dest, "CNPJ").text = doc
    else:
        etree.SubElement(dest, "CPF").text = doc
    etree.SubElement(dest, "xNome").text = cli.get("nome", "")
    enderDest = etree.SubElement(dest, "enderDest")
    for tag, val in [
        ("xLgr", cli_end.get("logradouro", "")), ("nro", cli_end.get("numero", "")),
        ("xBairro", cli_end.get("bairro", "")),
        ("cMun", cli_end.get("cod_municipio", "3550308")),
        ("xMun", cli_end.get("municipio", "")), ("UF", cli_end.get("uf", uf)),
        ("CEP", only_digits(cli_end.get("cep", ""))), ("cPais", "1058"),
        ("xPais", "BRASIL"),
    ]:
        etree.SubElement(enderDest, tag).text = str(val)
    etree.SubElement(dest, "indIEDest").text = str(cli.get("indicador_ie", 9))

    for i, it in enumerate(invoice.get("itens", []), start=1):
        det = etree.SubElement(infNFe, "det", nItem=str(i))
        prod = etree.SubElement(det, "prod")
        for tag, val in [
            ("cProd", it.get("codigo", "")), ("cEAN", "SEM GTIN"),
            ("xProd", it.get("descricao", "")), ("NCM", it.get("ncm", "00000000")),
            ("CFOP", it.get("cfop", "5102")), ("uCom", it.get("unidade", "UN")),
            ("qCom", f"{it.get('quantidade', 1):.4f}"),
            ("vUnCom", f"{it.get('valor_unitario', 0):.4f}"),
            ("vProd", _f(it.get("valor_total"))), ("cEANTrib", "SEM GTIN"),
            ("uTrib", it.get("unidade", "UN")),
            ("qTrib", f"{it.get('quantidade', 1):.4f}"),
            ("vUnTrib", f"{it.get('valor_unitario', 0):.4f}"),
            ("indTot", "1"),
        ]:
            etree.SubElement(prod, tag).text = str(val)
        imposto = etree.SubElement(det, "imposto")
        icms = etree.SubElement(imposto, "ICMS")
        crt = int(company.get("crt", 1))
        if crt in (1, 2):
            icmssn = etree.SubElement(icms, "ICMSSN102")
            etree.SubElement(icmssn, "orig").text = it.get("origem", "0")
            etree.SubElement(icmssn, "CSOSN").text = it.get("cst_icms", "102")
        else:
            icms00 = etree.SubElement(icms, "ICMS00")
            etree.SubElement(icms00, "orig").text = it.get("origem", "0")
            etree.SubElement(icms00, "CST").text = "00"
            etree.SubElement(icms00, "modBC").text = "3"
            etree.SubElement(icms00, "vBC").text = _f(it.get("valor_total"))
            etree.SubElement(icms00, "pICMS").text = _f(it.get("icms_aliquota"))
            etree.SubElement(icms00, "vICMS").text = _f(it.get("icms_valor"))
        pis = etree.SubElement(imposto, "PIS")
        pisaliq = etree.SubElement(pis, "PISAliq")
        etree.SubElement(pisaliq, "CST").text = "01"
        etree.SubElement(pisaliq, "vBC").text = _f(it.get("valor_total"))
        etree.SubElement(pisaliq, "pPIS").text = _f(it.get("pis_aliquota"))
        etree.SubElement(pisaliq, "vPIS").text = _f(it.get("pis_valor"))
        cofins = etree.SubElement(imposto, "COFINS")
        cofinsaliq = etree.SubElement(cofins, "COFINSAliq")
        etree.SubElement(cofinsaliq, "CST").text = "01"
        etree.SubElement(cofinsaliq, "vBC").text = _f(it.get("valor_total"))
        etree.SubElement(cofinsaliq, "pCOFINS").text = _f(it.get("cofins_aliquota"))
        etree.SubElement(cofinsaliq, "vCOFINS").text = _f(it.get("cofins_valor"))

    tot = invoice.get("totais", {})
    total = etree.SubElement(infNFe, "total")
    icmstot = etree.SubElement(total, "ICMSTot")
    for tag, key in [
        ("vBC", "v_prod"), ("vICMS", "v_icms"), ("vICMSDeson", None),
        ("vFCP", None), ("vBCST", None), ("vST", None), ("vFCPST", None),
        ("vFCPSTRet", None), ("vProd", "v_prod"), ("vFrete", "v_frete"),
        ("vSeg", None), ("vDesc", "v_desc"), ("vII", None), ("vIPI", "v_ipi"),
        ("vIPIDevol", None), ("vPIS", "v_pis"), ("vCOFINS", "v_cofins"),
        ("vOutro", None), ("vNF", "v_nf"),
    ]:
        val = tot.get(key, 0) if key else 0
        etree.SubElement(icmstot, tag).text = _f(val)

    transp = etree.SubElement(infNFe, "transp")
    etree.SubElement(transp, "modFrete").text = "9"

    pag = etree.SubElement(infNFe, "pag")
    detpag = etree.SubElement(pag, "detPag")
    etree.SubElement(detpag, "tPag").text = "01"
    etree.SubElement(detpag, "vPag").text = _f(tot.get("v_nf", 0))

    if invoice.get("info_adicional"):
        infad = etree.SubElement(infNFe, "infAdic")
        etree.SubElement(infad, "infCpl").text = invoice.get("info_adicional")

    return etree.tostring(nfe, encoding="unicode")


def assinar_xml(xml_str: str, pfx_bytes: bytes, senha: str) -> str:
    """Assina digitalmente o XML com certificado A1 (.pfx). Requer certificado real."""
    from lxml import etree
    from signxml import XMLSigner, methods
    from cryptography.hazmat.primitives.serialization import pkcs12, Encoding, PrivateFormat, NoEncryption
    key, cert, _ = pkcs12.load_key_and_certificates(pfx_bytes, senha.encode())
    key_pem = key.private_bytes(Encoding.PEM, PrivateFormat.PKCS8, NoEncryption())
    cert_pem = cert.public_bytes(Encoding.PEM)
    root = etree.fromstring(xml_str.encode())
    signed_el = root.find(".//*[@Id]")
    if signed_el is None:
        signed_el = root
    ref_uri = "#" + signed_el.get("Id")
    signer = XMLSigner(method=methods.enveloped, signature_algorithm="rsa-sha1",
                       digest_algorithm="sha1", c14n_algorithm="http://www.w3.org/TR/2001/REC-xml-c14n-20010315")
    signed = signer.sign(root, key=key_pem, cert=cert_pem, reference_uri=ref_uri)
    return etree.tostring(signed, encoding="unicode")


def gerar_danfe_pdf(company: dict, invoice: dict, logo_bytes: bytes = None) -> bytes:
    """Gera o DANFE no layout oficial (modelo 55, retrato)."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.lib import colors
    from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table,
                                    TableStyle, Image as RLImage)
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.enums import TA_CENTER
    from reportlab.graphics.barcode import code128

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=7 * mm, bottomMargin=7 * mm,
                            leftMargin=12 * mm, rightMargin=12 * mm)
    lbl = ParagraphStyle("lbl", fontName="Helvetica", fontSize=5,
                         textColor=colors.HexColor("#444444"), leading=6)
    val = ParagraphStyle("val", fontName="Helvetica", fontSize=8, leading=9)
    tiny = ParagraphStyle("tiny", fontName="Helvetica", fontSize=6, leading=7)
    cen = ParagraphStyle("cen", fontName="Helvetica-Bold", fontSize=9,
                         alignment=TA_CENTER, leading=10)
    cenb = ParagraphStyle("cenb", fontName="Helvetica-Bold", fontSize=7,
                          alignment=TA_CENTER, leading=8)
    right = ParagraphStyle("right", fontName="Helvetica", fontSize=8, leading=9,
                           alignment=2)

    grid = TableStyle([("BOX", (0, 0), (-1, -1), 0.6, colors.black),
                       ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.black),
                       ("VALIGN", (0, 0), (-1, -1), "TOP"),
                       ("TOPPADDING", (0, 0), (-1, -1), 1),
                       ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                       ("LEFTPADDING", (0, 0), (-1, -1), 3)])

    def F(label, value, style=val):
        v = value if value not in (None, "") else "\u00a0"
        return [Paragraph(label, lbl), Paragraph(str(v), style)]

    story = []
    end = company.get("endereco", {})
    sef = company.get("sefaz", {})
    uf = sef.get("uf", "SP")
    chave = invoice.get("chave_acesso", "")
    cli = invoice.get("cliente", {})
    cli_end = cli.get("endereco", {})
    tot = invoice.get("totais", {})
    numero = f"{invoice.get('numero', 0):09d}"
    serie = f"{invoice.get('serie', 1):03d}"
    status = invoice.get("status", "rascunho").upper()

    if status not in ("AUTORIZADA",):
        story.append(Paragraph(f"SEM VALOR FISCAL - {status}",
                     ParagraphStyle("wm", fontName="Helvetica-Bold", fontSize=9,
                                    textColor=colors.HexColor("#B91C1C"), alignment=TA_CENTER)))
        story.append(Spacer(1, 2))

    # ---------- Canhoto ----------
    canhoto_txt = Paragraph(
        f"RECEBEMOS DE <b>{company.get('razao_social','')}</b> OS PRODUTOS / SERVICOS "
        f"CONSTANTES DA NOTA FISCAL ELETRONICA INDICADA AO LADO", tiny)
    sub = Table([[Paragraph("DATA DE RECEBIMENTO", lbl),
                  Paragraph("IDENTIFICACAO E ASSINATURA DO RECEBEDOR", lbl)]],
                colWidths=[38 * mm, 108 * mm])
    sub.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.4, colors.black),
                             ("TOPPADDING", (0, 0), (-1, -1), 10),
                             ("LEFTPADDING", (0, 0), (-1, -1), 3)]))
    left_block = Table([[canhoto_txt], [sub]], colWidths=[146 * mm])
    left_block.setStyle(TableStyle([("TOPPADDING", (0, 0), (-1, -1), 2),
                                    ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                                    ("LEFTPADDING", (0, 0), (-1, -1), 3)]))
    right_block = Paragraph(f"<b>NF-e</b><br/><br/>N&ordm; {numero}<br/>SERIE {serie}", cen)
    canhoto = Table([[left_block, right_block]], colWidths=[146 * mm, 40 * mm])
    canhoto.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 0.6, colors.black),
                                 ("LINEAFTER", (0, 0), (0, 0), 0.6, colors.black),
                                 ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                                 ("ALIGN", (1, 0), (1, 0), "CENTER")]))
    story.append(canhoto)
    story.append(Spacer(1, 4))

    # ---------- Cabecalho (emitente | DANFE | chave) ----------
    logo_img = Paragraph("", val)
    if logo_bytes:
        try:
            logo_img = RLImage(io.BytesIO(logo_bytes), width=22 * mm, height=15 * mm, kind="proportional")
        except Exception:
            logo_img = Paragraph("", val)
    emit_info = Paragraph(
        f"<b>{company.get('razao_social','')}</b><br/>"
        f"{end.get('logradouro','')}, {end.get('numero','')}<br/>"
        f"{end.get('bairro','')} - {end.get('municipio','')}/{uf}<br/>"
        f"CEP: {end.get('cep','')} &nbsp; Fone: {end.get('fone','')}", tiny)
    emit_cell = Table([[logo_img, emit_info]], colWidths=[24 * mm, 62 * mm])
    emit_cell.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                                   ("LEFTPADDING", (0, 0), (-1, -1), 2)]))

    tipo_box = Table([[Paragraph("0-ENTRADA<br/>1-SAIDA", tiny),
                       Paragraph(f"<b>{invoice.get('tipo_operacao',1)}</b>", cen)]],
                     colWidths=[26 * mm, 10 * mm])
    tipo_box.setStyle(TableStyle([("BOX", (1, 0), (1, 0), 0.4, colors.black),
                                  ("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
    danfe_cell = Table([
        [Paragraph("DANFE", cen)],
        [Paragraph("Documento Auxiliar da<br/>Nota Fiscal Eletronica",
                   ParagraphStyle("c2", fontSize=5, alignment=TA_CENTER, leading=6))],
        [tipo_box],
        [Paragraph(f"N&ordm; {numero}", cenb)],
        [Paragraph(f"SERIE {serie}", cenb)],
        [Paragraph("FOLHA 1/1", ParagraphStyle("c3", fontSize=6, alignment=TA_CENTER))],
    ], colWidths=[40 * mm])
    danfe_cell.setStyle(TableStyle([("TOPPADDING", (0, 0), (-1, -1), 1),
                                    ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
                                    ("ALIGN", (0, 0), (-1, -1), "CENTER")]))

    bc = Paragraph("", val)
    if chave:
        try:
            bc = code128.Code128(chave, barHeight=11 * mm, barWidth=0.22 * mm)
        except Exception:
            bc = Paragraph("", val)
    chave_fmt = " ".join(re.findall("....", chave)) if chave else ""
    key_cell = Table([
        [bc],
        [Paragraph("CHAVE DE ACESSO", lbl)],
        [Paragraph(chave_fmt, ParagraphStyle("k", fontName="Helvetica-Bold",
                   fontSize=6, alignment=TA_CENTER, leading=7))],
        [Paragraph("Consulta de autenticidade no portal nacional da NF-e "
                   "www.nfe.fazenda.gov.br/portal ou no site da Sefaz Autorizadora",
                   ParagraphStyle("k2", fontSize=5, alignment=TA_CENTER, leading=6))],
    ], colWidths=[60 * mm])
    key_cell.setStyle(TableStyle([("ALIGN", (0, 0), (-1, -1), "CENTER"),
                                  ("TOPPADDING", (0, 0), (-1, -1), 2)]))

    header = Table([[emit_cell, danfe_cell, key_cell]], colWidths=[86 * mm, 40 * mm, 60 * mm])
    header.setStyle(grid)
    story.append(header)

    prot = f"{invoice.get('nprot') or invoice.get('protocolo','')}"
    if prot and invoice.get("data_emissao"):
        prot += " - " + invoice["data_emissao"][:19].replace("T", " ")
    nat = Table([[F("NATUREZA DA OPERACAO", invoice.get("natureza_operacao", "")),
                  F("PROTOCOLO DE AUTORIZACAO DE USO", prot)]], colWidths=[112 * mm, 74 * mm])
    nat.setStyle(grid)
    story.append(nat)
    ie_row = Table([[F("INSCRICAO ESTADUAL", company.get("ie", "")),
                     F("INSC.EST.SUBST.TRIB.", company.get("im", "")),
                     F("CNPJ", company.get("cnpj", ""))]],
                   colWidths=[62 * mm, 62 * mm, 62 * mm])
    ie_row.setStyle(grid)
    story.append(ie_row)
    story.append(Spacer(1, 3))

    # ---------- Destinatario ----------
    story.append(Paragraph("DESTINATARIO / REMETENTE", lbl))
    d1 = Table([[F("NOME / RAZAO SOCIAL", cli.get("nome", "")),
                 F("CNPJ / CPF", cli.get("cpf_cnpj", "")),
                 F("DATA DA EMISSAO", (invoice.get("data_emissao", "") or "")[:10])]],
               colWidths=[110 * mm, 46 * mm, 30 * mm])
    d2 = Table([[F("ENDERECO", f"{cli_end.get('logradouro','')}, {cli_end.get('numero','')}"),
                 F("BAIRRO", cli_end.get("bairro", "")),
                 F("CEP", cli_end.get("cep", ""))]],
               colWidths=[110 * mm, 46 * mm, 30 * mm])
    d3 = Table([[F("MUNICIPIO", cli_end.get("municipio", "")),
                 F("UF", cli_end.get("uf", "")),
                 F("INSCRICAO ESTADUAL", cli.get("ie", "")),
                 F("FONE / FAX", cli.get("fone", ""))]],
               colWidths=[80 * mm, 14 * mm, 52 * mm, 40 * mm])
    for tb in (d1, d2, d3):
        tb.setStyle(grid)
        story.append(tb)
    story.append(Spacer(1, 3))

    # ---------- Calculo do imposto ----------
    story.append(Paragraph("CALCULO DO IMPOSTO", lbl))
    c1 = Table([[F("BASE DE CALCULO DO ICMS", _f(tot.get("v_prod")), right),
                 F("VALOR DO ICMS", _f(tot.get("v_icms")), right),
                 F("BASE CALC. ICMS ST", _f(0), right),
                 F("VALOR DO ICMS ST", _f(0), right),
                 F("VALOR TOTAL DOS PRODUTOS", _f(tot.get("v_prod")), right)]],
               colWidths=[40 * mm, 34 * mm, 36 * mm, 34 * mm, 42 * mm])
    c2 = Table([[F("VALOR DO FRETE", _f(tot.get("v_frete")), right),
                 F("VALOR DO SEGURO", _f(0), right),
                 F("DESCONTO", _f(tot.get("v_desc")), right),
                 F("OUTRAS DESPESAS", _f(0), right),
                 F("VALOR TOTAL DO IPI", _f(tot.get("v_ipi")), right),
                 F("VALOR TOTAL DA NOTA", _f(tot.get("v_nf")), right)]],
               colWidths=[30 * mm, 30 * mm, 28 * mm, 30 * mm, 30 * mm, 38 * mm])
    for tb in (c1, c2):
        tb.setStyle(grid)
        story.append(tb)
    story.append(Spacer(1, 3))

    # ---------- Transportador ----------
    story.append(Paragraph("TRANSPORTADOR / VOLUMES TRANSPORTADOS", lbl))
    tr = Table([[F("FRETE POR CONTA", "9-Sem Frete"), F("PLACA DO VEICULO", ""),
                 F("UF", ""), F("CNPJ / CPF", "")]],
               colWidths=[46 * mm, 50 * mm, 20 * mm, 70 * mm])
    tr.setStyle(grid)
    story.append(tr)
    story.append(Spacer(1, 3))

    # ---------- Produtos ----------
    story.append(Paragraph("DADOS DOS PRODUTOS / SERVICOS", lbl))
    head_style = ParagraphStyle("hd", fontName="Helvetica-Bold", fontSize=5,
                                alignment=TA_CENTER, leading=6, textColor=colors.white)
    cols = ["COD", "DESCRICAO DO PRODUTO / SERVICO", "NCM/SH", "CST", "CFOP", "UN",
            "QUANT", "V.UNIT", "V.TOTAL", "BC ICMS", "V.ICMS", "V.IPI", "%ICMS", "%IPI"]
    rows = [[Paragraph(c, head_style) for c in cols]]
    it_style = ParagraphStyle("its", fontName="Helvetica", fontSize=5, leading=6)
    it_r = ParagraphStyle("itr", fontName="Helvetica", fontSize=5, leading=6, alignment=2)
    for it in invoice.get("itens", []):
        cst = f"{it.get('origem','0')}{it.get('cst_icms','')}"
        rows.append([
            Paragraph(it.get("codigo", ""), it_style),
            Paragraph(it.get("descricao", ""), it_style),
            Paragraph(it.get("ncm", ""), it_style),
            Paragraph(cst, it_style),
            Paragraph(it.get("cfop", ""), it_style),
            Paragraph(it.get("unidade", ""), it_style),
            Paragraph(f"{it.get('quantidade',0):.2f}", it_r),
            Paragraph(f"{it.get('valor_unitario',0):.2f}", it_r),
            Paragraph(_f(it.get("valor_total")), it_r),
            Paragraph(_f(it.get("valor_total")), it_r),
            Paragraph(_f(it.get("icms_valor")), it_r),
            Paragraph(_f(it.get("ipi_valor")), it_r),
            Paragraph(f"{it.get('icms_aliquota',0):.1f}", it_r),
            Paragraph(f"{it.get('ipi_aliquota',0):.1f}", it_r),
        ])
    widths = [12, 33, 12, 9, 9, 7, 13, 14, 14, 13, 12, 11, 9, 9]
    it_table = Table(rows, colWidths=[w * mm for w in widths], repeatRows=1)
    it_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1E293B")),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.black),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 1),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
        ("LEFTPADDING", (0, 0), (-1, -1), 2),
        ("RIGHTPADDING", (0, 0), (-1, -1), 2),
    ]))
    story.append(it_table)
    story.append(Spacer(1, 3))

    # ---------- Dados adicionais + Reservado ao Fisco ----------
    story.append(Paragraph("DADOS ADICIONAIS", lbl))
    add = Table([[Paragraph(invoice.get("info_adicional", "") or "\u00a0", tiny),
                  Paragraph("RESERVADO AO FISCO", lbl)]],
                colWidths=[126 * mm, 60 * mm], rowHeights=[22 * mm])
    add.setStyle(grid)
    story.append(add)

    doc.build(story)
    return buf.getvalue()


# ============ SEFAZ transmission (NFe 4.00) ============
def _pfx_to_pem_files(pfx_bytes: bytes, senha: str):
    import tempfile
    from cryptography.hazmat.primitives.serialization import (
        pkcs12, Encoding, PrivateFormat, NoEncryption)
    key, cert, _ = pkcs12.load_key_and_certificates(pfx_bytes, senha.encode())
    certf = tempfile.NamedTemporaryFile(delete=False, suffix=".pem")
    keyf = tempfile.NamedTemporaryFile(delete=False, suffix=".pem")
    certf.write(cert.public_bytes(Encoding.PEM)); certf.close()
    keyf.write(key.private_bytes(Encoding.PEM, PrivateFormat.TraditionalOpenSSL,
                                 NoEncryption())); keyf.close()
    return certf.name, keyf.name


def _strip_decl(xml: str) -> str:
    xml = xml.strip()
    if xml.startswith("<?xml"):
        xml = xml[xml.find("?>") + 2:].strip()
    return xml


def _find_text(root, tag: str) -> str:
    els = root.findall(".//{*}" + tag)
    return els[0].text if els and els[0].text else ""


def transmitir_sefaz(signed_nfe_xml: str, company: dict, pfx_bytes: bytes,
                     senha: str, url_override: str = None) -> dict:
    """Transmite a NF-e assinada ao webservice NFeAutorizacao4 da UF (modo sincrono).
    Retorna dict com status, protocolo, nprot, motivo e xml_proc."""
    import os as _os
    import requests
    import urllib3
    urllib3.disable_warnings()
    from lxml import etree

    sef = company.get("sefaz", {})
    uf = sef.get("uf", "SP")
    amb = int(sef.get("ambiente", 2))
    url = url_override or get_ws_url(uf, amb, "NFeAutorizacao4")
    if not url:
        return {"status": "rejeitada", "protocolo": "", "nprot": "",
                "motivo": f"UF {uf} sem endpoint de autorizacao configurado.",
                "xml_proc": signed_nfe_xml}

    nfe = _strip_decl(signed_nfe_xml)
    envi = ('<enviNFe versao="4.00" xmlns="http://www.portalfiscal.inf.br/nfe">'
            f'<idLote>1</idLote><indSinc>1</indSinc>{nfe}</enviNFe>')
    soap = ('<?xml version="1.0" encoding="UTF-8"?>'
            '<soap12:Envelope xmlns:soap12="http://www.w3.org/2003/05/soap-envelope">'
            '<soap12:Body>'
            '<nfeDadosMsg xmlns="http://www.portalfiscal.inf.br/nfe/wsdl/NFeAutorizacao4">'
            f'{envi}</nfeDadosMsg></soap12:Body></soap12:Envelope>')

    certfile, keyfile = _pfx_to_pem_files(pfx_bytes, senha)
    try:
        r = requests.post(url, data=soap.encode("utf-8"),
                          headers={"Content-Type": "application/soap+xml; charset=utf-8"},
                          cert=(certfile, keyfile), verify=False, timeout=60)
        root = etree.fromstring(r.content, parser=etree.XMLParser(recover=True))
        protnfe = root.findall(".//{*}protNFe")
        if protnfe:
            inf = protnfe[0]
            cstat = _find_text(inf, "cStat")
            xmot = _find_text(inf, "xMotivo")
            nprot = _find_text(inf, "nProt")
            status = "autorizada" if cstat in ("100", "150") else "rejeitada"
            xml_proc = (f'<nfeProc versao="4.00" xmlns="http://www.portalfiscal.inf.br/nfe">'
                        f'{nfe}{etree.tostring(inf, encoding="unicode")}</nfeProc>')
            return {"status": status, "protocolo": nprot, "nprot": nprot,
                    "motivo": f"[{cstat}] {xmot}", "xml_proc": xml_proc}
        cstat = _find_text(root, "cStat")
        xmot = _find_text(root, "xMotivo")
        return {"status": "rejeitada", "protocolo": "", "nprot": "",
                "motivo": f"[{cstat}] {xmot}" if cstat else "Resposta invalida do SEFAZ.",
                "xml_proc": signed_nfe_xml}
    except Exception as e:
        return {"status": "rejeitada", "protocolo": "", "nprot": "",
                "motivo": f"Falha na comunicacao com o SEFAZ: {e}",
                "xml_proc": signed_nfe_xml}
    finally:
        for f in (certfile, keyfile):
            try: _os.unlink(f)
            except Exception: pass


COND_USO_CCE = ("A Carta de Correcao e disciplinada pelo paragrafo 1o-A do art. 7o "
                "do Convenio S/N, de 15 de dezembro de 1970 e pode ser utilizada para "
                "regularizacao de erro ocorrido na emissao de documento fiscal, desde que "
                "o erro nao esteja relacionado com: I - as variaveis que determinam o valor "
                "do imposto tais como: base de calculo, aliquota, diferenca de preco, "
                "quantidade, valor da operacao ou da prestacao; II - a correcao de dados "
                "cadastrais que implique mudanca do remetente ou do destinatario; "
                "III - a data de emissao ou de saida.")


def build_evento_cce(company: dict, chave: str, seq: int, texto: str) -> str:
    """Constroi o XML do evento Carta de Correcao (tpEvento 110110)."""
    from lxml import etree
    ns = "http://www.portalfiscal.inf.br/nfe"
    sef = company.get("sefaz", {})
    uf = sef.get("uf", "SP")
    cuf = UF_CODES.get(uf.upper(), "35")
    amb = str(sef.get("ambiente", 2))
    dh = (datetime.now(timezone.utc) - timedelta(hours=3)).strftime("%Y-%m-%dT%H:%M:%S-03:00")
    tp_evento = "110110"
    n_seq = str(seq)
    ev_id = f"ID{tp_evento}{chave}{n_seq.zfill(2)}"

    evento = etree.Element("{%s}evento" % ns, nsmap={None: ns}, versao="1.00")
    inf = etree.SubElement(evento, "infEvento", Id=ev_id)
    etree.SubElement(inf, "cOrgao").text = cuf
    etree.SubElement(inf, "tpAmb").text = amb
    etree.SubElement(inf, "CNPJ").text = only_digits(company.get("cnpj", ""))
    etree.SubElement(inf, "chNFe").text = chave
    etree.SubElement(inf, "dhEvento").text = dh
    etree.SubElement(inf, "tpEvento").text = tp_evento
    etree.SubElement(inf, "nSeqEvento").text = n_seq
    etree.SubElement(inf, "verEvento").text = "1.00"
    det = etree.SubElement(inf, "detEvento", versao="1.00")
    etree.SubElement(det, "descEvento").text = "Carta de Correcao"
    etree.SubElement(det, "xCorrecao").text = texto
    etree.SubElement(det, "xCondUso").text = COND_USO_CCE
    return etree.tostring(evento, encoding="unicode")


def transmitir_evento(signed_evento_xml: str, company: dict, pfx_bytes: bytes,
                      senha: str) -> dict:
    """Transmite um evento (ex.: CC-e) ao webservice NFeRecepcaoEvento4."""
    import os as _os
    import requests
    import urllib3
    urllib3.disable_warnings()
    from lxml import etree

    sef = company.get("sefaz", {})
    uf = sef.get("uf", "SP")
    amb = int(sef.get("ambiente", 2))
    url = get_ws_url(uf, amb, "NFeRecepcaoEvento4")
    if not url:
        return {"status": "rejeitada", "protocolo": "",
                "motivo": f"UF {uf} sem endpoint de eventos configurado."}
    ev = _strip_decl(signed_evento_xml)
    env = ('<envEvento versao="1.00" xmlns="http://www.portalfiscal.inf.br/nfe">'
           f'<idLote>1</idLote>{ev}</envEvento>')
    soap = ('<?xml version="1.0" encoding="UTF-8"?>'
            '<soap12:Envelope xmlns:soap12="http://www.w3.org/2003/05/soap-envelope">'
            '<soap12:Body>'
            '<nfeDadosMsg xmlns="http://www.portalfiscal.inf.br/nfe/wsdl/NFeRecepcaoEvento4">'
            f'{env}</nfeDadosMsg></soap12:Body></soap12:Envelope>')
    certfile, keyfile = _pfx_to_pem_files(pfx_bytes, senha)
    try:
        r = requests.post(url, data=soap.encode("utf-8"),
                          headers={"Content-Type": "application/soap+xml; charset=utf-8"},
                          cert=(certfile, keyfile), verify=False, timeout=60)
        root = etree.fromstring(r.content, parser=etree.XMLParser(recover=True))
        ret = root.findall(".//{*}retEvento")
        node = ret[0] if ret else root
        cstat = _find_text(node, "cStat")
        xmot = _find_text(node, "xMotivo")
        nprot = _find_text(node, "nProt")
        status = "registrado" if cstat in ("135", "136", "155") else "rejeitado"
        return {"status": status, "protocolo": nprot, "motivo": f"[{cstat}] {xmot}"}
    except Exception as e:
        return {"status": "rejeitado", "protocolo": "",
                "motivo": f"Falha na comunicacao com o SEFAZ: {e}"}
    finally:
        for f in (certfile, keyfile):
            try: _os.unlink(f)
            except Exception: pass


# ============ Consulta de situacao (NFeConsultaProtocolo4) ============
def consultar_protocolo(chave: str, company: dict, pfx_bytes: bytes, senha: str) -> dict:
    import os as _os
    import requests
    import urllib3
    urllib3.disable_warnings()
    from lxml import etree

    sef = company.get("sefaz", {})
    uf = sef.get("uf", "SP")
    amb = int(sef.get("ambiente", 2))
    url = get_ws_url(uf, amb, "NFeConsultaProtocolo4")
    if not url:
        return {"status": None, "protocolo": "", "nprot": "",
                "motivo": f"UF {uf} sem endpoint de consulta configurado."}
    cons = ('<consSitNFe versao="4.00" xmlns="http://www.portalfiscal.inf.br/nfe">'
            f'<tpAmb>{amb}</tpAmb><xServ>CONSULTAR</xServ><chNFe>{chave}</chNFe></consSitNFe>')
    soap = ('<?xml version="1.0" encoding="UTF-8"?>'
            '<soap12:Envelope xmlns:soap12="http://www.w3.org/2003/05/soap-envelope">'
            '<soap12:Body>'
            '<nfeDadosMsg xmlns="http://www.portalfiscal.inf.br/nfe/wsdl/NFeConsultaProtocolo4">'
            f'{cons}</nfeDadosMsg></soap12:Body></soap12:Envelope>')
    certfile, keyfile = _pfx_to_pem_files(pfx_bytes, senha)
    try:
        r = requests.post(url, data=soap.encode("utf-8"),
                          headers={"Content-Type": "application/soap+xml; charset=utf-8"},
                          cert=(certfile, keyfile), verify=False, timeout=60)
        root = etree.fromstring(r.content, parser=etree.XMLParser(recover=True))
        protnfe = root.findall(".//{*}protNFe")
        if protnfe:
            inf = protnfe[0]
            cstat = _find_text(inf, "cStat")
            xmot = _find_text(inf, "xMotivo")
            nprot = _find_text(inf, "nProt")
        else:
            cstat = _find_text(root, "cStat")
            xmot = _find_text(root, "xMotivo")
            nprot = ""
        if cstat == "100":
            status = "autorizada"
        elif cstat in ("101", "151", "135", "155"):
            status = "cancelada"
        elif cstat in ("110", "301", "302", "303"):
            status = "rejeitada"
        else:
            status = None  # ainda em processamento / nao consta
        return {"status": status, "protocolo": nprot, "nprot": nprot,
                "motivo": f"[{cstat}] {xmot}"}
    except Exception as e:
        return {"status": None, "protocolo": "", "nprot": "",
                "motivo": f"Falha na comunicacao com o SEFAZ: {e}"}
    finally:
        for f in (certfile, keyfile):
            try: _os.unlink(f)
            except Exception: pass


# ============ Evento de Cancelamento (110111) ============
def build_evento_cancelamento(company: dict, chave: str, nprot: str,
                              justificativa: str, seq: int = 1) -> str:
    from lxml import etree
    ns = "http://www.portalfiscal.inf.br/nfe"
    sef = company.get("sefaz", {})
    cuf = UF_CODES.get(sef.get("uf", "SP").upper(), "35")
    amb = str(sef.get("ambiente", 2))
    dh = (datetime.now(timezone.utc) - timedelta(hours=3)).strftime("%Y-%m-%dT%H:%M:%S-03:00")
    tp_evento = "110111"
    n_seq = str(seq)
    ev_id = f"ID{tp_evento}{chave}{n_seq.zfill(2)}"
    evento = etree.Element("{%s}evento" % ns, nsmap={None: ns}, versao="1.00")
    inf = etree.SubElement(evento, "infEvento", Id=ev_id)
    etree.SubElement(inf, "cOrgao").text = cuf
    etree.SubElement(inf, "tpAmb").text = amb
    etree.SubElement(inf, "CNPJ").text = only_digits(company.get("cnpj", ""))
    etree.SubElement(inf, "chNFe").text = chave
    etree.SubElement(inf, "dhEvento").text = dh
    etree.SubElement(inf, "tpEvento").text = tp_evento
    etree.SubElement(inf, "nSeqEvento").text = n_seq
    etree.SubElement(inf, "verEvento").text = "1.00"
    det = etree.SubElement(inf, "detEvento", versao="1.00")
    etree.SubElement(det, "descEvento").text = "Cancelamento"
    etree.SubElement(det, "nProt").text = nprot
    etree.SubElement(det, "xJust").text = justificativa
    return etree.tostring(evento, encoding="unicode")


# ============ Inutilizacao de numeracao (NFeInutilizacao4) ============
def build_inutilizacao_xml(company: dict, ano: str, serie: int, ini: int,
                           fim: int, justificativa: str) -> str:
    from lxml import etree
    ns = "http://www.portalfiscal.inf.br/nfe"
    sef = company.get("sefaz", {})
    cuf = UF_CODES.get(sef.get("uf", "SP").upper(), "35")
    amb = str(sef.get("ambiente", 2))
    cnpj = only_digits(company.get("cnpj", "")).rjust(14, "0")
    ser = str(serie).zfill(3)
    ini_s = str(ini).zfill(9)
    fim_s = str(fim).zfill(9)
    ano2 = ano[-2:]
    inut_id = f"ID{cuf}{ano2}{cnpj}55{ser}{ini_s}{fim_s}"
    inut = etree.Element("{%s}inutNFe" % ns, nsmap={None: ns}, versao="4.00")
    inf = etree.SubElement(inut, "infInut", Id=inut_id)
    for tag, val in [("tpAmb", amb), ("xServ", "INUTILIZAR"), ("cUF", cuf),
                     ("ano", ano2), ("CNPJ", cnpj), ("mod", "55"), ("serie", str(serie)),
                     ("nNFIni", str(ini)), ("nNFFin", str(fim)), ("xJust", justificativa)]:
        etree.SubElement(inf, tag).text = val
    return etree.tostring(inut, encoding="unicode")


def transmitir_inutilizacao(signed_xml: str, company: dict, pfx_bytes: bytes,
                            senha: str) -> dict:
    import os as _os
    import requests
    import urllib3
    urllib3.disable_warnings()
    from lxml import etree

    sef = company.get("sefaz", {})
    uf = sef.get("uf", "SP")
    amb = int(sef.get("ambiente", 2))
    url = get_ws_url(uf, amb, "NFeInutilizacao4")
    if not url:
        return {"status": "rejeitada", "protocolo": "",
                "motivo": f"UF {uf} sem endpoint de inutilizacao configurado."}
    msg = _strip_decl(signed_xml)
    soap = ('<?xml version="1.0" encoding="UTF-8"?>'
            '<soap12:Envelope xmlns:soap12="http://www.w3.org/2003/05/soap-envelope">'
            '<soap12:Body>'
            '<nfeDadosMsg xmlns="http://www.portalfiscal.inf.br/nfe/wsdl/NFeInutilizacao4">'
            f'{msg}</nfeDadosMsg></soap12:Body></soap12:Envelope>')
    certfile, keyfile = _pfx_to_pem_files(pfx_bytes, senha)
    try:
        r = requests.post(url, data=soap.encode("utf-8"),
                          headers={"Content-Type": "application/soap+xml; charset=utf-8"},
                          cert=(certfile, keyfile), verify=False, timeout=60)
        root = etree.fromstring(r.content, parser=etree.XMLParser(recover=True))
        cstat = _find_text(root, "cStat")
        xmot = _find_text(root, "xMotivo")
        nprot = _find_text(root, "nProt")
        status = "inutilizada" if cstat in ("102",) else "rejeitada"
        return {"status": status, "protocolo": nprot, "motivo": f"[{cstat}] {xmot}"}
    except Exception as e:
        return {"status": "rejeitada", "protocolo": "",
                "motivo": f"Falha na comunicacao com o SEFAZ: {e}"}
    finally:
        for f in (certfile, keyfile):
            try: _os.unlink(f)
            except Exception: pass


# ============ Relatorio fiscal em PDF ============
def gerar_relatorio_pdf(company: dict, data: dict, start: str, end: str) -> bytes:
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.units import mm
    from reportlab.lib import colors
    from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle)
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(A4), topMargin=14 * mm,
                            bottomMargin=14 * mm, leftMargin=12 * mm, rightMargin=12 * mm)
    styles = getSampleStyleSheet()
    small = ParagraphStyle("small", parent=styles["Normal"], fontSize=7, leading=9)
    label = ParagraphStyle("label", parent=styles["Normal"], fontSize=7,
                           textColor=colors.HexColor("#64748B"))
    h = ParagraphStyle("h", parent=styles["Normal"], fontSize=14, fontName="Helvetica-Bold")
    story = []
    story.append(Paragraph("Relatorio Fiscal de NF-e", h))
    story.append(Paragraph(f"{company.get('razao_social','')} - CNPJ {company.get('cnpj','')}", small))
    story.append(Paragraph(f"Periodo: {start or 'inicio'} a {end or 'hoje'}", label))
    story.append(Spacer(1, 8))

    t = data.get("totais", {})
    tot_tbl = Table([
        ["Notas", "Faturadas", "Produtos", "ICMS", "IPI", "PIS", "COFINS", "Total NF"],
        [str(data.get("count", 0)), str(data.get("faturadas", 0)),
         _f(t.get("v_prod")), _f(t.get("v_icms")), _f(t.get("v_ipi")),
         _f(t.get("v_pis")), _f(t.get("v_cofins")), _f(t.get("v_nf"))],
    ], colWidths=[30 * mm] * 8)
    tot_tbl.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F172A")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#CBD5E1")),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("BACKGROUND", (7, 1), (7, 1), colors.HexColor("#DBEAFE")),
        ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(tot_tbl)
    story.append(Spacer(1, 10))

    rows = [["Num", "Serie", "Data", "Cliente", "Status", "ICMS", "IPI", "PIS", "COFINS", "Total"]]
    for n in data.get("notas", []):
        nt = n.get("totais", {})
        rows.append([str(n.get("numero", "")), str(n.get("serie", "")),
                     (n.get("data_emissao", "") or "")[:10],
                     Paragraph(n.get("cliente", {}).get("nome", ""), small),
                     n.get("status", ""), _f(nt.get("v_icms")), _f(nt.get("v_ipi")),
                     _f(nt.get("v_pis")), _f(nt.get("v_cofins")), _f(nt.get("v_nf"))])
    tbl = Table(rows, colWidths=[16 * mm, 12 * mm, 20 * mm, 70 * mm, 24 * mm,
                                 20 * mm, 20 * mm, 20 * mm, 20 * mm, 24 * mm])
    tbl.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 7),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1E293B")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#CBD5E1")),
        ("ALIGN", (5, 1), (-1, -1), "RIGHT"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
        ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(tbl)
    doc.build(story)
    return buf.getvalue()


# ============ Contingencia (SVC) ============
SVC_RS_UFS = {"AC", "AL", "AP", "DF", "ES", "MG", "PB", "PR", "RJ", "RN",
              "RO", "RR", "RS", "SC", "SE", "SP", "TO"}


def svc_for_uf(uf: str):
    """Retorna (nome_svc, tp_emis) de contingencia para a UF."""
    if (uf or "SP").upper() in SVC_RS_UFS:
        return ("SVC-RS", 7)
    return ("SVC-AN", 6)


def get_svc_url(uf: str, ambiente: int) -> str:
    svc, _ = svc_for_uf(uf)
    amb = int(ambiente)
    if svc == "SVC-RS":
        return ("https://nfe.svrs.rs.gov.br/ws/NfeAutorizacao/NFeAutorizacao4.asmx"
                if amb == 1 else
                "https://nfe-homologacao.svrs.rs.gov.br/ws/NfeAutorizacao/NFeAutorizacao4.asmx")
    return ("https://www.svc.fazenda.gov.br/NFeAutorizacao4/NFeAutorizacao4.asmx"
            if amb == 1 else
            "https://hom.svc.fazenda.gov.br/NFeAutorizacao4/NFeAutorizacao4.asmx")


# ============ Manifestacao do Destinatario ============
MANIFESTO_TIPOS = {
    "210200": "Confirmacao da Operacao",
    "210210": "Ciencia da Operacao",
    "210220": "Desconhecimento da Operacao",
    "210240": "Operacao nao Realizada",
}


def build_evento_manifestacao(cnpj: str, chave: str, tp_evento: str,
                              justificativa: str, ambiente: int, seq: int = 1) -> str:
    from lxml import etree
    ns = "http://www.portalfiscal.inf.br/nfe"
    dh = (datetime.now(timezone.utc) - timedelta(hours=3)).strftime("%Y-%m-%dT%H:%M:%S-03:00")
    n_seq = str(seq)
    ev_id = f"ID{tp_evento}{chave}{n_seq.zfill(2)}"
    evento = etree.Element("{%s}evento" % ns, nsmap={None: ns}, versao="1.00")
    inf = etree.SubElement(evento, "infEvento", Id=ev_id)
    etree.SubElement(inf, "cOrgao").text = "91"  # Ambiente Nacional
    etree.SubElement(inf, "tpAmb").text = str(ambiente)
    etree.SubElement(inf, "CNPJ").text = only_digits(cnpj)
    etree.SubElement(inf, "chNFe").text = chave
    etree.SubElement(inf, "dhEvento").text = dh
    etree.SubElement(inf, "tpEvento").text = tp_evento
    etree.SubElement(inf, "nSeqEvento").text = n_seq
    etree.SubElement(inf, "verEvento").text = "1.00"
    det = etree.SubElement(inf, "detEvento", versao="1.00")
    etree.SubElement(det, "descEvento").text = MANIFESTO_TIPOS.get(tp_evento, "Manifestacao")
    if tp_evento in ("210220", "210240"):
        etree.SubElement(det, "xJust").text = justificativa
    return etree.tostring(evento, encoding="unicode")


def transmitir_evento_nacional(signed_evento_xml: str, ambiente: int,
                               pfx_bytes: bytes, senha: str) -> dict:
    """Transmite evento (manifestacao) ao Ambiente Nacional (RecepcaoEvento)."""
    import os as _os
    import requests
    import urllib3
    urllib3.disable_warnings()
    from lxml import etree

    amb = int(ambiente)
    url = ("https://www.nfe.fazenda.gov.br/NFeRecepcaoEvento4/NFeRecepcaoEvento4.asmx"
           if amb == 1 else
           "https://hom.nfe.fazenda.gov.br/NFeRecepcaoEvento4/NFeRecepcaoEvento4.asmx")
    ev = _strip_decl(signed_evento_xml)
    env = ('<envEvento versao="1.00" xmlns="http://www.portalfiscal.inf.br/nfe">'
           f'<idLote>1</idLote>{ev}</envEvento>')
    soap = ('<?xml version="1.0" encoding="UTF-8"?>'
            '<soap12:Envelope xmlns:soap12="http://www.w3.org/2003/05/soap-envelope">'
            '<soap12:Body>'
            '<nfeDadosMsg xmlns="http://www.portalfiscal.inf.br/nfe/wsdl/NFeRecepcaoEvento4">'
            f'{env}</nfeDadosMsg></soap12:Body></soap12:Envelope>')
    certfile, keyfile = _pfx_to_pem_files(pfx_bytes, senha)
    try:
        r = requests.post(url, data=soap.encode("utf-8"),
                          headers={"Content-Type": "application/soap+xml; charset=utf-8"},
                          cert=(certfile, keyfile), verify=False, timeout=60)
        root = etree.fromstring(r.content, parser=etree.XMLParser(recover=True))
        ret = root.findall(".//{*}retEvento")
        node = ret[0] if ret else root
        cstat = _find_text(node, "cStat")
        xmot = _find_text(node, "xMotivo")
        nprot = _find_text(node, "nProt")
        status = "registrado" if cstat in ("135", "136", "155") else "rejeitado"
        return {"status": status, "protocolo": nprot, "motivo": f"[{cstat}] {xmot}"}
    except Exception as e:
        return {"status": "rejeitado", "protocolo": "",
                "motivo": f"Falha na comunicacao com o SEFAZ: {e}"}
    finally:
        for f in (certfile, keyfile):
            try: _os.unlink(f)
            except Exception: pass

