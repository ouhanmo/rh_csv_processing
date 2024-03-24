import pandas as pd

class AssetRecord:
    class SellRecord:
        pass

    def __init__(self, name):
        self.name = name
        self.buy_price = []
        self.buy_quan = []
        self.sell_price = []
        self.sell_quan = []
        self.quan = 0
        self.sell_records = []
        self.remaining_quan = []
        self.remaining_basis = []

    def register_buy(self, price, quan):
        self.buy_price.append(price)
        self.buy_quan.append(quan)
        self.remaining_basis.append(price)
        self.remaining_quan.append(quan)
        self.quan += quan
    
    def register_sell(self, price, quan, date):
        self.compute_sell_record(price, quan, date)
        self.sell_price.append(price)
        self.sell_quan.append(quan)
        self.quan -= quan

    def register_split(self, quan):
        rate = quan / self.quan + 1
        self.quan += quan
        for i in range(len(self.buy_quan)):
            self.buy_quan[i] *= rate
        for i in range(len(self.sell_quan)):
            self.sell_quan[i] *= rate
        for i in range(len(self.buy_price)):
            self.buy_price[i] /= rate
        for i in range(len(self.sell_price)):
            self.sell_price[i] /= rate
        for i in range(len(self.remaining_basis)):
            self.remaining_basis[i] /= rate
        for i in range(len(self.remaining_quan)):
            self.remaining_quan[i] *= rate

    def compute_sell_record(self, price, quan, date):     
        quan_temp = quan
        this_quan = []
        this_bases = []
        while quan_temp > 0.0000000001 :
            if quan_temp >= self.remaining_quan[0]:
                this_quan.append(self.remaining_quan[0])
                this_bases.append(self.remaining_basis[0])
                quan_temp -= self.remaining_quan[0]
                self.remaining_quan.pop(0)
                self.remaining_basis.pop(0)
            else:
                this_quan.append(quan_temp)
                this_bases.append(self.remaining_basis[0])
                self.remaining_quan[0] -= quan_temp
                quan_temp = 0

        record = self.SellRecord()
        record.price = price 
        record.quan = quan
        record.proceeds = price * quan
        record.remaining = self.quan - quan
        record.basis = 0
        for i in range(len(this_quan)):
            record.basis += this_quan[i] * this_bases[i]
        record.gain = record.proceeds - record.basis
        record.date = date

        self.sell_records.append(record)

class TransAnalysis:
    def __init__(self, filename):
        self.data = pd.read_csv(filename, parse_dates = True, date_format= "%m/%d/%y")
        self.convert_data()

        self.assets = {}
        
        self.process_io()
        self.process_interest()
        self.process_dividends()
        self.process_buysell()

        self.curr_assets = pd.DataFrame({"Instrument": [], "Quantity": []})
        for key, record in self.assets.items():
            self.curr_assets.loc[len(self.curr_assets)] = [key, record.quan]

        self.sell_records = pd.DataFrame({"SettleDate" : [], "Instument": [], "Quantity": [], "Price": [], "Proceeds": [], "Basis": [], "GainLoss": []})
        for _, asset in self.assets.items():
            for record in asset.sell_records:
                self.sell_records.loc[len(self.sell_records)] = [record.date, asset.name, record.quan, record.price, record.proceeds, record.basis, record.gain]

        self.sell_records = self.sell_records.sort_values(by = ["SettleDate"])
        self.sell_records = self.sell_records.round(2)

    def convert_data(self):
        self.data = self.data.iloc[::-1]
        self.data["Amount"] = self.data["Amount"].str.replace('$', '')
        self.data["Amount"] = self.data["Amount"].str.replace(',', '')
        self.data["Amount"] = self.data["Amount"].str.replace('(', "-").str.rstrip(")")
        self.data["Amount"] = pd.to_numeric(self.data["Amount"])
        self.data["Price"] = self.data["Price"].str.replace('$', '')
        self.data["Price"] = self.data["Price"].str.replace(',', '')
        self.data["Price"] = pd.to_numeric(self.data["Price"])
        self.data["Quantity"] = pd.to_numeric(self.data["Quantity"])
        self.data["ActivityDate"] = pd.to_datetime(self.data["ActivityDate"])
        self.data["ProcessDate"] = pd.to_datetime(self.data["ProcessDate"])
        self.data["SettleDate"] = pd.to_datetime(self.data["SettleDate"])
        self.data["Quantity"] = self.data["Quantity"].fillna(0)
        self.data["Price"] = self.data["Price"].fillna(0)
        self.data["Amount"] = self.data["Amount"].fillna(0)

    def process_io(self):
        self.data_io = self.data.loc[self.data['TransCode'] == "ACH"]
        self.data_io = self.data_io[["SettleDate", "Description", "Amount"]]

    def process_interest(self):       
        self.data_int = self.data.loc[self.data['TransCode'] == "INT"] 
        self.data_int = self.data_int[["SettleDate", "Amount"]]

    def process_dividends(self):
        self.data_div = self.data.loc[self.data['TransCode'] == "CDIV"]
        self.data_div = self.data_div[["SettleDate", "Instrument", "Description", "Amount"]]

    def process_buysell(self):
        self.data_buysell = self.data.loc[self.data['TransCode'].isin(["Buy", "Sell", "SPL", "REC"])] # buy/sell/splits
        print(self.data_buysell.shape[0])
        for index in range(self.data_buysell.shape[0]):
            # get data
            name = self.data_buysell["Instrument"].iloc[index]
            quan = self.data_buysell["Quantity"].iloc[index]
            price = self.data_buysell["Price"].iloc[index]
            date = self.data_buysell["SettleDate"].iloc[index]
            # add a new stock record
            if not name in self.assets.keys():
                self.assets[name] = AssetRecord(name)
            # register transaction
            if self.data_buysell["TransCode"].iloc[index] in ['Buy', 'REC']:
                self.assets[name].register_buy(price, quan)
            elif self.data_buysell["TransCode"].iloc[index] == 'Sell':
                self.assets[name].register_sell(price, quan, date)
            elif self.data_buysell["TransCode"].iloc[index] == 'SPL':
                self.assets[name].register_split(quan)
      
    def print_io(self):
        print(self.data_io)
        print("Total: $", self.data_io["Amount"].sum())
        print()

    def print_interest(self):
        print(self.data_int)
        print("Total: $", self.data_int["Amount"].sum())
        print()

    def print_dividends(self):
        print(self.data_div)
        print("Total: $", self.data_div["Amount"].sum())
        print()

    def print_buysell(self):
        print(self.data_buysell)
        print()

    def print_assets(self):
        print(self.curr_assets)
        print()

    def print_sell(self, write = False, filename = "", year = None):
        if year:
            data = self.sell_records[ (self.sell_records["SettleDate"] >= "%d-1-1" % year) &  (self.sell_records["SettleDate"] <= "%d-12-31" % year) ]
        else: 
            data = self.sell_records
        print(data)
        print("Total Proceeds:", data["Proceeds"].sum().round(2))
        print("Total Costs:", data["Basis"].sum().round(2))
        print("Total Gain/Loss:", data["GainLoss"].sum().round(2))

        print()
        
        if write:
            data.to_csv(filename)

if __name__ == "__main__":
    print(pd.__version__)
    inst = TransAnalysis("robinhood.csv")
    print(inst.data)
    inst.print_io()
    inst.print_interest()
    inst.print_dividends()
    inst.print_buysell()
    inst.print_assets()
    inst.print_sell(write = True, filename= "sell_record.csv", year = 2023)