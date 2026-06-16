import pandas as pd
import requests

# Lớp xử lý kết nối Apache Drill và chuẩn hóa dữ liệu từ file CSV không có header
class DataAccessLayer:
    def __init__(self, vm_ip, hdfs_path):
        self.url = f"http://{vm_ip}:8047/query.json"
        self.hdfs_path = hdfs_path

    def load_data(self):
        expected_cols = ['symbol', 'trading_date', 'scrape_time', 'source', 'close', 'volume', 'open', 'high', 'low']
        
        sql = f"""
        SELECT 
            columns[0] AS symbol,
            columns[1] AS trading_date,
            columns[2] AS scrape_time,
            columns[3] AS source,
            columns[4] AS close,
            columns[5] AS volume,
            columns[6] AS open,
            columns[7] AS high,
            columns[8] AS low
        FROM table(dfs.`{self.hdfs_path}` (type => 'text', fieldDelimiter => ',', extractHeader => false))
        """
        
        payload = {"queryType": "SQL", "query": sql}
        headers = {"Content-Type": "application/json"}
        
        try:
            response = requests.post(self.url, json=payload, headers=headers)
            if response.status_code == 200:
                rows = response.json().get("rows", [])
                
                if not rows:
                    print(f"Cảnh báo: Không có dữ liệu trả về từ Drill tại đường dẫn {self.hdfs_path}")
                    return pd.DataFrame(columns=expected_cols)
                
                df = pd.DataFrame(rows)
                
                df['trading_date'] = pd.to_datetime(df['trading_date'])
                if 'scrape_time' in df.columns:
                    df['scrape_time'] = pd.to_datetime(df['scrape_time'], errors='coerce')
                
                numeric_cols = ['close', 'volume', 'open', 'high', 'low']
                for col in numeric_cols:
                    if col in df.columns:
                        df[col] = pd.to_numeric(df[col], errors='coerce')
                        
                return df
            else:
                print("Lỗi từ Drill:", response.text)
                return pd.DataFrame(columns=expected_cols)
        except Exception as e:
            print("Kết nối thất bại:", str(e))
            return pd.DataFrame(columns=expected_cols)