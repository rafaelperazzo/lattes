"""
Calculo do scorelattes
"""
import zipfile
import os
from datetime import date
import requests
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask import Flask, jsonify
from waitress import serve
import zeep
import scorerun

app = Flask(__name__)

XML_DIR = 'xml/'

limiter = Limiter(
    get_remote_address,
    app=app,
    storage_uri="redis://redis:6379",
    default_limits=["300 per day", "80 per hour"],
    storage_options={"socket_connect_timeout": 30},
    strategy="fixed-window",
)

def token_valido(token):
    """Verifica se um token é válido.

    Args:
        token (string): Token

    Returns:
        boolean: Verdadeiro ou falso
    """
    if not token.isalnum():
        return False
    else:
        return True

def numero_valido(numero):
    """Verifica se um número é válido.

    Args:
        numero (string): Identificador

    Returns:
        boolean: Verdadeiro ou falso
    """
    try:
        int(numero)
        return True
    except ValueError:
        return False


def salvarCV(idlattes):
    wsdl = './cnpq'
    client = zeep.Client(wsdl=wsdl)
    resultado = client.service.getCurriculoCompactado(idlattes)
    if resultado is not None:
        arquivo = open(idlattes + '.zip','wb')
        arquivo.write(resultado)
        arquivo.close()
        with zipfile.ZipFile(idlattes + '.zip','r') as zip_ref:
            zip_ref.extractall(XML_DIR)
        if os.path.exists(idlattes + '.zip'):
            os.remove(idlattes + '.zip')


def getID(cpf):
    wsdl = './cnpq'
    client = zeep.Client(wsdl=wsdl)
    idlattes = client.service.getIdentificadorCNPq(cpf,"","")
    if idlattes is None:
        idlattes = "0000000000000000"
    return str(idlattes)

@app.route('/')
def home():
    return 'Hello, Flask!'

@app.route("/score/<cpf>/<area_capes>/<periodo>/<tipo>", methods=['GET'])
@limiter.limit("30/day;10/hour;3/minute",methods=["POST"])
def getScoreLattesFromFile(cpf, area_capes, periodo, tipo):
    retorno = {"score": "0"}
    idlattes = "0"
    if len(str(cpf)) != 11:
        idlattes = str(cpf)
    else:
        idlattes = getID(cpf)
    if not token_valido(idlattes):
        return jsonify(retorno)
    periodo = int(periodo)
    if not numero_valido(periodo) or periodo not in [5,7]:
        return jsonify(retorno)
    continuar = False
    for i in range(1,6,1):
        try:
            salvarCV(idlattes)
            continuar = True
        except requests.exceptions.ConnectionError:
            continuar = False
        except Exception:
            continuar = False
        if continuar:
            break
        else:
            return(jsonify(retorno))
    arquivo = XML_DIR + idlattes + ".xml"
    try:
        
        ano_fim = date.today().year
        ano_inicio = ano_fim - periodo
        score = scorerun.Score(arquivo, ano_inicio, ano_fim, area_capes,2017,0,False)
        if tipo=='0':
            sumario = str(score.get_score())
        else:
            sumario = score.sumario()
            return (sumario)
        retorno = {"score": sumario}
        return jsonify(retorno)
    except Exception:
        return jsonify(retorno)

if __name__ == '__main__':
    serve(app, host='0.0.0.0', port=80, url_prefix='/lattes',trusted_proxy='*',trusted_proxy_headers='x-forwarded-for x-forwarded-proto x-forwarded-port')