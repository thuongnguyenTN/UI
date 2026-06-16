from data_access import DataAccessLayer
from business_logic import BusinessLogicLayer
from presentation import PresentationLayer

if __name__ == "__main__":
    vm_ip = "100.80.217.65"
    hdfs_path = "/user/hadoop/stock_cleaned_csv"
    
    dal = DataAccessLayer(vm_ip, hdfs_path)
    bll = BusinessLogicLayer(dal)
    gui = PresentationLayer(bll)
    
    # gui.plot_intraday_price_volume(symbol="VCB", target_date="2026-06-16")
    # gui.plot_intraday_vwap(symbol="VCB", target_date="2026-06-09")
    gui.plot_daily_candlestick(symbol="VCB", start_date="2026-06-01", end_date="2026-06-16")
    # gui.plot_daily_moving_average(symbol="VCB", start_date="2025-01-01", end_date="2026-06-09")
    # gui.plot_daily_volume(symbol="VCB", start_date="2026-05-01", end_date="2026-06-09")
    # gui.plot_monthly_volatility(symbol="VCB", target_year="2025")
    # gui.plot_yearly_stacked_volume(target_years=[2024, 2025, 2026])