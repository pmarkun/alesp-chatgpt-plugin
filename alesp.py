import re
import urllib.parse
import requests
from lxml.html import fromstring, etree
import urllib.request
import pdfplumber
import os
import subprocess
import tempfile

base_url = "https://www.al.sp.gov.br"

def construct_search_url(tipo=None, numero=None, ano=None, author_id=None, start_date=None, end_date=None):
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
        'rowsPerPage': 50,
        'currentPageDetalhe': 1,
        'method': 'search'
    }
    if tipo:
        args['natureId'] = nature[tipo.upper()]
    if ano:
        args['legislativeYear'] = ano
    if tipo and numero and ano:
        args['legislativeNumber'] = str(int(numero))
        args['rowsPerPage'] = 5
    if author_id:
        args['author'] = author_id
    if start_date:
        args['strInitialDate'] = start_date
    if end_date:
        args['strFinalDate'] = end_date

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

def extract_search_results(url):
    soup = requests.get(url)
    text = soup.content
    soup = fromstring(text)
    
    # Extract the rows from the search results table
    rows = soup.xpath("//div[@id='lista_resultado']//table[@class='tabela']/tbody/tr")
    
    # Initialize an empty list to store the extracted data
    results = []
    
    # Iterate over the rows and extract the relevant information
    for i in range(0, len(rows), 2):  # Skip every other row (empty rows)
        row = rows[i]
        author_td, document_td = row.xpath("./td")
        
        # Extract the author name and URL
        if author_td.xpath(".//a"):
            author_link = author_td.xpath(".//a")[0]
            author_url = author_link.get("href")
        else:
            author_url = ''
        try:
            author_name = author_link.text_content().strip()
        except:
            author_name = author_td.text_content()
        
        # Extract the document name, URL, and description
        document_link = document_td.xpath(".//a")[0]
        document_name = document_link.text_content().strip()
        document_url = document_link.get("href")
        document_description = document_link.xpath("./following-sibling::br")[0].tail.strip()
        
        # Append the extracted data to the results list
        results.append({
            "author_name": author_name,
            "author_url": base_url + author_url,
            "project": document_name,
            "url": base_url + document_url,
            "subject": document_description
        })
    
    return results

def fetch_and_clean_deputados_data():
    # Fetch the XML data from the URL
    response = requests.get("https://www.al.sp.gov.br/repositorioDados/deputados/deputados.xml")
    xml_content = response.content

    # Parse the XML data
    root = etree.fromstring(xml_content)
    deputados = root.xpath("//Deputado")

    # Initialize an empty list to store the cleaned data
    cleaned_data = []

    # Extract and clean up the data for each deputy
    for deputado in deputados:
        data = {}
        for child in deputado:
            tag = child.tag
            text = child.text
            data[tag] = text
        cleaned_data.append(data)

    # Store the cleaned data in a JSON file
    return(cleaned_data)

def get_deputado_by_name(deputados_data, name):
    for deputado in deputados_data:
        if deputado['NomeParlamentar'].lower() == name.lower():
            return deputado
    return {}