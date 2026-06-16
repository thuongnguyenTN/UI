import pandas as pd
import numpy as np

# Lớp BLL xử lý logic tính toán, gom nhóm và chuẩn bị dữ liệu cho biểu đồ
class BusinessLogicLayer:
    def __init__(self, dal):
        self.df = dal.load_data()

    def get_intraday_data(self, symbol, target_date):
        mask = (self.df['symbol'] == symbol) & (self.df['trading_date'].dt.strftime('%Y-%m-%d') == target_date)
        return self.df[mask].sort_values('scrape_time')

    def get_vwap_data(self, symbol, target_date):
        data = self.get_intraday_data(symbol, target_date).copy()
        if not data.empty:
            data['vwap'] = (data['volume'] * data['close']).cumsum() / data['volume'].cumsum()
        return data

    def get_daily_data(self, symbol, start_date, end_date):
        mask = (self.df['symbol'] == symbol) & (self.df['trading_date'] >= start_date) & (self.df['trading_date'] <= end_date)
        df_filtered = self.df[mask].sort_values(['trading_date', 'scrape_time'])
        daily_df = df_filtered.groupby('trading_date').agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        }).reset_index()
        return daily_df

    def get_ma_data(self, symbol, start_date, end_date, ma1, ma2):
        data = self.get_daily_data(symbol, start_date, end_date).copy()
        if not data.empty:
            data[f'MA{ma1}'] = data['close'].rolling(window=ma1).mean()
            data[f'MA{ma2}'] = data['close'].rolling(window=ma2).mean()
        return data

    def get_daily_volume_color_data(self, symbol, start_date, end_date):
        data = self.get_daily_data(symbol, start_date, end_date).copy()
        if not data.empty:
            data['prev_close'] = data['close'].shift(1)
            data['color'] = np.where(data['close'] >= data['prev_close'], 'green', 'red')
            data.loc[0, 'color'] = 'green'
        return data

    def get_monthly_data(self, symbol, target_year):
        daily_data = self.get_daily_data(symbol, f"{target_year}-01-01", f"{target_year}-12-31")
        if not daily_data.empty:
            daily_data['month'] = daily_data['trading_date'].dt.month
        return daily_data

    def get_yearly_stacked_data(self, target_years):
        data = self.df.copy()
        data['year'] = data['trading_date'].dt.year
        if target_years is not None:
            if not isinstance(target_years, list):
                target_years = [target_years]
            target_years = [int(y) for y in target_years]
            data = data[data['year'].isin(target_years)]
        if data.empty:
            return None
        return data.groupby(['year', 'symbol'])['volume'].sum().unstack()