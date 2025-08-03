import requests
import json
import time

# --- 配置 ---
# 如果没有API Key，确保这里是空的字符串
SEMANTIC_SCHOLAR_API_KEY = "" # 留空表示没有API Key

BASE_URL = "https://api.semanticscholar.org/graph/v1/paper/search/bulk"
QUERY_TERM = "skin cells" # 你的搜索关键词
TARGET_PAPERS = 100000 # 目标获取的文献数量
PAPERS_PER_REQUEST = 100 # 每次API请求获取的文献数量 (最大100)

# 包含所需字段
FIELDS = "paperId,title,abstract"

# 设置请求头
headers = {}
if SEMANTIC_SCHOLAR_API_KEY:
    headers["x-api-key"] = SEMANTIC_SCHOLAR_API_KEY
    # 带有API Key的速率限制通常是1 RPS (request per second)
    WAIT_TIME_SECONDS = 1
else:
    # **无API Key的速率限制是每5分钟100个请求**
    # 这意味着每次请求之间需要等待至少 300秒 / 100请求 = 3秒
    # 我们设置一个更保守的等待时间，并加上重试机制
    WAIT_TIME_SECONDS = 3.5 # 每次请求之间的等待时间
    # 针对429错误的额外等待时间
    RATE_LIMIT_WAIT_SECONDS = 60 # 遇到429时等待60秒，因为它是5分钟/100请求

all_papers = []
current_offset = 0
retry_count = 0
MAX_RETRIES = 5 # 最大重试次数

print(f"开始搜索 '{QUERY_TERM}' 相关的文献 (无API Key模式)...")

while len(all_papers) < TARGET_PAPERS:
    params = {
        "query": QUERY_TERM,
        "fields": FIELDS,
        "limit": PAPERS_PER_REQUEST,
        "offset": current_offset,
        "min_publication_date":"2015-01-01"
    }

    print(f"尝试获取：offset={current_offset}, limit={PAPERS_PER_REQUEST}")

    try:
        response = requests.get(BASE_URL, headers=headers, params=params)
        response.raise_for_status() # 检查HTTP错误
        data = response.json()

        papers_batch = data.get("data", [])
        total_results = data.get("total", 0) # API可能返回总结果数

        if not papers_batch:
            print("未获取到更多文献。可能已达搜索结果上限或没有更多匹配项。")
            break

        all_papers.extend(papers_batch)
        current_offset += len(papers_batch)
        retry_count = 0 # 成功后重置重试计数

        print(f"已获取 {len(all_papers)} / {TARGET_PAPERS} 篇文献。总计可能结果: {total_results}")

        # 如果已经达到目标数量或已获取所有可用结果，则停止
        if len(all_papers) >= TARGET_PAPERS or (total_results > 0 and current_offset >= total_results):
            print("已达到目标文献数量或已获取所有可用文献。")
            break

        # 遵守速率限制
        print(f"等待 {WAIT_TIME_SECONDS} 秒以遵守速率限制...")
        time.sleep(WAIT_TIME_SECONDS)

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 429: # Too Many Requests
            retry_count += 1
            if retry_count <= MAX_RETRIES:
                print(f"触发速率限制 (429)，第 {retry_count} 次重试。等待 {RATE_LIMIT_WAIT_SECONDS} 秒...")
                time.sleep(RATE_LIMIT_WAIT_SECONDS) # 遇到429时等待更长时间
            else:
                print(f"多次触发速率限制，达到最大重试次数 ({MAX_RETRIES})，终止。")
                break
        else:
            print(f"HTTP 错误: {e.response.status_code} - {e.response.text}")
            break # 其他HTTP错误直接退出
    except requests.exceptions.RequestException as e:
        print(f"请求错误: {e}")
        break
    except json.JSONDecodeError:
        print("JSON 解码错误，可能响应不是有效的 JSON。")
        break

print(f"\n最终成功获取 {len(all_papers)} 篇文献。")

# 将所有文献保存到 JSON 文件
output_filename = "skin_cells_papers_others.json"
with open(output_filename, 'w', encoding='utf-8') as f:
    json.dump(all_papers, f, ensure_ascii=False, indent=2)

print(f"\n所有文献数据已保存到 {output_filename}")