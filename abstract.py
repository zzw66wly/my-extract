import requests
import json
import time

# --- ���� ---
# ���û��API Key��ȷ�������ǿյ��ַ���
SEMANTIC_SCHOLAR_API_KEY = "" # ���ձ�ʾû��API Key

BASE_URL = "https://api.semanticscholar.org/graph/v1/paper/search/bulk"
QUERY_TERM = "skin cells" # ��������ؼ���
TARGET_PAPERS = 100000 # Ŀ���ȡ����������
PAPERS_PER_REQUEST = 100 # ÿ��API�����ȡ���������� (���100)

# ���������ֶ�
FIELDS = "paperId,title,abstract"

# ��������ͷ
headers = {}
if SEMANTIC_SCHOLAR_API_KEY:
    headers["x-api-key"] = SEMANTIC_SCHOLAR_API_KEY
    # ����API Key����������ͨ����1 RPS (request per second)
    WAIT_TIME_SECONDS = 1
else:
    # **��API Key������������ÿ5����100������**
    # ����ζ��ÿ������֮����Ҫ�ȴ����� 300�� / 100���� = 3��
    # ��������һ�������صĵȴ�ʱ�䣬���������Ի���
    WAIT_TIME_SECONDS = 3.5 # ÿ������֮��ĵȴ�ʱ��
    # ���429����Ķ���ȴ�ʱ��
    RATE_LIMIT_WAIT_SECONDS = 60 # ����429ʱ�ȴ�60�룬��Ϊ����5����/100����

all_papers = []
current_offset = 0
retry_count = 0
MAX_RETRIES = 5 # ������Դ���

print(f"��ʼ���� '{QUERY_TERM}' ��ص����� (��API Keyģʽ)...")

while len(all_papers) < TARGET_PAPERS:
    params = {
        "query": QUERY_TERM,
        "fields": FIELDS,
        "limit": PAPERS_PER_REQUEST,
        "offset": current_offset,
        "min_publication_date":"2015-01-01"
    }

    print(f"���Ի�ȡ��offset={current_offset}, limit={PAPERS_PER_REQUEST}")

    try:
        response = requests.get(BASE_URL, headers=headers, params=params)
        response.raise_for_status() # ���HTTP����
        data = response.json()

        papers_batch = data.get("data", [])
        total_results = data.get("total", 0) # API���ܷ����ܽ����

        if not papers_batch:
            print("δ��ȡ���������ס������Ѵ�����������޻�û�и���ƥ���")
            break

        all_papers.extend(papers_batch)
        current_offset += len(papers_batch)
        retry_count = 0 # �ɹ����������Լ���

        print(f"�ѻ�ȡ {len(all_papers)} / {TARGET_PAPERS} ƪ���ס��ܼƿ��ܽ��: {total_results}")

        # ����Ѿ��ﵽĿ���������ѻ�ȡ���п��ý������ֹͣ
        if len(all_papers) >= TARGET_PAPERS or (total_results > 0 and current_offset >= total_results):
            print("�ѴﵽĿ�������������ѻ�ȡ���п������ס�")
            break

        # ������������
        print(f"�ȴ� {WAIT_TIME_SECONDS} ����������������...")
        time.sleep(WAIT_TIME_SECONDS)

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 429: # Too Many Requests
            retry_count += 1
            if retry_count <= MAX_RETRIES:
                print(f"������������ (429)���� {retry_count} �����ԡ��ȴ� {RATE_LIMIT_WAIT_SECONDS} ��...")
                time.sleep(RATE_LIMIT_WAIT_SECONDS) # ����429ʱ�ȴ�����ʱ��
            else:
                print(f"��δ����������ƣ��ﵽ������Դ��� ({MAX_RETRIES})����ֹ��")
                break
        else:
            print(f"HTTP ����: {e.response.status_code} - {e.response.text}")
            break # ����HTTP����ֱ���˳�
    except requests.exceptions.RequestException as e:
        print(f"�������: {e}")
        break
    except json.JSONDecodeError:
        print("JSON ������󣬿�����Ӧ������Ч�� JSON��")
        break

print(f"\n���ճɹ���ȡ {len(all_papers)} ƪ���ס�")

# ���������ױ��浽 JSON �ļ�
output_filename = "skin_cells_papers_others.json"
with open(output_filename, 'w', encoding='utf-8') as f:
    json.dump(all_papers, f, ensure_ascii=False, indent=2)

print(f"\n�������������ѱ��浽 {output_filename}")