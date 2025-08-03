# -*- coding: gbk -*-  # 若文件是GBK编码
# 或
# coding=utf-8        # 若文件是UTF-8编码
import pandas as pd
import requests
import json
import time

API_KEY = "sk-klgidfnfvyaetinrtnkblzicwoaztxgkmlfnnpbbvcspzehv"
headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}
url = "https://api.siliconflow.cn/v1/chat/completions"

PROMPT_TEMPLATE = '''
As a biomedical knowledge extraction expert, identify all (entity1, relation, entity2) quadruples with entity types from the given text. 
Follow these guidelines:
1. Output JSON format must be: [{{"entity1": "", "entity1_type": "", "relation": "", "entity2": "", "entity2_type": "", "evidence": ""}}]
2. Entity types must be selected from: [Protein, Gene, Disease, Drug, CellType ,Method,CellComponent, Chemical,Light and electromagneticwave,Tissue and organ,Biologics,BiologicalProcess,Organism,Cell Line],If a new entity_type is found, use 'Others'.
3.You must choose the final relation verb ONLY from this standardized list:

[
  interact_with, inhibit, activate, cause, treat, regulate, express, phosphorylate, 
  bind_to, encode, transcribe, localize_in, transport, metabolize, is_marker_of, induce, located_in,
  suppress,upregulate, downregulate, modulate, prevent, trigger, participate_in,have,from,positively_associate_with, negatively_associate_with
]

DO NOT output relation verbs like "improves", "enhances", "represses", etc. These must always be normalized to the closest match from the list above.

4. Handle complex entities with special symbols (e.g., "TGF-β1" as single entity)
5. Resolve coreferences (e.g., "this protein" refers to previous entity)
6. Entity Recognition Standards:Use standardized biological nomenclature (e.g. ,"EGFR" instead of "epidermal growth factor receptor gene")
7. Relation normalization (map synonymous phrases):
 [activate: "promote", "enhance", "improve", "stimulate", "boost", "facilitate", "play a vital role in", "is essential for",
 inhibit: "reduce", "suppress", "block", "repress", "lower", "negatively regulate", "downregulate", "interfere with",
 cause: "leads to", "induce", "trigger", "result in", "is associated with", "is a key factor in", "underlies",
 regulate: "modulate", "maintain", "control", "balance", "adjust", "fine-tune",
 binds_to: "bind with", "form complex with", "interact with physically", "co-localize",
 treat: "alleviate", "used for", "improve symptoms of", "is effective against",
 prevent: "protect against", "is protective for", "reduce risk of",
 participate_in: "is involved in", "take part in", "contribute to",
 express: only for gene/protein expression activities,
 phosphorylate: only when explicitly stated,
 interact_with: use only for unspecified interactions or when interaction type is unclear]
Ensure all relations in the final output use only one of the allowed standard relation types
8. Entity normalization:
   - If two terms refer to the same concept (e.g., synonyms, abbreviations, aliases), map both to a single standardized name.
   - Use standard biomedical vocabularies (e.g., HGNC for genes, MeSH or UMLS for diseases, ChEBI for chemicals).
   - Examples:
     - "UV radiation", "ultraviolet radiation", "UVR" change to "ultraviolet radiation"
     - "EGFR", "epidermal growth factor receptor" change to "EGFR"
     - "heart attack", "myocardial infarction" change to "myocardial infarction"
   - Always use the canonical form in the output.
9. All forms of relational verbs should be changed to their base forms.(e.g. ,"inhibits", "activates", "causes","participates_in","" change to "inhibit", "activate", "cause","participate_in")
10. Before deciding the relation, identify which entity is the controller (cause/source/initiator) and which is the target (effect/outcome).
11.If the sentence is in passive voice (e.g., "X is activated by Y"), you must rewrite it in active voice ("Y activate X"). Ensure the direction of the relation is biologically and syntactically correct.
12. You must return the sentence as "evidence".
13.Only output a single pure JSON array. No markdown, no explanations, no text outside the array. If you include anything else, the answer will be rejected.


Example:
Text: "BRCA1 mutation causes breast cancer by disrupting DNA repair pathways." 
Output: [
    {{"entity1": "BRCA1", "entity1_type": "Gene", "relation": "cause", "entity2": "breast cancer", "entity2_type": "Disease", "evidence": "BRCA1 mutation causes breast cancer by disrupting DNA repair pathways."}},
    {{"entity1": "BRCA1", "entity1_type": "Gene", "relation": "disrupt", "entity2": "DNA repair pathways", "entity2_type": "BiologicalProcess", "evidence": "BRCA1 mutation causes breast cancer by disrupting DNA repair pathways."}}
]

Text: "U.V.radiation causes skin cancer."
Output: [
    {{"entity1": "ultraviolet radiation", "entity1_type": "Light and electromagneticwave","relation": "cause","entity2": "skin cancer", "entity2_type": "Disease","evidence":"U.V.radiation causes skin cancer."}}
]
Text: "IL-6 improved immune response in mice."
Output:
[
  {{"entity1": "IL-6", "entity1_type": "Protein", "relation": "activate", "entity2": "immune response", "entity2_type": "BiologicalProcess","evidence":"IL-6 improved immune response in mice."}}
]


Now process this biomedical text:
{}
'''


def extract_triples(text):
    payload = {
        "model": "deepseek-ai/DeepSeek-V3",
        "messages": [{"role": "user", "content": PROMPT_TEMPLATE.format(text)}],
        "stream": False,
        "max_tokens": 3000
    }
    for _ in range(3):  # 重试机制
        try:
            r = requests.request("POST", url, json=payload, headers=headers)
            output = r.json()
            output = output["choices"][0]["message"]["content"]
            return json.loads(output)
        except:
            time.sleep(2)
    return []


import concurrent.futures


def extract_triples_from_csv(input_csv, output_json, top_n=10, max_workers=3):
    df = pd.read_csv(input_csv, encoding='ansi')
    df = df[df["abstract_text"].notnull()].iloc[:top_n]
    all_triples = []

    # 使用线程池并行处理
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        # 提交所有任务
        future_to_text = {
            executor.submit(extract_triples, text): text
            for text in df["abstract_text"]
        }

        # 异步收集结果
        for future in concurrent.futures.as_completed(future_to_text):
            try:
                triples = future.result()
                all_triples.extend(triples)
            except Exception as e:
                print(f"处理失败: {str(e)}")

    # 保存结果
    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(all_triples, f, indent=2, ensure_ascii=False)
