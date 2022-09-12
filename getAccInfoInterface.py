def read_positions(): #read all accounts positions and return DataFrame with information

    from ibapi.client import EClient
    from ibapi.wrapper import EWrapper
    from ibapi.common import TickerId
    from threading import Thread

    import pandas as pd
    import time

    class ib_class(EWrapper, EClient):

        def __init__(self):
            EClient.__init__(self, self)

            self.all_positions = pd.DataFrame([], columns = ['Account','Symbol', 'Quantity', 'Average Cost', 'Sec Type'])

        def error(self, reqId:TickerId, errorCode:int, errorString:str):
            if reqId > -1:
                print("Error. Id: " , reqId, " Code: " , errorCode , " Msg: " , errorString)

        def position(self, account, contract, pos, avgCost):
            self.all_positions.loc[len(self.all_positions.index)] = account, contract.symbol, pos, avgCost, contract.secType

    def run_loop():
        app.run()

    app = ib_class()
    app.connect('127.0.0.1', 7496, 0)
    #Start the socket in a thread
    api_thread = Thread(target=run_loop, daemon=True)
    api_thread.start()
    time.sleep(1) #Sleep interval to allow time for connection to server

    app.reqPositions() # associated callback: position
    print("Waiting for IB's API response for accounts positions requests...\n")
    time.sleep(3)
    current_positions = app.all_positions
    #current_positions.set_index('Account',inplace=True,drop=True) #set all_positions DataFrame index to "Account"

    app.disconnect()

    return(current_positions)


def read_navs(): #read all accounts NAVs

    from ibapi.client import EClient
    from ibapi.wrapper import EWrapper
    from ibapi.common import TickerId
    from threading import Thread

    import pandas as pd
    import time

    class ib_class(EWrapper, EClient):

        def __init__(self):
            EClient.__init__(self, self)

            self.all_accounts = pd.DataFrame([], columns = ['reqId','Account', 'Tag', 'Value' , 'Currency'])

        def error(self, reqId:TickerId, errorCode:int, errorString:str):
            if reqId > -1:
                print("Error. Id: " , reqId, " Code: " , errorCode , " Msg: " , errorString)

        def accountSummary(self, reqId, account, tag, value, currency):
            self.all_accounts.loc[len(self.all_accounts.index)]=reqId, account, tag, value, currency

    def run_loop():
        app.run()

    app = ib_class()
    app.connect('127.0.0.1', 7496, 0)
    #Start the socket in a thread
    api_thread = Thread(target=run_loop, daemon=True)
    api_thread.start()
    time.sleep(1) #Sleep interval to allow time for connection to server

    app.reqAccountSummary(0,"All","NetLiquidation")  # associated callback: accountSummary / Can use "All" up to 50 accounts; after that might need to use specific group name(s) created on TWS workstation
    print("Waiting for IB's API response for NAVs requests...\n")
    time.sleep(5)
    current_nav = app.all_accounts

    app.disconnect()

    return(current_nav)
