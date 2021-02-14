import re, traceback
def escreve_erros(erro):
    linhas = " -> ".join(re.findall(
        r'line \d+', str(traceback.extract_tb(erro.__traceback__))))
    with open("errors.log", "a") as file:
        file.write(f"{type(erro)} - {erro}:\n{linhas}\n")

try:
    from iqoptionapi.stable_api import IQ_Option
    import eel, time, json, threading

    from datetime import datetime, timedelta
    from cryptography.fernet import Fernet
    from dontpad import Dontpad
    from os import listdir

    class IQOption:
        def __init__(self):
            self.API = None
            self.amount = 2
            self.stopwin = 10
            self.stoploss = 10
            self.earn = 0
            self.id = 0
            self.wait = 5   
            self.url = ""
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
            self.API = IQ_Option(email, password)
            self.API.connect()
            if self.API.check_connect():
                self.API.change_balance("PRACTICE")
                return True
            return False

        def ordem(self, par, tipo, direcao, tempo):
            id = self.id
            eel.placeTrade(par.upper(), direcao.upper(), tempo, id)
            self.id += 1

            if tipo == "binary" and tempo == 5:
                atual = datetime.utcnow()
                if ((atual.minute % 5 == 4 and atual.second < 30) 
                    or atual.minute % 5 < 4): 
                    tempo = 5 - (atual.minute % 5)

            if tipo == "binary":
                status, identificador = self.API.buy(
                    self.amount, par, direcao, tempo)
            else:
                status, identificador = self.API.buy_digital_spot(
                    par, self.amount, direcao, tempo)
                
            if not status:
                return "error", 0

            lucro = 0
            if tipo == "binary":
                resultado, lucro = self.API.check_win_v4(identificador)
            else:
                status = False
                while not status:
                    status, lucro = self.API.check_win_digital_v2(identificador)
                    time.sleep(0.5)
                if lucro > 0: 
                    resultado = "win"
                elif lucro < 0: 
                    resultado = "loose"
                else: 
                    resultado = "equal"

            if resultado == "win": self.earn += lucro
            elif resultado == "loose": self.earn -= abs(lucro)
            eel.setResult(id, resultado.upper())
            eel.updateInfos(self.earn, self.stopwin, self.stoploss)

            return resultado, lucro

        def auto_trade(self):
            ultimo = ()
            while self.earn < self.stopwin and self.earn > -self.stoploss:
                response = json.loads(
                    Dontpad.read("copytrader/" + self.url))
                try:
                    for trade in response['orders']:
                        timestamp = trade['timestamp']
                        if time.time() - timestamp < self.wait + 2:
                            par, tipo = trade['asset'], trade['type']
                            direcao = trade['order']
                            tempo = trade['timeframe']
                            if (par, timestamp) != ultimo:
                                ultimo = (par, timestamp)
                                threading.Thread(
                                    target = self.ordem, daemon = True,
                                    args=(par, tipo, direcao, tempo)).start()
                except: pass
                time.sleep(self.wait)
            eel.changeStatus()

    api = IQOption()
    eel.init('web')

    @eel.expose
    def verify_connection(email, password):
        if not api.login(email, password):
            return None
        try:
            # requests.get(SERVER_URL)
            json.loads(Dontpad.read("copytrader/" + api.url))
            threading.Thread(
                target = api.auto_trade, daemon = True).start()
            return True
        except Exception as e: 
            return False

    def save_config():
        dic = {
            "id": api.url,
            "account": api.account,
            "amount": api.amount,
            "stopwin": api.stopwin,
            "stoploss": api.stoploss,
            "wait": api.wait
        }
        with open("config/data.json", "w") as file:
            json.dump(dic, file, indent = 2)
            
    @eel.expose
    def change_config(account, amount, stopwin, stoploss, wait):
        api.change_balance(account)
        api.amount = float(amount)
        api.stopwin = float(stopwin)
        api.stoploss = float(stoploss)
        api.wait = int(wait)
        save_config()
        eel.updateInfos(api.earn, api.stopwin, api.stoploss)

    def get_data():
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

    def devolve_restante(tempo_restante):
        if  tempo_restante < 0:
            mensagem = "Renove sua licença"
            api.url = None
        else:
            horas_minutos = timedelta(seconds = tempo_restante)
            duracao = str(horas_minutos)[:-7].replace('days', 'dias')
            if "dias" not in duracao:
                duracao += "h"
            mensagem = f"Sua licença dura {duracao}"
        return mensagem

    def procurar_licenca(filetext = ""):
        f = Fernet(b'cHJvN6obAWDiWc5ghyYrPTuPx5x2a8DKr55RVQIMT50=')
        dia, mes, ano = 17, 2, 2021
        email, hora, minuto = "", 0, 0

        def decrypt(text):
            message = f.decrypt(text).decode()
            email, data, horario = message.split("|")
            dia, mes, ano = list(map(int, data.split("/")))
            hora, minuto = list(map(int, horario.split(":")))
            return email, dia, mes, ano, hora, minuto

        if filetext != "":
            try:
                email, dia, mes, ano, hora, minuto = decrypt(
                    filetext.encode("utf-8"))
            except Exception as e: print(type(e), e); filetext = ""
        else:
            try:
                files = listdir(".")
                indice = list(map(lambda x:".key" in x, files)).index(True)
                with open(f"{files[indice]}", "rb") as file:
                    email, dia, mes, ano, hora, minuto = decrypt(file.readline())
            except:
                try:
                    with open("license.key", "rb") as file:
                        message = f.decrypt(file.readline()).decode()
                        dia, mes, ano = list(map(int, message.split("/")))
                except Exception as e: 
                    print(e)
        
        data_final = datetime(ano, mes, dia, hora, minuto)
        tempo_restante = datetime.timestamp(data_final
            ) - datetime.timestamp(datetime.now())

        mensagem = devolve_restante(tempo_restante)
        return mensagem, email, filetext

    @eel.expose
    def search_license(text):
        mensagem, email, filetext = procurar_licenca(text)
        eel.changeLicense(email, mensagem)
        if filetext != "":
            with open("license.key", "wb") as file:
                file.write(filetext.encode("utf-8"))

    get_data()
    with open("config/data.json") as file:
        resultado = json.load(file)
        api.url = resultado['id']
        eel.changeConfig(resultado)

    mensagem, email, caminho = procurar_licenca()
    eel.changeLicense(email, mensagem)
    eel.start('index.html')
except Exception as e:
    escreve_erros(e)