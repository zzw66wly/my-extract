# -*- coding: gbk -*-  # 若文件是GBK编码
# 或
# coding=utf-8        # 若文件是UTF-8编码
import json
import re
import requests
import spacy
from concurrent.futures import ThreadPoolExecutor, as_completed

# 载入 spaCy 英文模型（注意需要先安装 en_core_web_sm）
nlp = spacy.load("en_core_web_sm")

API_KEY = ""
URL = "https://api.siliconflow.cn/v1/chat/completions"
HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

RELATION_SET = [
    "acts_on", "promotes", "inhibits", "induces", "treats", "involved_in", "expresses",
    "subordinate", "transports", "activates", "regulates", "protects", "synergizes_with",
    "directly_interacts"
]

# ---------------- 规则匹配 ----------------
def rule_match_relation(relation):
    text = relation.lower()

    RULE_KEYWORDS = {
        "acts_on": ["act on", "acts on"],
        "promotes": ["promote", "enhance", "increase","promote", "stimulate", "activate", "upregulate", "enhance", "increase", "facilitate", "reconstitute", "drive", "mediate", "assemble", "differentiate", "transplant", "generate", "combine", "contribute", "help", "assist", "stimulate", "upregulate"],
        "inhibits": ["inhibit", "suppress", "block", "prevent","inhibit", "downregulate", "prevent", "reduce", "decrease", "negate", "disrupt", "damage", "restrict", "resist", "isolate", "eliminate", "suppress", "block", "counteract", "restrain"],
        "induces": ["induce", "trigger", "cause","induce", "trigger", "cause", "initiate", "generate", "release", "expose", "lead to", "drive", "invade", "transport", "secrete", "provoke", "stimulate", "elicit"],
        "treats": ["treat", "therapy", "used for", "cure","treat", "repair", "protect", "heal", "cure", "modulate", "apply", "reconfigure", "eliminate", "mediate", "rescue", "alleviate", "restore", "remedy"],
        "involved_in": ["involved in", "play a role", "responsible for","participate", "interact", "associate", "engage", "collaborate", "contribute", "modulate", "signal", "transduce", "bind", "communicate", "cooperate", "involve", "link", "connect"],
        "expresses": ["express", "expressed","express", "show", "exhibit", "display", "confirm", "identify", "disclose", "recognize", "sense", "illustrate", "marker_of", "encode", "signal", "perceive", "profile", "localize", "located_in", "secrete", "transcribe"],
        "subordinate": ["is a", "classified as", "belongs to", "type of","have", "contain", "include", "belong", "possess", "own", "incorporate", "consist of", "be", "use", "apply", "allow", "enable", "act", "self-organize", "store", "transfer", "modify", "bind", "sense", "occur", "are", "is", "provide"],
        "transports": ["transport", "carry"],
        "activates": ["activate", "stimulate"],
        "regulates": ["regulate", "control", "modulate"],
        "protects": ["protect", "defend", "prevent damage"],
        "synergizes_with": ["synergize", "work with", "cooperate with"],
        "directly_interacts": ["interact", "bind to", "associate with"]
    }

    for relation_type, keywords in RULE_KEYWORDS.items():
        for keyword in keywords:
            if keyword in text:
                return relation_type

    return None

# ---------------- 被动语态判断（spacy） ----------------
def is_passive_voice(phrase):
    doc = nlp(phrase)
    for token in doc:
        if token.dep_ == "auxpass":  # 被动语态助动词
            return True
    return False

# ---------------- API 调用：关系标准化 ----------------
def normalize_relation_api(relation):
    prompt = f"""
You are a biomedical relation normalizer.

Your task is to classify a relation phrase into one of the following predefined types:
{', '.join(f'\"{r}\"' for r in RELATION_SET)}.

If no close match can be found, return "others".

Rules:
- Return only one of the listed relation types or "others".
- No explanation.
- Output a single word (not in JSON array).
- Must return a word.

Examples:
Input: "is able to inhibit"
Output relation: inhibits

Input: "can promote"
Output relation: promotes

Input: "plays a role in"
Output relation: involved_in

Input: "help with treatment of"
Output relation: treats

Input:"Ginseng is a traditional herbal medicine"
Output relation: subordinate

Now classify:
Input: "{relation}"
Output:
"""

    payload = {
        "model": "Pro/deepseek-ai/DeepSeek-V3-1226",
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "max_tokens": 3000
    }

    try:
        r = requests.post(URL, headers=HEADERS, json=payload, timeout=20)
        content = r.json()["choices"][0]["message"]["content"]
        result = content.strip().splitlines()[0]
        return result if result in RELATION_SET else "others"
    except Exception as e:
        print(f"[!!] API 标准化失败: {relation} -> {e}")
        return "others"

# ---------------- 主函数 ----------------
def normalize_triples_with_relations(input_path, output_path, max_workers=3):
    with open(input_path, encoding="utf-8") as f:
        raw_data = json.load(f)

    data = [
        t for t in raw_data
        if all(k in t for k in ("entity1", "entity1_type", "entity2", "entity2_type", "relation"))
    ]

    relation_cache = {}
    passive_map = {}
    all_relations = list(set(t["relation"] for t in data))
    to_query_llm = []

    for r in all_relations:
        rule_result = rule_match_relation(r)
        passive_map[r] = is_passive_voice(r)  # 在标准化前提取
        if rule_result:
            relation_cache[r.lower()] = rule_result
        else:
            to_query_llm.append(r)

    def worker(rel):
        return rel, normalize_relation_api(rel)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_rel = {executor.submit(worker, r): r for r in to_query_llm}
        for future in as_completed(future_to_rel):
            r, norm = future.result()
            relation_cache[r.lower()] = norm

    normalized = []
    for t in data:
        raw_rel = t["relation"]
        norm_rel = relation_cache.get(raw_rel.lower(), "others")
        is_passive = passive_map.get(raw_rel, False)

        if is_passive:
            norm = {
                "entity1": t["entity2"],
                "entity1_type": t["entity2_type"],
                "relation": norm_rel,
                "entity2": t["entity1"],
                "entity2_type": t["entity1_type"],
                "evidence": t.get("evidence", "")
            }
        else:
            norm = {
                "entity1": t["entity1"],
                "entity1_type": t["entity1_type"],
                "relation": norm_rel,
                "entity2": t["entity2"],
                "entity2_type": t["entity2_type"],
                "evidence": t.get("evidence", "")
            }

        normalized.append(norm)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(normalized, f, indent=2, ensure_ascii=False)

    print(f"[?] 完成标准化：总计 {len(normalized)} 条关系。")




