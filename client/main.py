import eel, time, json, threading, traceback, requests
from utils.lista_taxa import ListaTaxa as Operacao
from api import Api

from socketclient import WebsocketClient
from cryptography.fernet import Fernet
from datetime import datetime

def hitStop(): eel.hitStop()
def addLog(*args, **kwargs): eel.addLog(*args, *kwargs)
def updateGeral(*args, **kwargs): eel.updateGeral(*args, *kwargs)
def placeTrade(paridade, direcao, tempo, valor): 
    current_id = api.id
    paridade, direcao = paridade.upper(), direcao.upper()
    eel.placeTrade(paridade, direcao, tempo, valor, current_id)
    api.id += 1
    return current_id

def registerResult(id: int, resultado: str):
    if resultado.upper() != "ERROR":
        eel.updateInfos(api.API.ganho_total, 
          api.API.stopwin, api.API.stoploss)
    eel.setResult(id, resultado.upper())

class IQOption:
    def __init__(self):
        self.API = None
        self.socket = None
        self.id = 0
        self.wait = 1
        self.inicio = 1
        self.final = 100
        self.timeframe = 1
        self.premium = True
        self.reverso = False
        self.lista_atual = []
        self.account = "train"

    def change_balance(self, balance):
        if self.API != None:
            if not balance and self.account != "real":
                self.API.change_balance("REAL")
                self.account = "real"
            elif self.account != "train":
                self.API.change_balance("PRACTICE")
                self.account = "train"

    def login(self, email, password):
        config = {
            "scalper_loss": 0,
            "tipo_gale": "martingale",
            "tipo_martin": "agressivo",
            "minimo": 0, "delay": False,
            "scalper_win": 0, "valor": 2, 
            "stoploss": 10, "max_gale": 2,
            "timeframe": 1, "reverso": False,
            "stopwin": 10, "ciclos_gale": [],
            "email": email, "senha": password,
            "max_soros": 0, "ciclos_soros": [], 
            "tipo_conta": "treino", "token": "",
            "tipo_soros": "normal", "chat_id": "", 
            "prestopwin": 0, "prestoploss": False,
            "tipo_stop": "fixo", "tipo_par": "auto", 
            "vez_gale": "vela",
        }
        try:
            eel.loadConfig(config)
            self.API = Operacao(config, addLog, updateGeral,
                        placeTrade, registerResult, hitStop)
            return True
        except Exception as e:
            print(type(e), e)
            return False

    def can_trade(self):
        return (self.API.ganho_total < self.API.stopwin and 
                self.API.ganho_total > -self.API.stoploss)

    def auto_trade(self, response: dict):
        ultimo = ()
        if self.can_trade():
            try:
                trade_list = response.get('orders', [])
                if len(trade_list) > 1 and trade_list != self.lista_atual:
                    self.API.mostrar_mensagem(
                        f"Lista de {len(trade_list)} entradas recebida do ADM!")
                    self.API.comandos = trade_list
                    self.lista_atual = trade_list
                    self.API.comando_atual = 0
                    threading.Thread(
                        target = self.API.operar_lista_taxas,
                        daemon = True).start()
                    return
                elif len(trade_list) > 1: return
                for trade in trade_list:
                    timestamp = trade['timestamp']
                    if time.time() - timestamp < self.wait + 3:
                        par, tipo = trade['asset'], trade['type']
                        tempo = trade['timeframe']
                        direcao = trade['order']
                        if not self.can_trade():
                            return eel.hitStop()

                        if (par, timestamp) != ultimo:
                            ultimo = (par, timestamp)
                            threading.Thread(
                                target = self.API.realizar_trade,
                                daemon = True, args = (self.API.valor,
                                    par, direcao, tempo, 0.7, tipo)
                            ).start()
            except Exception as e: 
                print(type(e), traceback.print_exc())
        else: eel.hitStop()

api = IQOption()
eel.init('web')

@eel.expose
def change_operation(): 
    if api.premium: 
        today = datetime.now()
        addLog(today.strftime("%d/%m/%Y"), 
            today.strftime("%H:%M"), 
            "🔰 Esperando entradas do ADM.")

@eel.expose
def verify_connection(email, password):
    has_access, message = autenticar_licenca(email)
    if not has_access:
        eel.screenAlert(message)
        return None

    if not api.login(email, password):
        return None
    
    today = datetime.now()
    addLog(today.strftime("%d/%m/%Y"), 
        today.strftime("%H:%M"), message)
    try:
        with open("./config/data.json") as file:
            config = json.load(file)
        api.socket = WebsocketClient(config['ip'], api.auto_trade)
        api.socket.connect()
        return True
    except Exception as e:
        print(type(e), e)
    return False

@eel.expose
def change_config(config):
    if not api.can_trade():
        eel.goOnline()
        api.API.resetar_status()

    api.API.salvar_variaveis(config)
    api.timeframe = int(config.get("timeframe", 1))
    api.reverso = bool(config.get("reverso", False))
    eel.updateInfos(api.API.ganho_total, 
        api.API.stopwin, api.API.stoploss)

@eel.expose
def load_from_admin():
    new_config = Api.read()
    api.API.config.update(new_config)
    api.API.salvar_variaveis(api.API.config)
    eel.updateInfos(api.API.ganho_total, 
        api.API.stopwin, api.API.stoploss)
    eel.updateConfig(api.API.config)
    eel.loadConfig(api.API.config)

def load_bot_data_info():
    f = Fernet(b'yqzmMSzGGdoYCfIu_OCE5VEQeDh5v5M6vqjDqhAGYk0=')
    try:
        with open("config/data.dll", "rb") as file:
            message = f.decrypt(file.readline()).decode()
            config = json.loads(message)
    except:
        config = {
            "titulo": "Copytrader",
            "login": "CopyClient Login",
            "nome": "CopyTrader",
            "icone": ""
        }
    eel.changeData(config)

def autenticar_licenca(email):
    validacao, mensagem = False, "Adquira uma licença!"
    try:
        response = requests.get("https://tiagobots.vercel.app/api/clients", 
            params = { "email": email, "botName": "copytrader"}).json()
        if "timestamp" in response and int(response["timestamp"]) > 0:
            validacao, mensagem = True, response["message"]
        else:
            validacao, mensagem = False, "Compre uma licença!"
    except:
        validacao, mensagem = False, "Servidor em manutenção!"
    return validacao, mensagem


load_bot_data_info()