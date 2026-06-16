import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

# Lớp GUI nhận dữ liệu sạch từ BLL và hiển thị lên màn hình
class PresentationLayer:
    def __init__(self, bll):
        self.bll = bll

    def plot_intraday_price_volume(self, symbol, target_date):
        data = self.bll.get_intraday_data(symbol, target_date)
        if data.empty: return
            
        fig, ax1 = plt.subplots(figsize=(10, 6))
        ax1.plot(data['scrape_time'], data['close'], color='blue', label='Giá đóng cửa')
        ax1.set_xlabel('Thời gian')
        ax1.set_ylabel('Giá đóng cửa', color='blue')
        ax1.tick_params(axis='y', labelcolor='blue')
        
        ax2 = ax1.twinx()
        ax2.bar(data['scrape_time'], data['volume'], color='gray', alpha=0.3, width=0.002, label='Khối lượng')
        ax2.set_ylabel('Khối lượng', color='gray')
        ax2.tick_params(axis='y', labelcolor='gray')
        
        plt.title(f'Biểu đồ Giá và Khối lượng trong ngày - {symbol} ({target_date})')
        fig.tight_layout()
        plt.show()

    def plot_intraday_vwap(self, symbol, target_date):
        data = self.bll.get_vwap_data(symbol, target_date)
        if data.empty: return
            
        plt.figure(figsize=(10, 6))
        plt.plot(data['scrape_time'], data['close'], label='Giá đóng cửa', color='black', alpha=0.6)
        plt.plot(data['scrape_time'], data['vwap'], label='Đường VWAP', color='red', linewidth=2)
        plt.title(f'Trung bình giá gia quyền theo khối lượng (VWAP) - {symbol} ({target_date})')
        plt.xlabel('Thời gian')
        plt.ylabel('Giá')
        plt.legend()
        plt.grid(True, linestyle='--', alpha=0.5)
        plt.tight_layout()
        plt.show()

    def plot_daily_candlestick(self, symbol, start_date, end_date):
        data = self.bll.get_daily_data(symbol, start_date, end_date)
        if data.empty: return
            
        plt.figure(figsize=(12, 6))
        up = data[data['close'] >= data['open']]
        down = data[data['close'] < data['open']]
        width, width2 = 0.6, 0.05
        
        plt.bar(up['trading_date'], up['close'] - up['open'], width, bottom=up['open'], color='green')
        plt.bar(up['trading_date'], up['high'] - up['low'], width2, bottom=up['low'], color='green')
        plt.bar(down['trading_date'], down['close'] - down['open'], width, bottom=down['open'], color='red')
        plt.bar(down['trading_date'], down['high'] - down['low'], width2, bottom=down['low'], color='red')
        
        plt.title(f'Biểu đồ Nến Nhật - {symbol}')
        plt.xlabel('Ngày giao dịch')
        plt.ylabel('Giá')
        plt.grid(True, linestyle='--', alpha=0.5)
        plt.tight_layout()
        plt.show()

    def plot_daily_moving_average(self, symbol, start_date, end_date, ma1=10, ma2=20):
        data = self.bll.get_ma_data(symbol, start_date, end_date, ma1, ma2)
        if data.empty: return
            
        plt.figure(figsize=(12, 6))
        plt.plot(data['trading_date'], data['close'], label='Giá đóng cửa', color='black', linewidth=1.5)
        plt.plot(data['trading_date'], data[f'MA{ma1}'], label=f'Trung bình {ma1} ngày', color='blue', linestyle='--')
        plt.plot(data['trading_date'], data[f'MA{ma2}'], label=f'Trung bình {ma2} ngày', color='red', linestyle='--')
        plt.title(f'Đường trung bình động (MA) - {symbol}')
        plt.xlabel('Ngày giao dịch')
        plt.ylabel('Giá đóng cửa')
        plt.legend()
        plt.grid(True, linestyle='--', alpha=0.5)
        plt.tight_layout()
        plt.show()

    def plot_daily_volume(self, symbol, start_date, end_date):
        data = self.bll.get_daily_volume_color_data(symbol, start_date, end_date)
        if data.empty: return
            
        plt.figure(figsize=(12, 6))
        plt.bar(data['trading_date'], data['volume'], color=data['color'])
        
        green_patch = mpatches.Patch(color='green', label='Giá tăng')
        red_patch = mpatches.Patch(color='red', label='Giá giảm')
        plt.legend(handles=[green_patch, red_patch], loc='upper left')
        
        plt.title(f'Khối lượng giao dịch hàng ngày - {symbol}')
        plt.xlabel('Ngày giao dịch')
        plt.ylabel('Khối lượng')
        plt.grid(True, axis='y', linestyle='--', alpha=0.5)
        plt.tight_layout()
        plt.show()

    def plot_monthly_volatility(self, symbol, target_year):
        data = self.bll.get_monthly_data(symbol, target_year)
        if data.empty: return
            
        months = sorted(data['month'].unique())
        plot_data = [data[data['month'] == m]['close'].dropna() for m in months]
        
        plt.figure(figsize=(10, 6))
        plt.boxplot(plot_data, labels=months)
        plt.title(f'Phân phối biến động giá theo tháng - {symbol} ({target_year})')
        plt.xlabel('Tháng')
        plt.ylabel('Giá đóng cửa')
        plt.grid(True, axis='y', linestyle='--', alpha=0.5)
        plt.tight_layout()
        plt.show()

    def plot_yearly_stacked_volume(self, target_years=None):
        pivot_data = self.bll.get_yearly_stacked_data(target_years)
        if pivot_data is None: return
            
        ax = pivot_data.plot(kind='bar', stacked=True, figsize=(10, 6), colormap='viridis')
        totals = pivot_data.sum(axis=1)
        for i, total in enumerate(totals):
            ax.text(i, total, f'{total:,.0f}', ha='center', va='bottom', fontsize=10)
        
        plt.xticks(rotation=0)
        title_suffix = f" ({', '.join(map(str, target_years))})" if target_years else " (Tất cả các năm)"
        plt.title(f'So sánh thanh khoản dài hạn theo năm{title_suffix}')
        plt.xlabel('Năm')
        plt.ylabel('Tổng khối lượng giao dịch')
        plt.legend(title='Mã cổ phiếu')
        plt.grid(True, axis='y', linestyle='--', alpha=0.5)
        plt.tight_layout()
        plt.show()