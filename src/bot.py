##=============== VERSION =============
version="🪙TT Beta 1.24"
##=============== import  =============
##log
import logging
import sys
import traceback
##env
import os
from os import getenv
from dotenv import load_dotenv
import json, requests
#telegram
import telegram
from telegram import Update, constants
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters, CallbackContext
#notification
import apprise
#db
import tinydb
from tinydb import TinyDB, Query
import re
#CEX
import ccxt
#DEX
import web3
from web3 import Web3
from web3.contract import Contract
from typing import List
import time

##=============== Logging  =============
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

##=============== CONFIG ===============
dotenv_path = './config/.env'
db_path= './config/db.json'
#===================
global ex
exchanges = {}
trading=True
testmode="True"
#===================
commandlist= """
<code>/bal</code>
<code>/cex binance</code> <code>buy btcusdt sl=1000 tp=20 q=5%</code>
<code>/cex kraken</code> <code>buy btc/usdt sl=1000 tp=20 q=5%</code> <code>/price btc/usdt</code>
<code>/cex binancecoinm</code> <code>buy btcbusd sl=1000 tp=20 q=5%</code>
<code>/dex pancake</code> <code>buy btcb sl=1000 tp=20 q=0.001</code> <code>/price BTCB</code>
<code>/dex quickswap</code> <code>buy wbtc sl=1000 tp=20 q=0.01</code> <code>/price wbtc</code>
<code>/trading</code>
<code>/testmode</code>"""
menu=f'{version} \n {commandlist}\n'
#===========Common Functions ===============

def LibCheck():
    logger.info(msg=f"{version}")
    logger.info(msg=f"Python {sys.version}")
    logger.info(msg=f"TinyDB {tinydb.__version__}")
    logger.info(msg=f"TPB {telegram.__version__}")
    logger.info(msg=f"CCXT {ccxt.__version__}")
    logger.info(msg=f"Web3 {web3.__version__}")
    logger.info(msg=f"apprise {apprise.__version__}")
    return

##===========DB Functions
def DBCommand_Add_TG(s1,s2,s3):
    if len(telegramDB.search(q.token==s1)):
        logger.info(msg=f"token is already setup")
    else:
        telegramDB.insert({"token": s1,"channel": s2,"platform": s3})
def DBCommand_Add_CEX(s1,s2,s3,s4,s5,s6,s7):
    if len(cexDB.search(q.api==s2)):
        logger.info(msg=f"EX exists in DB")
    else:
        cexDB.insert({
        "name": s1,
        "api": s2,
        "secret": s3,
        "password": s4,
        "testmode": s5,
        "ordertype": s6,
        "defaultType": s7}) 
def DBCommand_Add_DEX(s1,s2,s3,s4,s5,s6,s7,s8,s9,s10,s11):
    if len(dexDB.search(q.name==s1)):
        logger.info(msg=f"EX exists in DB")
    else:
        dexDB.insert({
            "name": s1,
            "address": s2,
            "privatekey": s3,
            "version": s4,
            "networkprovider": s5,
            "router": s6,
            "testmode": s7,
            "tokenlist":s8,
            "abiurl":s9,
            "abiurltoken":s10,
            "basesymbol":s11}) 
async def dropDB_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info(msg=f"db dropped")
    db.drop_tables()
async def showDB_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info(msg=f"display db")
    message=f" db extract: \n {db.all()}"
    await send(update,message)
    
#=========Exchange Functions
async def SearchCEX(s1,s2):
    if type(s1) is str:
        query1 = ((q.name==s1)&(q['testmode'] == s2))
        CEXSearch = cexDB.search(query1)
        if (len(str(CEXSearch))>=1):
            return CEXSearch
    elif type(string1) is not str:
        try:
            query1 = ((q.name==s1.name.lower())&(q['testmode'] == s2))
            CEXSearch = cexDB.search(query1)
            if (len(str(CEXSearch))==1):
                return CEXSearch
            else:
                return
        except Exception as e:
            await HandleExceptions(e)
            return
    else:
        return
    
async def SearchDEX(s1,s2):
    try:
        query = ((q.name==s1)&(q['testmode'] == s2))
        DEXSearch = dexDB.search(query)
        if (len(str(DEXSearch))>=1):
         #logger.info(msg=f"{DEXSearch}")
         return DEXSearch
        else:
         return
    except Exception as e:
        await HandleExceptions(e)
        return
    
async def SearchEx(s1,s2):
    try:
      if (isinstance(s1,str)):
        CEXCheck= await SearchCEX(s1,s2)
        DEXCheck= await SearchDEX(s1,s2)
        if (CEXCheck!= None):
            if(len(str(CEXCheck))>=1):
                return CEXCheck[0]['name']
        elif (len(str(DEXCheck))>=1):
            return DEXCheck[0]['name']
      elif not (isinstance(s1,web3.main.Web3)):
        CEXCheck=await SearchCEX(s1.id,s2)
        return CEXCheck[0]['name']
      elif (isinstance(s1,web3.main.Web3)):
        DEXCheck=await SearchDEX(s1,s2)
        return DEXCheck[0]['name']
      else:
        return
    except Exception as e:
        await HandleExceptions(e)
        return
        
async def LoadExchange(exchangeid, mode):
    global ex
    global name
    global networkprovider
    global address
    global privatekey
    global tokenlist
    global router
    global abiurl
    global abiurltoken
    global basesymbol
    global m_ordertype
    logger.info(msg=f"Setting up exchange {exchangeid}")
    CEXCheck= await SearchCEX(exchangeid,mode)
    DEXCheck= await SearchDEX(exchangeid,mode)
    if (CEXCheck):
        newex=CEXCheck
        exchange = getattr(ccxt, exchangeid)
        exchanges[exchangeid] = exchange()
        try:
            exchanges[exchangeid] = exchange({'apiKey': newex[0]['api'],'secret': newex[0]['secret']})
            m_ordertype=newex[0]['ordertype']
            ex=exchanges[exchangeid]
            name=ex
            #ex.verbose = True
            #logger.info(msg=f"markets: {markets}")
            if (mode=="True"):
                ex.set_sandbox_mode('enabled')
                markets=ex.loadMarkets()
                logger.info(msg=f"ex: {ex}")
                return ex
            else:
                markets=ex.loadMarkets ()
                logger.info(msg=f"ex: {ex}")
                return ex
        except Exception as e:
            await HandleExceptions(e)
    elif (DEXCheck):
        newex= DEXCheck
        name= newex[0]['name']
        address= newex[0]['address']
        privatekey= newex[0]['privatekey']
        networkprovider= newex[0]['networkprovider']
        router= newex[0]['router']
        mode=newex[0]['testmode']
        tokenlist=newex[0]['tokenlist']
        abiurl=newex[0]['abiurl']
        abiurltoken=newex[0]['abiurltoken']
        basesymbol=newex[0]['basesymbol']
        ex = Web3(Web3.HTTPProvider(networkprovider))
        if ex.net.listening:
            logger.info(msg=f"Connected to Web3 {ex}")
            return name
        else:
            raise ConnectionError(f'Could not connect to {router}')
    else:
        return

async def DEXContractLookup(symb):
    try:
        url = requests.get(tokenlist)
        text = url.text
        token_list = json.loads(text)['tokens']
        symb=symb.upper()
        #logger.info(msg=f"symbol {symb}")
        try:
            symbolcontract = [token for token in token_list if token['symbol'] == symb]
            if len(symbolcontract) > 0:
                #logger.info(msg=f"symbolcontract {symbolcontract[0]['address']}")
                return symbolcontract[0]['address']
            else:
                msg=f"{symb} does not exist in the token list {tokenlist}"
                await HandleExceptions(msg)
                return
        except Exception as e:
            await HandleExceptions(e)
            return
    except Exception as e:
        await HandleExceptions(e)
        return

async def DEXFetchAbi(addr):
    try:
        url = abiurl
        params = {
            "module": "contract",
            "action": "getabi",
            "address": addr,
            "apikey": abiurltoken }
        #logger.info(msg=f"{url}")
        #logger.info(msg=f"{params}")
        headers = { "User-Agent": "Mozilla/5.0" }
        resp = requests.get(url, params=params, headers=headers).json()
        logger.info(msg=f"request {requests.get(url, params=params, headers=headers)}")    
        abi = resp["result"]
        #logger.info(msg=f"{abi}")
        if(abi!=""):
            return abi
        else:
            return None
    except Exception as e:
        await HandleExceptions(e)

async def DEXFetchSwapMethod(abidata):
    try:
        #logger.info(msg=f"abidata {abidata}")
        swapfunction = abidata.find("swapExactETHForTokens")
        if(swapfunction!=""):
            return 'swapExactETHForTokens'
        else:
            return 'swapExactInputSingle'
    except Exception as e:
        await HandleExceptions(e)

#ORDER PARSER
def Convert(s):
    li = s.split(" ")
    logger.info(msg=f"li{li} no direction")
    try:
        m_dir= li[0]
    except (IndexError, TypeError):
        logger.error(msg=f"{s} no direction")
        return  
    try:
        m_symbol=li[1]
    except (IndexError, TypeError):
        logger.warning(msg=f"{s} no symbol")
        return
    try:
        m_sl=li[2][3:7]
    except (IndexError, TypeError):
        logger.warning(msg=f"{s} no sl")
        m_sl=0
    try:
        m_tp=li[3][3:7]
    except (IndexError, TypeError):
        logger.warning(msg=f"{s} no tp")
        m_tp=0
    try:
        m_q=li[4][2:8]
        m_q.replace("%", "")
    except (IndexError, TypeError):
        logger.warning(msg=f"{s} no size default to 1") 
        m_q=0.1
    order=[m_dir,m_symbol,m_sl,m_tp,m_q]
    logger.info(msg=f"order: {m_dir} {m_symbol} {m_sl} {m_tp} {m_q}")
    return order

#========== Buy function
async def Buy(s1,s2,s3,s4,s5):
    if not isinstance(ex,web3.main.Web3):
        response = await CEXBuy(s1,s2,s3,s4,s5)
        return response
    elif (isinstance(ex,web3.main.Web3)):
        response = await DEXBuy(s1,s2,s3,s4,s5)
        return response
    else:
        logger.warning(msg=f"exchange error {ex}")
        await HandleExceptions(e)
        return

async def CEXBuy(s1,s2,s3,s4,s5):
    try:
        s5=s5[0:-1]
        bal = ex.fetch_free_balance()
        bal = {k: v for k, v in bal.items() if v is not None and v>0}
        logger.info(msg=f"bal: {bal}")
        if (len(str(bal))):
            ######## % of bal
            m_price = float(ex.fetchTicker(f'{s2}').get('last'))
            totalusdtbal = ex.fetchBalance()['USDT']['free']
            amountpercent=((totalusdtbal)*(float(s5)/100))/float(m_price)
            ######## ORDER
            try:
                res = ex.create_order(s2, m_ordertype, s1, amountpercent)
                if({res}!= ValueError):                            
                    orderid=res['id']
                    timestamp=res['datetime']
                    symbol=res['symbol']
                    side=res['side']
                    amount=res['amount']
                    price=res['price']
                    response=f"🟢 ORDER Processed: \n order id {orderid} @ {timestamp} \n  {side} {symbol} {amount} @ {price}"
            except Exception as e:
                await HandleExceptions(e)
                return
    except Exception as e:
        await HandleExceptions(e)
        return

async def DEXBuy(s1,s2,s3,s4,s5):
    web3=ex
    transactionRevertTime = 10000
    gasAmount = 70000
    gasPrice = 20
    tokenToSell = basesymbol
    amountToBuy = s5[0:-1]
    txntime = (int(time.time()) + transactionRevertTime)
    try:
        if(await DEXContractLookup(s2)!= None):
            tokenToBuy = web3.to_checksum_address(await DEXContractLookup(s2))
            tokenToSell=web3.to_checksum_address(await DEXContractLookup(tokenToSell))
            dexabi= await DEXFetchAbi(router)
            method= await DEXFetchSwapMethod(dexabi)
            logger.info(msg=f"method {method}")
            contract = web3.eth.contract(address=router, abi=dexabi) #liquidityContract
            nonce = web3.eth.get_transaction_count(address)
            path=[tokenToSell, tokenToBuy]
            try:
                DEXtxn = contract.functions.swapExactETHForTokens(0,path,address,txntime).build_transaction({
                'from': address, # based Token
                'value': web3.to_wei(float(amountToBuy), 'ether'),
                'gas': gasAmount,
                'gasPrice': web3.to_wei(gasPrice, 'gwei'),
                'nonce': nonce})
                signed_txn = web3.eth.account.sign_transaction(DEXtxn, privatekey)
                tx_token = web3.eth.send_raw_transaction(signed_txn.rawTransaction) # BUY THE TK
                txHash = str(web3.to_hex(tx_token)) # TOKEN BOUGHT
                checkTransactionSuccessURL = abiurl + "?module=transaction&action=gettxreceiptstatus&txhash=" + \
                txHash + "&apikey=" + abiurltoken
                headers = { "User-Agent": "Mozilla/5.0" }
                checkTransactionRequest = requests.get(url=checkTransactionSuccessURL,headers=headers)
                txResult = checkTransactionRequest.json()['status']
                logger.info(msg=f"{txResult}")
                if(txResult == "1"):
                    logger.info(msg=f"{txHash}")
                    return txHash
                else:
                    return
            except Exception as e:
                await HandleExceptions(e)
                return
    except Exception as e:
        await HandleExceptions(e)
        return
#=========== Send function
async def send (self, messaging):
    try:
        await self.effective_chat.send_message(f"{messaging}", parse_mode=constants.ParseMode.HTML)
    except Exception as e:
        await HandleExceptions(e)
#========== notification function
async def notify(messaging):
    try:
        apobj.notify(body=messaging)
    except Exception as e:
        logger.error(msg=f"error: {e}")
#======= error handling
async def HandleExceptions(e) -> None:
    try:
        e==""
        logger.error(msg=f"{e}")
    except KeyError:
        logger.error(msg=f"DB content error {e}")
        e=f"DB content error {e}"
    except ccxt.base.errors:
        logger.error(msg=f"CCXT error {e}")
        e=f"CCXT error {e}"
    except ccxt.NetworkError:
        logger.error(msg=f"Network error {e}")
        e=f"Network error {e}"
    except ccxt.ExchangeError:
        logger.error(msg=f"Exchange error: {e}")
        e=f"Exchange error: {e}"
    except telegram.error:
        logger.error(msg=f"telegram error: {e}")
        e=f"telegram error: {e}"
    except Exception:
        logger.error(msg=f"error: {e}")
        e=f"{e}"
    message=f"⚠️ {e}"
    await notify(message)
##======== END OF FUNCTIONS ============

##============TG COMMAND================
##====view help =======
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg= f"Environment: {env}\nExchange: {await SearchEx(ex,testmode)} Sandbox: {testmode}\n {menu}"
    await send(update,msg)
##====view balance=====
async def bal_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg=f"🏦 Balance"
    try:
        if not isinstance(ex,web3.main.Web3):
            bal = ex.fetch_free_balance()
            bal = {k: v for k, v in bal.items() if v is not None and v>0}
            sbal=""
            for iterator in bal:
                sbal += (f"{iterator} : {bal[iterator]} \n")
            if(sbal==""):
                sbal="No Balance"
            msg+=f"\n{sbal}"
        else:
            bal = ex.eth.get_balance(address)
            bal = ex.from_wei(bal,'ether')
            msg += f"\n{bal}"
        await send(update,msg)
    except Exception as e:
        await HandleExceptions(e)

#===order parsing  ======
async def monitor(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msgtxt = update.effective_message.text
    msgtxt_upper =msgtxt.upper()
    filter_lst = ['BUY', 'SELL']
    msg=""
    if [ele for ele in filter_lst if(ele in msgtxt_upper)]:
        if (trading==False):
            message="TRADING DISABLED"
            await send(update,message)
        else:
            order_m = Convert(msgtxt_upper)
            logger.info(msg=f"order_m= {order_m}")
            m_dir= order_m[0]
            m_symbol=order_m[1]
            m_sl=order_m[2]
            m_tp=order_m[3]
            m_q=order_m[4]
            logger.info(msg=f"Processing: {m_symbol} {m_dir} {m_sl} {m_tp} {m_q}")
            try:
                res=await Buy(m_dir,m_symbol,m_sl,m_tp,m_q)          
                if (res!= None):       
                    response=f"🟢 ORDER Processed: {res}"
                    await send(update,response)
            except Exception as e:
                await HandleExceptions(e)
                return

##======TG COMMAND view price ===========
async def price_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    tginput  = update.effective_message.text
    input = tginput.split(" ")
    symbol=input[1]
    try:
        if not (isinstance(ex,web3.main.Web3)):
            price= ex.fetch_ticker(symbol.upper())['last']
            response=f"₿ {symbol} @ {price}"
        elif (isinstance(ex,web3.main.Web3)):
            if(await DEXContractLookup(symbol) != None):
                TokenToPrice = ex.to_checksum_address(await DEXContractLookup(symbol))
                logger.info(msg=f"token {TokenToPrice}")
                tokenToSell='USDT'
                basesymbol=ex.to_checksum_address(await DEXContractLookup(tokenToSell))
                logger.info(msg=f"basesymbol {basesymbol}")
                qty=1
                logger.info(msg=f"router {router}")
                dexabi= await DEXFetchAbi(router)
                contract = ex.eth.contract(address=router, abi=dexabi) #liquidityContract
                if(TokenToPrice != None):
                    price = contract.functions.getAmountsOut(1, [TokenToPrice,basesymbol]).call()[1]
                    logger.info(msg=f"price {price}")
                    response=f"₿ {TokenToPrice}\n{symbol} @ {(price)}"
                    await send(update,response)
    except Exception as e:
        await HandleExceptions(e)
        return   

##====TG COMMAND Trading switch  ========
async def TradingSwitch(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    global trading
    if (trading==False):
        trading=True
    else:
        trading=False
    message=f"Trading is {trading}"
    await send(update,message)
##====TG COMMAND CEX DEX switch =========
async def SwitchEx(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(msg=f"current ex {ex}")
    msg_ex  = update.effective_message.text
    newexmsg = msg_ex.split(" ")
    newex=newexmsg[1]
    typeex=newexmsg[0]
    try:
        if (typeex=="/cex"):
            SearchCEXResults= await SearchCEX(newex,testmode)
            CEX_name = SearchCEXResults[0]['name']
            CEX_test_mode = testmode
            res = await LoadExchange(CEX_name,CEX_test_mode)
            response = f"CEX is {ex}"
        elif (typeex=="/dex"):
            SearchDEXResults= await SearchDEX(newex,testmode)
            DEX_name= SearchDEXResults[0]['name']
            DEX_test_mode= testmode
            logger.info(msg=f"DEX_test_mode: {DEX_test_mode}")
            logger.info(msg=f"DEX_name: {DEX_name}")
            res = await LoadExchange(DEX_name,DEX_test_mode)
            logger.info(msg=f"res: {res}")
            response = f"DEX is {DEX_name}"
        await send(update,response)
    except Exception as e:
        await HandleExceptions(e)
##======TG COMMAND Test mode switch ======
async def TestModeSwitch(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    global testmode
    if (testmode=="False"):
        testmode="True"
    else:
        testmode="False"
    message=f"Sandbox is {testmode}"
    await send(update,message)
##======== DB START ===============
if not os.path.exists(db_path):
    logger.info(msg=f"setting up new DB")
    open('./config/db.json', 'w').write(open('./config/db.json.sample').read())
    if os.path.exists(dotenv_path):
        logger.info(msg=f"env file found")
        load_dotenv(dotenv_path)
    elif os.getenv("TG_TK")!="":
        logger.info("Using docker variable")
        try:
            TG_TK = os.getenv("TG_TK")
            TG_CHANNEL_ID = os.getenv("TG_CHANNEL_ID")
            CEX_name = os.getenv("EX_NAME")
            CEX_api = os.getenv("EX_YOURAPIKEY")
            CEX_secret = os.getenv("EX_YOURSECRET")
            CEX_password = os.getenv("EX_YOURPASSWORD")
            CEX_ordertype = os.getenv("EX_ORDERTYPE")
            CEX_defaulttype = os.getenv("EX_DEFAULTTYPE")
            CEX_test_mode = os.getenv("EX_SANDBOXMODE")
        except Exception as e:
            logger.error("no env variables")
    #### adding ENV data to DB
        if (TG_TK==""):
            logger.error(msg=f"no TG TK")
            sys.exit()
        else:
            DBCommand_Add_TG(TG_TK,TG_CHANNEL_ID)
        if (CEX_name==""):
            logger.error(msg=f"NO CEX")
        else:
            logger.error(msg=f"adding CEX to DB")
            DBCommand_Add_CEX(CEX_name,CEX_api,CEX_secret,CEX_password,CEX_ordertype,CEX_defaulttype,CEX_test_mode)
        if (DEX_name==""):
            ogger.error(msg=f"NO DEX")
        else:
            DBCommand_Add_DEX()
else:
    logger.info(msg=f"Verifying DB")

if os.path.exists(db_path):
    logger.info(msg=f"Existing DB")
    try:
        db = TinyDB(db_path)
        q = Query()
        globalDB = db.table('global')
        env = globalDB.all()[0]['env']
        ex = globalDB.all()[0]['defaultex']
        testmode = globalDB.all()[0]['defaulttestmode']
        logger.info(msg=f"Env {env} ex {ex}")
        telegramDB = db.table('telegram')
        cexDB = db.table('cex')
        dexDB = db.table('dex')
        tg=telegramDB.search(q.platform==env)
        TG_TK = tg[0]['token']
        TG_CHANNEL_ID = tg[0]['channel']
        cexdb=cexDB.all()
        dexdb=dexDB.all()
        CEX_name = cexdb[0]['name']
        CEX_ordertype = cexdb[0]['ordertype']
        CEX_defaulttype = cexdb[0]['defaultType']
        if (TG_TK==""):
            logger.error(msg=f"no TG TK")
            sys.exit()
        elif (CEX_name==""):
            logger.error(msg=f"missing cex")
            sys.exit()
    except Exception:
        logger.warning(msg=f"error with existing db file {db_path}")
##======== APPRISE Setup ===============
apobj = apprise.Apprise()
apobj.add('tgram://' + str(TG_TK) + "/" + str(TG_CHANNEL_ID))
##========== startup message ===========
async def post_init(application: Application):
    global ex
    await LoadExchange(ex,testmode)
    logger.info(msg=f"Bot is online")
    await application.bot.send_message(TG_CHANNEL_ID, f"Bot is online\nEnvironment: {env}\nExchange: {name} Sandbox: {testmode}\n {menu}", parse_mode=constants.ParseMode.HTML)
#===========bot error handling ==========
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error(msg="Exception:", exc_info=context.error)
    tb_list = traceback.format_exception(None, context.error, context.error.__traceback__)
    tb_string = "".join(tb_list)
    tb_trim = tb_string[:1000]
    e=f"{tb_trim}"
    message=f"⚠️ {e}"
    await send(update,message)
#================== BOT =================
def main():
    try:
        LibCheck()
#Starting Bot TPB
        application = Application.builder().token(TG_TK).post_init(post_init).build()

#TPBMenusHandlers
        application.add_handler(MessageHandler(filters.Regex('/help'), help_command))
        application.add_handler(MessageHandler(filters.Regex('/bal'), bal_command))
        application.add_handler(MessageHandler(filters.Regex('/p'), price_command))
        application.add_handler(MessageHandler(filters.Regex('/trading'), TradingSwitch))
        application.add_handler(MessageHandler(filters.Regex('(?:buy|Buy|BUY|sell|Sell|SELL)'), monitor))
        application.add_handler(MessageHandler(filters.Regex('(?:cex|dex)'), SwitchEx))
        application.add_handler(MessageHandler(filters.Regex('/dbdisplay'), showDB_command))
        application.add_handler(MessageHandler(filters.Regex('/dbpurge'), dropDB_command))
        application.add_handler(MessageHandler(filters.Regex('/testmode'), TestModeSwitch))
        application.add_error_handler(error_handler)
#Run the bot
        application.run_polling()
    except Exception as e:
        logger.fatal("Bot failed to start. Error: " + str(e))

if __name__ == '__main__':
    main()
