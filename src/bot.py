##▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒
##=============== VERSION  =============

TTVersion="🪙TT 0.9.8"

##▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒
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
from telegram import Update, constants
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters, CallbackContext

#notification
import apprise
# By default if no url or configuration is specified apprise will attempt to load
# configuration files (if present) from:
#  ~/.apprise
#  ~/.apprise.yml
#  ~/.config/apprise
#  ~/.config/apprise.yml
#apprise -vv -t 'my title' -b 'my notification body'
# Assuming our {bot_token} is 123456789:abcdefg_hijklmnop
# Assuming the {chat_id} belonging to lead2gold is 12315544
#apprise -vv -t "Test Message Title" -b "Test Message Body" \
#   tgram://123456789:abcdefg_hijklmnop/12315544/

#db
from tinydb import TinyDB, Query
import re

#ccxt
import ccxt

#dex
from web3 import Web3
from web3.contract import Contract
from typing import Dict, List
from decimal import Decimal
import time


##▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒
##=============== Logging  =============

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

logger.info(msg=f"{TTVersion}")
logger.info(msg=f"python {sys.version}")
logger.info(msg=f"CCXT Version: {ccxt.__version__}")

##▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒
##=============== CONFIG  =============

dotenv_path = './config/.env'
db_path= './config/db.json'
##== db ==
db = TinyDB(db_path)
q = Query()
globalDB = db.table('global') 
env = globalDB.all()[0]['env']
logger.info(msg=f"Environment is {env}")
telegramDB = db.table('telegram') 
cexDB = db.table('cex')
dexDB = db.table('dex')
##== var ==
global exchangeid
global web3
global active_ex
global messaging
global address

exchanges = {}
trading=True 
testmode=False

##== telegram bot commands and messages
commandlist= """<code>/help</code>
<code>/bal</code> view active exchange bal
<code>/trading</code> Disable/Enable Trading
<code>/test</code> Switch to Sandbox Mode
<code>/dbdisplay</code> View the DB
=============================
Use <code>/cex</code> or <code>/dex</code> to change active exchange setup in your config:
<code>/cex binance</code>
<code>/cex coinbase</code>
<code>/cex kraken</code>
<code>/cex kucoin</code>
<code>/cex binancecoinm</code>
<code>/cex binanceusdm</code>
<code>/cex huobi</code>
<code>/cex gate</code>
<code>/cex bybit</code>
<code>/dex pancake</code> 
<code>/dex uniswap</code> 
<code>/dex quickswap</code>"""
menu=f'{TTVersion} \n {commandlist}\n'

##▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒
##====== common functions  =============

def Convert(string):
   li = list(string.split(" "))
   return li
  
def loadExchange(exchangeid, api, secret, mode):
    global active_ex
    Ex_CEFI=cexDB.search(q.name.matches(f'{exchangeid}',flags=re.IGNORECASE))
    if Ex_CEFI:
        logger.info(msg=f"CEFI setup for {exchangeid}")
        exchange = getattr(ccxt, exchangeid)
        exchanges[exchangeid] = exchange()
        try:
            exchanges[exchangeid] = exchange({
                'apiKey': api,
                'secret': secret
                })
            logger.info(msg=f"{exchanges[exchangeid]} setup")
            active_ex=exchanges[exchangeid]
            if testmode:
                logger.info(msg=f"Sandbox exchange is {active_ex}")
                active_ex.set_sandbox_mode('enabled')
            else:
                logger.info(msg=f"EX is {active_ex}")
            return active_ex
        except ccxt.NetworkError as e:
            logger.error(msg=f"{e}")
        except ccxt.ExchangeError as e:
            logger.error(msg=f"{e}")
        except Exception as e:
            logger.error(msg=f"{e}")
    else: 
        active_ex=loadExchangeDEX(exchangeid)

def loadExchangeDEX(exchangeid):
    global active_ex
    global address
    global router
    global privatekey
    global tokenlist
    global abiurl
    global abiurltoken
    Ex_DEFI=dexDB.search((q.name.matches(f'{exchangeid}',flags=re.IGNORECASE)))
    if Ex_DEFI:
        try:
            logger.info(msg=f"defi setup for {exchangeid}")
            logger.info(msg=f"New DEX: {Ex_DEFI}")
            name= Ex_DEFI[0]['name']
            address= Ex_DEFI[0]['address']
            privatekey= Ex_DEFI[0]['privatekey']
            version= Ex_DEFI[0]['version']
            networkprovider= Ex_DEFI[0]['networkprovider']
            router= Ex_DEFI[0]['router']
            tokenlist=Ex_DEFI[0]['tokenlist']
            abiurl=Ex_DEFI[0]['abiurl']
            abiurltoken=Ex_DEFI[0]['abiurltoken']
            active_ex = Web3(Web3.HTTPProvider(networkprovider))
            if active_ex.net.listening:
             logger.info(msg=f"{active_ex.net.listening}")
             return name
        except Exception as e:
            logger.error(msg=f"Failed due to a web3 error: {e}")
    else:
        logger.error(msg=f"existing DEX setup")

def DexContractLookup(symbol):
 url = requests.get(tokenlist)
 text = url.text
 token_list = json.loads(text)['tokens']
 target_token = [token for token in token_list if token['symbol'].lower() == symbol.lower()]
 print("Token Contract Address: ", target_token[0]['address'])
 return target_token[0]['address'] if len(target_token)  >  0 else None

# fetch contract abi_
def fetch_abi(address: str):
   url = abiurl
   params = {
   "module": "contract",
   "action": "getabi",
   "address": address,
   "apikey": abiurltoken }
   resp = requests.get(url, params=params).json()
   abi = resp["result"]
   return abi

def DEX_Buy(tokenAddress, amountToBuy):
 global address
 global active_ex
 global privatekey
 web3=active_ex
 transactionRevertTime = 30
 gasAmount = 100
 gasPrice = 5
 try:
        if(tokenAddress != None):
            tokenToBuy = web3.toChecksumAddress(tokenAddress)
            spend = web3.toChecksumAddress(
                "0xbb4cdb9cbd36b01bd1cbaebf2de08d9173bc095c")  # wbnb contract address
            contract = web3.eth.contract(
                address=router, abi=fetch_abi(router))
            nonce = web3.eth.get_transaction_count(address)
            start = time.time()
            pancakeswap2_txn = contract.functions.swapExactETHForTokens(
                0,  # Set to 0 or specify min number of tokens - setting to 0 just buys X amount of tokens for whatever BNB specified
                [spend, tokenToBuy],
                address,
                (int(time.time()) + transactionRevertTime)
            ).buildTransaction({
                'from': address,
                # This is the Token(BNB) amount you want to Swap from
                'value': web3.toWei(float(amountToBuy), 'ether'),
                'gas': gasAmount,
                'gasPrice': web3.toWei(gasPrice, 'gwei'),
                'nonce': nonce,
            })

            try:
                signed_txn = web3.eth.account.sign_transaction(
                    pancakeswap2_txn, privatekey)
                tx_token = web3.eth.send_raw_transaction(
                    signed_txn.rawTransaction)  # BUY THE TOKEN
            except Exception as e:
             logger.error(msg=f"Failed due to  error: {e}")
             return e
           

            txHash = str(web3.toHex(tx_token))

        # TOKEN IS BOUGHT

            checkTransactionSuccessURL = "https://api.bscscan.com/api?module=transaction&action=gettxreceiptstatus&txhash=" + \
                txHash + "&apikey=" + abiurltoken
            checkTransactionRequest = requests.get(
                url=checkTransactionSuccessURL)
            txResult = checkTransactionRequest.json()['status']

            if(txResult == "1"):
             print(txHash)
             return txHash

            else:
                print(" [BUY] Transaction failed: likely not enough gas.")

 except Exception as e:
  logger.error(msg=f"Failed due to  error: {e}")
  return e

       

##▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒
##============= variables  =============

if os.path.exists(db_path):
    logger.info(msg=f"Existing DB found")
    tg=telegramDB.search(q.platform==env)
    TG_TOKEN = tg[0]['token']
    TG_CHANNEL_ID = tg[0]['channel']
    ex=cexDB.all()
    CCXT_id1_name = ex[0]['name']
    CCXT_id1_api = ex[0]['api']  
    CCXT_id1_secret = ex[0]['secret'] 
    CCXT_id1_password = ex[0]['password'] 
    CCXT_test_mode = ex[0]['testmode']
    CCXT_id1_ordertype = ex[0]['ordertype']
    CCXT_id1_defaulttype = ex[0]['defaultType']

else:
    logger.warning(msg=f"no DB, env file")
    if os.path.exists(dotenv_path):
        logger.info(msg=f"env file found")
        load_dotenv(dotenv_path)
    else:
        logger.error(msg=f"no env file available check the path for config")
        #environementinfo={json.dumps({**{}, **os.environ}, indent=2)}
        #logger.info(msg=f"{environementinfo}") 
        sys.exit()
    # ENV VAR (from file or docker variable)
    TG_TOKEN = os.getenv("TG_TOKEN")
    TG_CHANNEL_ID = os.getenv("TG_CHANNEL_ID")
    CCXT_id1_name = os.getenv("EXCHANGE1_NAME")
    CCXT_id1_api = os.getenv("EXCHANGE1_YOUR_API_KEY")  
    CCXT_id1_secret = os.getenv("EXCHANGE1_YOUR_SECRET") 
    CCXT_id1_password = os.getenv("EXCHANGE1_YOUR_PASSWORD") 
    CCXT_id1_ordertype = os.getenv("EXCHANGE1_ORDERTYPE")
    CCXT_id1_defaulttype = os.getenv("EXCHANGE1_DEFAULTTYPE")
    CCXT_test_mode = os.getenv("EXCHANGE1_SANDBOX_MODE")

##=========== DB SETUP =================
    exinsert=cexDB.search(q.api==CCXT_id1_api)
    if len(exinsert):
         logger.info(msg=f"exchange already exist in db")
    else:
         cexDB.insert({
         "name": CCXT_id1_name,
         "api": CCXT_id1_api,
         "secret": CCXT_id1_secret,
         "password": CCXT_id1_password,
         "testmode": CCXT_test_mode,
         "ordertype": CCXT_id1_ordertype,
         "defaultType": CCXT_id1_defaulttype
        })
    tginsert=telegramDB.search(q.token==TG_TOKEN)
    if len(tginsert):
      logger.info(msg=f"bot is already setup")
    else:
      telegramDB.insert({
        "token": TG_TOKEN,
        "channel": TG_CHANNEL_ID,
        "platform": "PRD"
         })
 
    if (TG_TOKEN==""):
        logger.error(msg=f"missing telegram token")
        sys.exit()
    elif (CCXT_id1_name==""):
        logger.error(msg=f"missing main exchangeinfo")
        sys.exit()
    elif (CCXT_id1_name==""):
        logger.error(msg=f"no sandbox setup")

##▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒
##======== INITIAL exchange setup  =====
#tobereviewed to be added to main function

loadExchange(CCXT_id1_name,CCXT_id1_api,CCXT_id1_secret,CCXT_test_mode)
#loadExchangeDEX('pancake') need to enable dex at the start

##▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒
## ========== startup message   ========

async def post_init(application: Application):
    logger.info(msg=f"bot is online")
    await application.bot.send_message(TG_CHANNEL_ID, f"Bot is online\n {env} {active_ex} Sandbox:{testmode}\n {menu}", parse_mode=constants.ParseMode.HTML)

##▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒
##=============== help  ================
##Send a message when /help is used.

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
 message= f"{env} {active_ex} Sandbox:{testmode}\n {menu}"
 await send(update,message)

##▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒
##========== view balance  =============
#Send a message when /bal is used.

async def bal_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info(msg=f" active exchange is {active_ex}")
    Ex_CEFI=cexDB.search(q.name.matches(f'{active_ex}',flags=re.IGNORECASE))
    if (Ex_CEFI):
        try:
            balance = active_ex.fetch_free_balance()
            logger.info(msg=f" active exchange is {balance}")
            balance = {k: v for k, v in balance.items() if v is not None and v>0}
            logger.info(msg=f"{balance}")
            prettybal=""
            for iterator in balance:
                prettybal += (f"{iterator} : {balance[iterator]} \n")
            message=f"🏦 Balance \n{prettybal}"
        except ccxt.NetworkError as e:
            logger.error(msg=f"Failed due to a network error {e}")
            message=f"⚠️{e}"
        except ccxt.ExchangeError as e:
            logger.error(msg=f"Failed due to a exchange error: {e}")
            message=f"⚠️{e}"
        except Exception as e:
            logger.error(msg=f"Failed due to a CCXT error: {e}")
            message=f"⚠️{e}"
    else:
        try:
            balance = active_ex.eth.get_balance(address)
            balance = active_ex.fromWei(balance,'ether')
            message = f"🏦 Balance: {balance}"
        except Exception as e:
            logger.error(msg=f"{e}")
            message=f"⚠️Failed due to a web3 error: {e}"
    await send(update,message)

##▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒
##=========  bot error handling ========
##▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒
## Log Errors caused by Updates

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error(msg="Exception:", exc_info=context.error)
    tb_list = traceback.format_exception(None, context.error, context.error.__traceback__)
    tb_string = "".join(tb_list)
    tb_trim = tb_string[:4000]
    e=f"⚠️ Error encountered {tb_trim}"
    logger.error(msg=f"{e}")
    message=f"{e}"
    await send(update,message)

##▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒
##===== order parsing and placing  =====
## process buy or sell order 

async def monitor(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    messagetxt = update.effective_message.text
    logger.info(msg=f"{messagetxt}")
    messagetxt_upper =messagetxt.upper()
    logger.info(msg=f"{messagetxt_upper}")
    filter_lst = ['BUY', 'SELL']
    if [ele for ele in filter_lst if(ele in messagetxt_upper)]:
        if (trading==False):
            message="TRADING IS DISABLED"
            await send(update,message)
        else:  # order format identified "sell BTCUSDT sl=6000 tp=4500 q=1%"" 
         Ex_CEFI=cexDB.search(q.name.matches(f'{active_ex}',flags=re.IGNORECASE))
         if (Ex_CEFI):
             try:
                order_m = Convert(messagetxt_upper) 
                m_dir= order_m[0]
                m_symbol=order_m[1]
                m_sl=order_m[2][3:7]
                m_tp=order_m[3][3:7]
                m_q=order_m[4][2:-1]
                m_ordertype=CCXT_id1_ordertype
                logger.info(msg=f"Processing order: {m_symbol} {m_ordertype} {m_dir} {m_sl} {m_tp} {m_q}")
                #calculate percentage 
                m_price = float(active_ex.fetchTicker(f'{m_symbol}').get('last'))
                totalusdtbal = active_ex.fetchBalance()['USDT']['free']
                amountpercent=((totalusdtbal)*(float(m_q)/100))/float(m_price) 
                ##need to create a common order send function across cdex and dex
                res = active_ex.create_order(m_symbol, m_ordertype, m_dir, amountpercent)
                orderid=res['id']
                timestamp=res['datetime']
                symbol=res['symbol']
                side=res['side']
                amount=res['amount']
                price=res['price']
                response=f"🟢 ORDER Processed: \n order id {orderid} @ {timestamp} \n  {side} {symbol} {amount} @ {price}"
                #return orderid
             except ccxt.NetworkError as e:
                logger.error(msg=f"Failed due to a network error {e}")
                response=f"⚠️Failed due to a network error {e}"
             except ccxt.ExchangeError as e:
                logger.error(msg=f"Failed due to a exchange error: {e}")
                response=f"⚠️Failed due to a exchange error: {e}"
             except Exception as e:
                logger.error(msg=f"Failed due to a CCXT error: {e}")
                response=f"⚠️Failed due to a CCXT error: {e}"
             await send(update,response)
         else:
          order_m = Convert(messagetxt_upper) 
          m_dir= order_m[0]
          m_symbol_tobuy=DexContractLookup(order_m[1])
          m_symbol_tosell=active_ex.toChecksumAddress("0xbb4cdb9cbd36b01bd1cbaebf2de08d9173bc095c")#wbnb contract
          #m_q=order_m[2][2:-1]
          m_q=1
          res=DEX_Buy(m_symbol_tobuy,m_q)
          response=f"DEX {res}"
         await send(update,response)
    else: error_handler()

##▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒
##======= view last closed orders  =====
## Send a message when /order is used.
async def lastorder_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info(msg=f"TBD lastorder_command")

##▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒
##=========== view positions  ========
## Send a message when the /pos is used.
async def position_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
 logger.info(msg=f"TBDposition_command")

##▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒
##=========== view today's pnl =========
## Send a message when /profit or add the output to /bal
async def pnl_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
 logger.info(msg=f"TBD pnl_command")

##▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒
##======== trading switch  =============
##Send a message when /trading is used

async def trading_switch(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    global trading
    if (trading==False):
        trading=True
    else:
        trading=False
    message=f"Trading is {trading}"
    await send(update,message)

##▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒
##============ CEX DEX switch  =========
#Send a message when /cex or /dex is used

async def switch(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg_ex  = update.effective_message.text
    newexchangemsg = Convert(msg_ex) 
    newexchange=newexchangemsg[1]
    extype=newexchangemsg[0]
    global active_ex
    if extype=="/cex":
        if testmode:
            newex=cexDB.search((q.name.matches(f'{newexchange}',flags=re.IGNORECASE)&(q.testmode=="True")))
        else:
            newex=cexDB.search((q.name.matches(f'{newexchange}',flags=re.IGNORECASE)&(q.testmode!="True")))
            logger.info(msg=f"New CEX: {newex}")
        if len(newex):
            logger.info(msg=f"CEX setup starting for {newex[0]['name']}")
            CCXT_name = newex[0]['name']
            CCXT_api = newex[0]['api']  
            CCXT_secret = newex[0]['secret'] 
            CCXT_password = newex[0]['password'] 
            CCXT_test_mode = newex[0]['testmode'] 
            res = loadExchange(CCXT_name,CCXT_api,CCXT_secret,CCXT_test_mode)
            response = f"Active CEX is {res} \n "
        else:
            response = 'CEX not setup'
    else:
        newex=dexDB.search((q.name.matches(f'{newexchange}',flags=re.IGNORECASE))&(q.testmode!="True"))
        name= newex[0]['name']
        logger.info(msg=f"dex setup for: {name}")
        res = loadExchangeDEX(name)
        logger.info(msg=f"res: {res}")
        response = f"Active DEX is {name}"
    await send(update,response)

##▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒
##======== Test mode switch  ===========
##Send a message when /test is used

async def testmode_switch(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    global testmode
    if (testmode==False):
        testmode=True
    else:
        testmode=False
    message=f"Sandbox is {testmode}"
    await send(update,message)

##▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒
##=========== DB COMMAND ===============

##=========  drop DB ========
async def dropDB_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info(msg=f"db table dropped")
    db.drop_tables()

##=========  show DB ========
async def showDB_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info(msg=f"display db")
    message=f" db extract: \n {db.all()}"
    await send(update,message)


##▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒
##=========  bot restart  ========

async def restart_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    (
    logger.info(msg=f"TBDrestarting")
    )
##▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒
##=======   notify command      ========
##▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒
async def notify_command()-> None:
    logger.info(msg=f"apprise test")
    #  apobj = apprise.Apprise()
    config = apprise.AppriseConfig()
    config.add('./config/apprise.yml')
    apobj.add(config)
    apobj.notify(
     body='what a great notification service!',
     title='my notification title')


##▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒
##=======   sendmessage command  =======
##▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒

async def send (self, messaging):
 await self.effective_chat.send_message(f"{messaging}", parse_mode=constants.ParseMode.HTML)

##▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒
##=======  bot unknow command  ========
##▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒
async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    log.error(update, 'TBD unknown')

##▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒
##=============== BOT  =============
##▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒

def main():

    # Create the Application
    try:
     apobj = apprise.Apprise()   
     application = Application.builder().token(TG_TOKEN).post_init(post_init).build()
        # Menus
     application.add_handler(MessageHandler(filters.Regex('/help'), help_command))
     application.add_handler(MessageHandler(filters.Regex('/bal'), bal_command))
     application.add_handler(MessageHandler(filters.Regex('/trading'), trading_switch))
     application.add_handler(MessageHandler(filters.Regex('(?:buy|Buy|BUY|sell|Sell|SELL)'), monitor))
     application.add_handler(MessageHandler(filters.Regex('(?:cex|dex)'), switch))
     application.add_handler(MessageHandler(filters.Regex('/test'), testmode_switch))
     application.add_handler(MessageHandler(filters.Regex('/lastorder'), lastorder_command))
     application.add_handler(MessageHandler(filters.Regex('/position'), position_command))
     application.add_handler(MessageHandler(filters.Regex('/restart'), restart_command))
     application.add_handler(MessageHandler(filters.Regex('/dbdisplay'), showDB_command))
     application.add_handler(MessageHandler(filters.Regex('/dbpurge'), dropDB_command))
     application.add_handler(MessageHandler(filters.Regex('/notify'), notify_command))

        #error handling 
     application.add_error_handler(error_handler)
        #Run the bot
     application.run_polling()
    except Exception as error:
     logger.fatal("Bot failed to start. Error: " + str(error))

if __name__ == '__main__':
    main()


