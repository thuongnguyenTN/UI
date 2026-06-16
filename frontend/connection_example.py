import requests

def query_drill(vm_ip, sql):
    #Thuc thi truy van SQL toi Apache Drill qua REST API va tra ve danh sach ket qua
    url = f"http://{vm_ip}:8047/query.json"
    payload = {"queryType": "SQL", "query": sql}
    headers = {"Content-Type": "application/json"}
    try:
        response = requests.post(url, json=payload, headers=headers)
        if response.status_code == 200:
            return response.json().get("rows", [])
        else:
            print("Error:", response.text)
            return []
    except Exception as e:
        print("Connection failed:", str(e))
        return []

if __name__ == "__main__":
    vm_ip = "100.80.217.65"

    print("1. QUERY MAU TOI MYSQL")
    mysql_query = "SHOW TABLES IN mysql_db"
    mysql_rows = query_drill(vm_ip, mysql_query)
    print(mysql_rows)

    print("\n2. QUERY MAU TOI HDFS (DA ADD HEADER & CAST TEXT)")
    hdfs_query = """
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
    FROM table(dfs.`/user/hadoop/stock_cleaned_csv/000000_0` (type => 'text', fieldDelimiter => ',', extractHeader => false)) 
    LIMIT 5
    """
    hdfs_rows = query_drill(vm_ip, hdfs_query)
    print(hdfs_rows)