# -*- coding: gbk -*-  # ���ļ���GBK����
# ��
# coding=utf-8        # ���ļ���UTF-8����
from triple_extraction import extract_triples_from_csv
#from triple_extraction2 import extract_triples_from_csv
from normalize_module import normalize_all_triples
from relationstander import normalize_triples_with_relations
from neo4j_loader import build_kg_direct
from analysis_skin import run_analysis_pipeline
from repurposing_skin import repurpose_skin
import shutil
import os


# 1. ��ȡ
raw_csv = "data/raw.csv"
raw_output = "data/raw_triples.json"
extract_triples_from_csv(raw_csv, raw_output, top_n=1100,max_workers=4)  # top_n ���Ƴ�ȡ����
raw_output = "C:\\Users\\hi\\Documents\\SimpleGermKG-main\\new_triple.json"
# 2. ��׼��
normalized_output = "data/new_triples2.json"

#normalize_all_triples(raw_output, normalized_output)
normalize_triples_with_relations(raw_output, normalized_output,max_workers=3)
# 3. ����ͼ��
import json
#data = json.load(open(normalized_output, encoding="utf-8"))
#build_kg_direct(data)

print(" Pipeline ��ɣ�ͼ���ѹ�����")
'''
# 4. ·�������������ӻ��Գɷַ���
RELlist = json.load(open("data/aggregated_relations.json", encoding="utf-8"))  # ��ǰ���ɺ�
entDict = json.load(open("data/entDict.json", encoding="utf-8"))
entSubtype = json.load(open("data/entSubtype.json", encoding="utf-8"))
entName = json.load(open("data/entName.json", encoding="utf-8"))
os.makedirs("DrugRepurposing_result", exist_ok=True)

# ����Ŀ��������̣�Ƥ�����﹦�ܣ�
target_id = "E51715287"
target_type = "Disease"
time_start = "2020-01-01"
time_end = "2025-01-01"
'''
# �������
#repurpose_skin(target_id, target_type, time_start, time_end,RELlist, entDict, entSubtype, entName, output_dir="DrugRepurposing_result")



#run_analysis_pipeline(input_dir="DrugRepurposing_result",output_dir="analysis_result",min_score=0.5,top_k=50)


