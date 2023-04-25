import re
import urllib.parse
import requests
from lxml.html import fromstring
import urllib.request
import pdfplumber
import os
import subprocess
import tempfile
import textwrap

def construct_search_url(tipo, numero, ano):
    base_url = "https://www.al.sp.gov.br"
    nature = {
        'PL': 1,
        'PDL': 4,
        'PLC': 2,
        'PR': 3,
        'PEC': 5,
        'REQ': 7
    }
    args = {
        'direction': 'inicio',
        'lastPage': 0,
        'currentPage': 0,
        'act': 'detalhe',
        'rowsPerPage': 5,
        'currentPageDetalhe': 1,
        'method': 'search',
        'natureId': nature[tipo.upper()],
        'legislativeNumber': str(int(numero)),
        'legislativeYear': ano
    }
    search_url = base_url + '/alesp/pesquisa-proposicoes?' + urllib.parse.urlencode(args)
    return search_url

def extract_proposal_url(search_url):
    res = requests.get(search_url)
    soup = fromstring(res.content)
    soup = soup.xpath("//div[@id='lista_resultado']//table/tbody/tr")
    if len(soup) > 1:
        n = soup[0].xpath('./td/a[@target="_top"]')[0]
        link_url = n.get('href')
        return link_url
    return None

def download_proposal(url):
    soup = requests.get(url)
    text = soup.content
    soup = fromstring(text)
    tabela = soup.xpath("//table[@class='tabelaDados']//tr")
    for linha in tabela:
        campo = linha.xpath("./td")[0].text_content().strip()
        valor = linha.xpath("./td")[1]
        if campo == 'Documento':
            file_url = valor.xpath("./a")[0].get("href")
            break
    response = urllib.request.urlopen(file_url)
    ext = file_url.split(".")[-1]
    local_file = tempfile.NamedTemporaryFile(delete=False, suffix=f".{ext}")
    local_file.write(response.read())
    local_file.close()
    return local_file.name

def extract_text_from_pdf(pdf_file):
    with pdfplumber.open(pdf_file) as pdf:
        clean_chunks = []
        for p in pdf.pages:
            bbox = (80, 100, p.width - 80, p.height - 100)
            texto = p.crop(bbox).extract_text()
            texto_limpo = " ".join(texto.strip().split())
            if len(texto_limpo) > 500:
                clean_chunks.append(texto_limpo)
        return " ".join(clean_chunks)

def extract_text_from_doc(doc_file):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as txt_file:
        txt_file_path = txt_file.name
    # Use the shell to redirect the output of antiword to a text file
    cmd = f'antiword "{doc_file}" -w 0 > "{txt_file_path}"'
    subprocess.run(cmd, shell=True, check=True)
    with open(txt_file_path, 'r') as f:
        text = f.read()
    os.unlink(txt_file_path)
    return text

def get_project_content(tipo, numero, ano):
    search_url = construct_search_url(tipo, numero, ano)
    link_url = extract_proposal_url(search_url)
    if link_url is None:
        return None
    base_url = "https://www.al.sp.gov.br"
    proposal_url = base_url + link_url
    local_file = download_proposal(proposal_url)
    if local_file.endswith(".pdf"):
        content = extract_text_from_pdf(local_file)
    elif local_file.endswith(".doc"):
        content = extract_text_from_doc(local_file)
    else:
        content = None
    os.unlink(local_file)

    # Construct metadata
    metadata = {
        'type': tipo,
        'number': numero,
        'year': ano,
        'url': proposal_url
        }

    # Construct the response dictionary
    response = {
        'metadata': metadata,
        'content': content
    }

    return response
