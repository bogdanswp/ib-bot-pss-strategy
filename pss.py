'''
Bot PSS strategy (Paired Switching strategy) described in the paper below
https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2437049
'''
import ibapi
from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.contract import Contract
from ibapi.order import *
from ibapi.ticktype import TickTypeEnum
import threading
import pandas as pd
from datetime import datetime, timedelta
import time
from collections import deque
import getAccInfoInterface as gai

#Vars
orderId = 1

# Class for Interactive Brokers Connection
# Data on IBApi Class and Logic in the Bot Class
class IBApi(EClient,EWrapper):
  def __init__(self):
    EClient.__init__(self, self)

  # Get next order id we can use
  def nextValidId(self, nextorderId):
    global orderId
    orderId = nextorderId

  def error(self, id, errorCode, errorMsg):
    print(errorCode,errorMsg)

  # Historical Backtest Data
  def historicalData(self, reqId, bar):
    try:
      bot.on_bar_update(reqId,bar,False)
    except Exception as e:
      print(e)

  # On Realtime Bar after historical data finishes
  def historicalDataUpdate(self, reqId, bar):
    try:
      bot.on_bar_update(reqId,bar,True)
    except Exception as e:
      print(e)

#Bar Object
class Bar:
  open = 0
  low = 0
  high = 0
  close = 0
  volume = 0
  date = datetime.now()
  def __init__(self):
    self.open = 0
    self.low = 0
    self.high = 0
    self.close = 0
    self.volume = 0
    self.date = datetime.now()

# Bot Logic
class Bot:
  global orderId;
  ib = None
  lastMonthClose = [None for bar in range(2)]
  currentBars = [None for bar in range(2)]
  historicBars = [[None for bar in range(3)],[None for bar in range(3)]]
  currentDay = 0
  strongerTrend = None
  contracts = pd.DataFrame([
    ['SPY','SMART','USD'],
    ['TLT','SMART','USD']
    ])
  # make decent column names
  contracts.columns = ['sym','exch','curr']

  def __init__(self):
    #Connect to IB on init
    self.ib = IBApi()
    self.ib.connect("127.0.0.1", 7496,1)
    ib_thread = threading.Thread(target=self.run_loop, daemon=True)
    # this will call run_loop. ib.run() will initiate the connection and start listening on the socket
    ib_thread.start()
    time.sleep(1)

    # request last three months bars containing closing prices. After the historic data, live data will be received
    for index, row in self.contracts.iterrows():
      c = Contract()
      c.symbol = row['sym']
      c.exchange = 'SMART'
      c.currency = 'USD'
      c.secType = 'STK'
      self.ib.reqHistoricalData(str(index),c,"","4 M","1 month","TRADES",1,1,True,[])

  #Listen to socket in separate thread
  def run_loop(self):
    self.ib.run()

  #Process historic and realtime bar data
  def on_bar_update(self, reqId, bar, realtime):
    global orderId
    newDay=0
    #Historical Data to catch up
    if (realtime == False):
      #add last month close plus three older monthly closes
      self.addHistoricBar(reqId,bar)
    else:
      barDate = datetime.strptime(bar.date, "%Y%m%d")
      if (self.currentDay != barDate.day):
        newDay = 1
        self.currentDay = barDate.day
        #Check which asset has a stronger trend (according to our formula) at the start of each month
        if ((newDay) and (barDate.day == 1)):
          #update lastMonthClose and historicBars
          self.updateAllBars()
          self.botLogic()
        else:
          print("I only check indicators once a month. Waiting patiently until next month.")
        self.currentBars[reqId]=bar

  def addHistoricBar(self,reqId,bar):
    for i, b in enumerate(self.historicBars[reqId]):
      if (b == None):
        self.historicBars[reqId][i] = bar
        break
      else:
        self.currentBars[reqId] = bar
    if((b!=None) and (self.lastMonthClose[reqId]==None)):
      self.lastMonthClose[reqId] = bar
      self.currentBars[reqId] = bar

  def updateAllBars(self):
    for reqId in range(2):
      self.historicBars[reqId][0]=self.historicBars[reqId][1]
      self.historicBars[reqId][1]=self.historicBars[reqId][2]
      self.historicBars[reqId][2]=self.lastMonthClose[reqId]
      self.lastMonthClose[reqId]=self.currentBars[reqId]

  def botLogic(self):
    actionType = None
    #Check wich asset has the stronger trend according to our strategy formula
    if (self.lastMonthClose[0].close/self.historicBars[0][0].close > self.lastMonthClose[1].close/self.historicBars[1][0].close):
      strongerTrend = 0
    else:
      strongerTrend = 1
    print("Stronger trend is: {}".format(self.contracts.iloc[strongerTrend]['sym']))
    #Update positions if needed
    if (strongerTrend == self.strongerTrend):
      print("Stronger trend is the same {}. Keep the same position.".format(self.contracts.iloc[strongerTrend]['sym']))
      return
    elif (self.strongerTrend == None):
      self.strongerTrend = strongerTrend
      print("Opening initial position. Buying asset: {}".format(self.contracts.iloc[strongerTrend]['sym']))
      self.placeOrders('firstOrder')
    else:
      self.strongerTrend = strongerTrend
      self.placeOrders('switchPositions')

  def placeOrders(self,actionType):
    global orderId
    position = None
    if(actionType == 'switchPositions'):
      #sell asset with weaker trend
      #Create sellContract for Sell Order
      sellContract = Contract()
      sellContract.symbol = self.contracts.iloc[1-self.strongerTrend]['sym']
      sellContract.secType = "CFD"
      sellContract.exchange = "SMART"
      sellContract.currency = "USD"
      print('sellContract = {}'.format(sellContract))
      #Create and Place Sell Order
      sellOrder = Order()
      sellOrder.orderId = orderId
      sellOrder.orderType = "MKT"
      sellOrder.action = "SELL"
      position = gai.read_positions()
      quantity = position.iloc[0]['Quantity']
      sellOrder.totalQuantity = quantity
      print('Place order to sell asset with weaker trend: {}'.format(sellContract.symbol))
      self.ib.placeOrder(sellOrder.orderId,sellContract,sellOrder)
      orderId+=1
      time.sleep(3)

    #buy strongerTrend asset
    #Create buyContract for Buy Order
    buyContract = Contract()
    buyContract.symbol = self.contracts.iloc[self.strongerTrend]['sym']
    buyContract.secType = "CFD"
    buyContract.exchange = "SMART"
    buyContract.currency = "USD"
    print('buyContract = {}'.format(buyContract))
    #Create and Place Buy Order
    buyOrder = Order()
    buyOrder.orderId = orderId
    buyOrder.orderType = "MKT"
    buyOrder.action = "BUY"
    position = gai.read_positions()
    #there should be no open position
    if(len(position)==0):
      nav = gai.read_navs()
      quantity = int(float(nav.iloc[0]['Value']) / self.currentBars[self.strongerTrend].close)
      buyOrder.totalQuantity = quantity
      print('Place order to buy asset with stronger trend: {}'.format(buyContract.symbol))
      self.ib.placeOrder(buyOrder.orderId,buyContract,buyOrder)
      orderId+=1
    elif(actionType != 'retrySellOrder'):
      #retry because maybe the sellOrder was not yet executed
      time.sleep(3)
      self.placeOrders("retrySellOrder")
    else:
      print("There are other open positions. This account should be dedicated only with for strategy.")
      self.ib.disconnect()

# start Bot
bot = Bot()
