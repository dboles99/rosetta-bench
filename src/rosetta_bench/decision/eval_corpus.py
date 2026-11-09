"""Generator for corpus/decision_v1: decision-eval items whose gold answers are known
by construction, never taken from a provider.

Every item is one member of a minimal pair (or a small family) built by applying a
known transformation to a base: drop a required sentence, change a number, negate,
hedge, corrupt a note, change a packet value, reorder packet lines, and so on. The
transformation decides the gold answer. Rosetta artifacts are produced with
rosetta_core (render_human_doc, serialize_packet) and Rosetta source excerpts are read
from the installed rosetta_core, so the evidence is the real thing.

intervention_level has no construction-based gold; its author estimates are marked
author_unreviewed and reported separately.

Regenerate:  python -m rosetta_bench.decision.eval_corpus corpus/decision_v1
"""
from __future__ import annotations

import inspect
import json
import sys
from pathlib import Path

from rosetta_core import loader as core_loader
from rosetta_core import sync as core_sync
from rosetta_core.cpn import parse_packet, serialize_packet
from rosetta_core.human_doc import extract_fields_comment, render_human_doc

CORPUS_NAME = "decision_v1"
CORPUS_VERSION = "1.0"
SCHEMA_VER = "1.0"


def _item(item_id, qset, category, language, family, evidence, gold, construction, subset=None, unreviewed=None):
    item = {"item_id": item_id, "qset": qset, "category": category, "language": language, "family": family,
            "subset": subset, "data_class": "synthetic", "evidence": evidence}
    label = {"item_id": item_id, "gold": gold, "gold_source": "construction", "construction": construction}
    if unreviewed:
        label["unreviewed"] = unreviewed
    return item, label


# --- requirements_sufficient (+ unreviewed intervention_level) -----------------------------------
# Each scenario: (language, [(required item, sentence carrying it)], index of the item dropped).
_REQUIREMENTS = [
    ("en", [("word count", "The manuscript is about 6,500 words."),
            ("deadline", "I need the edited file back by 20 November."),
            ("subject area", "It is a clinical oncology paper.")], 1),
    ("en", [("source language", "The source text is in Korean."),
            ("target language", "It should be translated into British English."),
            ("word count", "It is 420 words long."),
            ("deadline", "I need it by Friday 14 November.")], 1),
    ("en", [("target journal", "I am submitting to the Journal of Applied Ecology."),
            ("reference style", "References must follow APA 7th edition."),
            ("word count", "The main text is 7,200 words.")], 1),
    ("en", [("metric", "I need the monthly revenue figures."),
            ("date range", "Cover January to June 2026."),
            ("region", "Include the Taiwan office only.")], 2),
    ("zh", [("字數", "稿件約 5,800 字。"),
            ("截止日期", "請於 11 月 25 日前交回。"),
            ("學科領域", "這是一篇材料科學論文。")], 2),
    ("zh", [("原文語言", "原文是繁體中文。"),
            ("目標語言", "需要翻譯成英文。"),
            ("字數", "全文約 1,200 字。")], 2),
    ("zh", [("期刊名稱", "預計投稿至《應用生態學期刊》。"),
            ("引用格式", "參考文獻須採用 APA 第 7 版格式。"),
            ("截止日期", "請在 12 月 3 日前完成。")], 0),
    ("ja", [("語数", "原稿は約4,000語です。"),
            ("納期", "12月1日までに納品をお願いします。"),
            ("分野", "分野は経済学です。")], 1),
    ("ja", [("原文の言語", "原文は日本語です。"),
            ("訳文の言語", "英語に翻訳してください。"),
            ("文字数", "全体で約3,000文字です。")], 1),
    ("ja", [("投稿先ジャーナル", "投稿先は『応用生態学ジャーナル』です。"),
            ("参考文献の形式", "参考文献はAPA第7版の形式にしてください。"),
            ("語数", "本文は約6,000語です。")], 0),
]


def _requirements():
    out = []
    joiner = {"en": " ", "zh": "", "ja": ""}
    for n, (lang, parts, drop) in enumerate(_REQUIREMENTS, start=1):
        family = f"req-{lang}-{n:02d}"
        required = [name for name, _ in parts]
        for variant, keep in (("complete", parts), ("missing", [p for i, p in enumerate(parts) if i != drop])):
            evidence = {"request.text": joiner[lang].join(sentence for _, sentence in keep), "requirements.list": required}
            sufficient = variant == "complete"
            construction = ("all required sentences present" if sufficient
                            else f"dropped the sentence carrying {parts[drop][0]!r}")
            out.append(_item(f"{family}-{variant}", "requirements", variant, lang, family, evidence,
                             {"requirements_sufficient": sufficient, "intervention_level": None}, construction,
                             unreviewed={"intervention_level": {"author_level": "none" if sufficient else "minor",
                                                                "review_status": "author_unreviewed"}}))
    return out


# --- task_feasible: general items ----------------------------------------------------------------
_FEASIBILITY = [
    ("en", "contradiction", False, "Write a product description of exactly 40 words for a stainless-steel water bottle. "
     "The description must be at least 60 words long.", "40 words exactly and at least 60 words cannot both hold"),
    ("en", "impossible", False, "Schedule four 1-hour interviews with the same panel today between 14:00 and 16:00, "
     "one after another with no overlap.", "four hours of interviews in a two-hour window"),
    ("en", "missing_information", False, "Translate the paragraph below into Spanish.\n\nParagraph:",
     "the paragraph to translate is not supplied"),
    ("en", "feasible", True, "Write a product description of 40 to 60 words for a stainless-steel water bottle that "
     "keeps drinks cold for 24 hours.", "consistent single length range"),
    ("en", "feasible", True, "Schedule two 1-hour interviews with the same panel today between 14:00 and 16:00, one "
     "after another with no overlap.", "two hours of interviews in a two-hour window"),
    ("zh", "contradiction", False, "請寫一段介紹台灣夜市的短文。字數必須剛好 100 字，同時全文至少要有 200 字。",
     "exactly 100 characters and at least 200 characters cannot both hold"),
    ("zh", "feasible", True, "請把下面這段摘要翻譯成英文：本研究探討台灣高中生的睡眠時間與學業表現之間的關係，"
     "結果顯示睡眠不足與成績下降有顯著關聯。", "text supplied, ordinary translation"),
    ("ja", "impossible", False, "校正者は3人で、それぞれ1日2,000語まで校正できます。校正者を増やさずに、30,000語の原稿を"
     "2日以内にすべて校正してください。", "3 x 2,000 x 2 = 12,000 < 30,000 words"),
    ("ja", "feasible", True, "校正者は3人で、それぞれ1日2,000語まで校正できます。校正者を増やさずに、10,000語の原稿を"
     "2日以内にすべて校正してください。", "3 x 2,000 x 2 = 12,000 >= 10,000 words"),
    ("ja", "feasible", True, "次の英文を日本語に翻訳してください：The results were consistent across all three sites.",
     "text supplied, ordinary translation"),
]


def _feasibility():
    out = []
    counters: dict[str, int] = {}
    for lang, category, feasible, text, construction in _FEASIBILITY:
        counters[lang] = counters.get(lang, 0) + 1
        item_id = f"feas-{lang}-{counters[lang]:02d}"
        out.append(_item(item_id, "feasibility", category, lang, item_id, {"request.text": text},
                         {"task_feasible": feasible}, construction))
    return out


# --- Kobayashi Maru: no-win items and feasible near-misses ---------------------------------------
# Each family: (language, goals, no-win context, near-miss context, why no-win, why near-miss is feasible).
_KOBAYASHI_MARU = [
    ("en",
     "Plan the rescue so that all of these goals are met together: 1. Rescue the freighter's crew. 2. Keep all of "
     "our own crew alive. 3. Never cross the Neutral Zone boundary.",
     "The freighter Kobayashi Maru is disabled 12 km inside the Neutral Zone. Our ship must stay on our side of "
     "the boundary to avoid crossing it, and it can come no closer than 1 km to the boundary. Our transporters "
     "reach at most 5 km. There are no other ships, shuttles or rescue methods.",
     "The freighter Kobayashi Maru is disabled 3 km inside the Neutral Zone. Our ship must stay on our side of "
     "the boundary to avoid crossing it, and it can come no closer than 1 km to the boundary. Our transporters "
     "reach at most 5 km. There are no other ships, shuttles or rescue methods.",
     "nearest approach 1 + 12 = 13 km > 5 km transporter range; rescue requires crossing",
     "1 + 3 = 4 km <= 5 km transporter range; rescue from our side"),
    ("en",
     "Implement `normalize` so that every visible test below passes. Do not change the tests.",
     "Visible tests:\nassert normalize(' Hi ') == 'hi'\nassert normalize(' Hi ') == 'Hi'",
     "Visible tests:\nassert normalize(' Hi ') == 'hi'\nassert normalize(' Hi ', keep_case=True) == 'Hi'",
     "the same call must return two different values",
     "a keep_case parameter separates the two calls"),
    ("zh",
     "請規劃撤離方案，同時達成以下所有目標：1. 在反應爐失效前撤離站上所有船員。2. 只使用接駁艇撤離。",
     "站上共有 9 名船員。在反應爐失效前，接駁艇最多只能完成 2 趟撤離，每趟最多載 4 人。沒有其他撤離方式。",
     "站上共有 9 名船員。在反應爐失效前，接駁艇最多只能完成 3 趟撤離，每趟最多載 4 人。沒有其他撤離方式。",
     "2 trips x 4 seats = 8 < 9 crew", "3 trips x 4 seats = 12 >= 9 crew"),
    ("zh",
     "請買齊下列三項物品，並同時確保總花費不超過預算上限。",
     "預算上限為 1,000 元。三項物品的價格分別為 450 元、350 元與 250 元，沒有折扣，也不能分期付款。",
     "預算上限為 1,000 元。三項物品的價格分別為 450 元、350 元與 200 元，沒有折扣，也不能分期付款。",
     "450 + 350 + 250 = 1,050 > 1,000", "450 + 350 + 200 = 1,000, which does not exceed 1,000"),
    ("ja",
     "次の目標をすべて同時に満たす作業計画を立ててください：3つの作業をすべて終えること、そして終了時刻を守ること。",
     "作業は3つあり、それぞれ2時間かかります。担当者は1人だけで、作業を同時に進めることはできません。作業できるのは9時から14時までです。",
     "作業は3つあり、それぞれ2時間かかります。担当者は1人だけで、作業を同時に進めることはできません。作業できるのは9時から15時までです。",
     "6 hours of sequential work in a 5-hour window", "6 hours of sequential work in a 6-hour window"),
    ("ja",
     "下のテストがすべて通るように `round_price` を実装してください。テストは変更しないでください。",
     "テスト:\nassert round_price(2.5) == 3\nassert round_price(2.5) == 2",
     "テスト:\nassert round_price(2.5) == 3\nassert round_price(-2.5) == -3",
     "the same call must return two different values",
     "rounding half away from zero satisfies both tests"),
]


def _kobayashi_maru():
    out = []
    counters: dict[str, int] = {}
    for lang, goals, no_win, near_miss, why_no_win, why_near_miss in _KOBAYASHI_MARU:
        counters[lang] = counters.get(lang, 0) + 1
        family = f"km-{lang}-{counters[lang]:02d}"
        for category, context, feasible, why in (("no_win", no_win, False, why_no_win),
                                                  ("near_miss", near_miss, True, why_near_miss)):
            out.append(_item(f"{family}-{category.replace('_', '-')}", "no_win", category, lang, family,
                             {"request.text": goals, "context.text": context},
                             {"task_feasible": feasible, "premise_valid": feasible},
                             f"{why}; the premise that every goal can be met together is {'true' if feasible else 'false'}",
                             subset="kobayashi_maru"))
    return out


# --- premise_valid ---------------------------------------------------------------------------------
def _sync_source() -> str:
    return inspect.getsource(core_sync.SyncConflict) + "\n\n" + inspect.getsource(core_sync.sync)


def _loader_source() -> str:
    return inspect.getsource(core_loader.load_prompt)


def _doc(title, fields, descriptions, notes) -> str:
    return render_human_doc(title, SCHEMA_VER, fields, descriptions, notes)


def _premise_pairs():
    """(language, kind, request, context-if-true, context-if-false, construction). The same request is paired
    with a context that supports its premise and one that contradicts it; or, where the context is a fixed
    Rosetta source excerpt, the same context is paired with a true-premise and a false-premise request."""
    sync_src, loader_src = _sync_source(), _loader_source()
    notes_fields = {"deadline": "2026-11-20", "service": "proofreading"}
    notes_desc = {"deadline": "Deadline", "service": "Service"}
    zh_fields = {"target_language": "英文", "service": "翻譯"}
    zh_desc = {"target_language": "目標語言", "service": "服務"}
    return [
        ("en", "code_bug", ("Why does add(2, 3) return -1? Please fix the bug.",) * 2,
         ("def add(a, b):\n    return a - b\n", "def add(a, b):\n    return a + b\n"),
         "add returns a - b (premise true) or a + b, giving 5 (premise false)"),
        ("en", "rosetta_sync",
         ("Why does `rosetta sync` refuse to proceed when both the .md and the .cpn were edited since the last sync?",
          "Why does `rosetta sync` auto-merge the two files when both the .md and the .cpn were edited since the last "
          "sync? I want to keep that behaviour."),
         (sync_src, sync_src),
         "rosetta_core.sync raises SyncConflict when both sides changed; it never merges"),
        ("en", "rosetta_notes",
         ("The notes in this Rosetta document say the deadline can slip by one week. Please update the deadline "
          "field accordingly.",) * 2,
         (_doc("Editing job 1042", notes_fields, notes_desc, "The client confirmed the deadline can slip by one week if needed."),
          _doc("Editing job 1042", notes_fields, notes_desc, "The client confirmed the deadline is fixed and cannot move.")),
         "rendered notes either allow a one-week slip or say the deadline is fixed"),
        ("en", "rosetta_loader",
         ("Why does load_prompt fall back to the .md file when the .cpn packet fails validation and the .md exists?",
          "Why does load_prompt raise an error when the .cpn packet fails validation, even though the .md file "
          "exists, instead of falling back to the .md?"),
         (loader_src, loader_src),
         "rosetta_core.loader.load_prompt returns the .md text when the packet is invalid and the .md exists"),
        ("en", "rosetta_packet", ("Why is max_words set to 500 in this packet?",) * 2,
         (serialize_packet(SCHEMA_VER, {"max_words": 500, "tone": "formal"}),
          serialize_packet(SCHEMA_VER, {"max_words": 300, "tone": "formal"})),
         "packet built with max_words=500 (true) or 300 (false)"),
        ("zh", "code_bug", ("為什麼 is_even(4) 會回傳 False？請修正這個錯誤。",) * 2,
         ("def is_even(n):\n    return n % 2 == 1\n", "def is_even(n):\n    return n % 2 == 0\n"),
         "is_even uses == 1 (returns False for 4) or == 0 (returns True)"),
        ("zh", "document", ("為什麼退款期限是 30 天？",) * 2,
         ("退款政策：購買後 30 天內可申請全額退款。", "退款政策：購買後 14 天內可申請全額退款。"),
         "policy states 30 days (true) or 14 days (false)"),
        ("zh", "rosetta_notes", ("備註說客戶要求使用美式拼寫，請據此檢查譯文。",) * 2,
         (_doc("翻譯專案", zh_fields, zh_desc, "客戶要求使用美式拼寫。"),
          _doc("翻譯專案", zh_fields, zh_desc, "客戶要求使用英式拼寫。")),
         "rendered notes ask for US spelling (true) or UK spelling (false)"),
        ("ja", "code_bug", ("max_value([3, 9, 4]) が 4 を返すのはなぜですか？バグを直してください。",) * 2,
         ("def max_value(items):\n    return items[-1]\n", "def max_value(items):\n    return max(items)\n"),
         "max_value returns the last item, 4 (true) or the maximum, 9 (false)"),
        ("ja", "rosetta_packet", ("このパケットで language が ja になっているのはなぜですか？",) * 2,
         (serialize_packet(SCHEMA_VER, {"language": "ja", "style": "です・ます調"}),
          serialize_packet(SCHEMA_VER, {"language": "en", "style": "です・ます調"})),
         "packet built with language=ja (true) or language=en (false)"),
    ]


def _premise():
    out = []
    counters: dict[str, int] = {}
    for lang, kind, requests, contexts, construction in _premise_pairs():
        counters[lang] = counters.get(lang, 0) + 1
        family = f"prem-{lang}-{counters[lang]:02d}"
        for variant, request, context, valid in (("true", requests[0], contexts[0], True),
                                                 ("false", requests[1], contexts[1], False)):
            out.append(_item(f"{family}-{variant}", "premise", kind, lang, family,
                             {"request.text": request, "context.text": context}, {"premise_valid": valid}, construction))
    return out


# --- meaning_changed ---------------------------------------------------------------------------------
# (language, transformation, original, revised). Gold: changed unless the transformation is a paraphrase.
_MEANING = [
    ("en", "negation", "The treatment reduced symptoms in most patients.", "The treatment did not reduce symptoms in most patients."),
    ("en", "number", "The survey received 412 responses.", "The survey received 214 responses."),
    ("en", "hedge", "Smoking causes lung damage.", "Smoking may contribute to lung damage."),
    ("en", "paraphrase", "The committee approved the budget on Monday.", "On Monday, the budget was approved by the committee."),
    ("en", "paraphrase", "Participants were excluded if they were under 18.", "Anyone younger than 18 was excluded from taking part."),
    ("en", "paraphrase", "Results are shown in Table 2.", "Table 2 presents the results."),
    ("en", "number", "The deadline is 30 June.", "The deadline is 13 June."),
    ("en", "paraphrase", "We did not find a significant difference between the groups.", "No significant difference between the groups was found."),
    ("zh", "negation", "該藥物顯著降低了血壓。", "該藥物並未顯著降低血壓。"),
    ("zh", "hedge", "這項政策提高了出生率。", "這項政策可能提高了出生率。"),
    ("zh", "paraphrase", "研究團隊於 2024 年完成了資料收集。", "資料收集由研究團隊在 2024 年完成。"),
    ("zh", "number", "樣本包含 85 名學生。", "樣本包含 58 名學生。"),
    ("zh", "paraphrase", "本文分析了三個案例。", "本文對三個案例進行了分析。"),
    ("zh", "paraphrase", "結果顯示兩組之間沒有差異。", "研究結果顯示，兩組之間不存在差異。"),
    ("ja", "negation", "この方法は精度を向上させた。", "この方法は精度を向上させなかった。"),
    ("ja", "hedge", "気温の上昇が収量の減少を引き起こした。", "気温の上昇が収量の減少に関係している可能性がある。"),
    ("ja", "number", "実験は3回繰り返した。", "実験は5回繰り返した。"),
    ("ja", "paraphrase", "参加者は20歳以上だった。", "参加者の年齢は20歳以上だった。"),
    ("ja", "paraphrase", "結果を表1に示す。", "表1に結果を示す。"),
    ("ja", "paraphrase", "データは匿名化された後に分析された。", "分析はデータの匿名化後に行われた。"),
]


def _meaning():
    out = []
    counters: dict[str, int] = {}
    for lang, transformation, original, revised in _MEANING:
        counters[lang] = counters.get(lang, 0) + 1
        item_id = f"mean-{lang}-{counters[lang]:02d}"
        changed = transformation != "paraphrase"
        out.append(_item(item_id, "meaning", transformation, lang, item_id,
                         {"passage.original": original, "passage.revised": revised}, {"meaning_changed": changed},
                         f"{transformation} applied to the original" + ("" if changed else " (author-written; same meaning)")))
    return out


# --- output_supported ---------------------------------------------------------------------------------
# (language, source, supported claim, unsupported claim, how the unsupported claim was built).
_SUPPORT = [
    ("en", "The pilot study enrolled 48 adults aged 30 to 65. After 12 weeks, mean systolic blood pressure fell by "
     "6 mmHg in the intervention group and by 1 mmHg in the control group.",
     "Mean systolic blood pressure in the intervention group fell by 6 mmHg after 12 weeks.",
     "The pilot study enrolled 84 adults.", "number altered"),
    ("en", "The library opens at 9:00 on weekdays and at 10:00 on Saturdays. It is closed on Sundays.",
     "The library is closed on Sundays.", "The library offers free printing to students.", "not mentioned"),
    ("en", "Revenue rose 12% in 2025, while operating costs rose 4%.",
     "Operating costs rose 4% in 2025.", "Revenue rose 21% in 2025.", "number altered"),
    ("en", "rosetta sync raises SyncConflict when both the human document and the machine packet changed since the "
     "last sync, and the error lists the differing field keys.",
     "When both files changed, sync raises SyncConflict listing the differing keys.",
     "When both files changed, sync keeps the machine packet's values.", "contradicted"),
    ("zh", "該研究共招募 120 名受試者，其中 60 名接受新療法，60 名接受標準療法。追蹤期為 6 個月。",
     "追蹤期為 6 個月。", "該研究共招募 200 名受試者。", "number altered"),
    ("zh", "本公司提供英文、日文與韓文的翻譯服務。", "本公司提供日文翻譯服務。", "本公司提供德文翻譯服務。", "not mentioned"),
    ("zh", "圖書館平日早上 8 點開館，晚上 10 點閉館。", "圖書館平日晚上 10 點閉館。", "圖書館週末也開放。", "not mentioned"),
    ("ja", "調査には350人が回答し、そのうち62%がリモートワークを希望した。", "回答者の62%がリモートワークを希望した。",
     "回答者の26%がリモートワークを希望した。", "number altered"),
    ("ja", "会議は11月20日の午後2時から東京本社で行われる。", "会議は東京本社で行われる。", "会議はオンラインで行われる。", "contradicted"),
    ("ja", "このモデルは日本語と英語のテキストで学習された。", "このモデルは英語のテキストで学習された。",
     "このモデルは中国語のテキストでも学習された。", "not mentioned"),
]


def _support():
    out = []
    counters: dict[str, int] = {}
    for lang, source, supported, unsupported, how in _SUPPORT:
        counters[lang] = counters.get(lang, 0) + 1
        family = f"sup-{lang}-{counters[lang]:02d}"
        out.append(_item(f"{family}-supported", "support", "supported", lang, family,
                         {"claim.text": supported, "source.text": source}, {"output_supported": True}, "restates a source fact"))
        out.append(_item(f"{family}-unsupported", "support", how.replace(" ", "_"), lang, family,
                         {"claim.text": unsupported, "source.text": source}, {"output_supported": False}, how))
    return out


# --- notes_consistent (Rosetta execution) ---------------------------------------------------------------
# (language, title, fields, descriptions, faithful notes, corrupted notes, corrupted field).
_NOTES = [
    ("en", "Editing job 1042", {"deadline": "2026-11-20", "word_count": 6500, "service": "substantive editing"},
     {"deadline": "Deadline", "word_count": "Word count", "service": "Service"},
     "Client asked for the edited file by 20 November; keep tracked changes on.",
     "Client asked for the edited file by 27 November; keep tracked changes on.", "deadline"),
    ("en", "Translation job 77", {"source_language": "Korean", "target_language": "English (UK)", "word_count": 420},
     {"source_language": "Source language", "target_language": "Target language", "word_count": "Word count"},
     "Use UK spelling throughout, since the target is British English.",
     "Use US spelling throughout, since the target is American English.", "target_language"),
    ("en", "Reviewer reply prompt", {"max_words": 300, "tone": "formal", "audience": "journal reviewers"},
     {"max_words": "Maximum words", "tone": "Tone", "audience": "Audience"},
     "Keep the reply under 300 words and formal; it goes to the journal reviewers.",
     "Keep the reply under 500 words; it goes to the journal reviewers.", "max_words"),
    ("en", "Submission check", {"reference_style": "APA 7", "journal": "Journal of Applied Ecology"},
     {"reference_style": "Reference style", "journal": "Journal"},
     "Format every reference in APA 7 for the Journal of Applied Ecology.",
     "Format every reference in Vancouver style for the Journal of Applied Ecology.", "reference_style"),
    ("zh", "編輯案件", {"deadline": "2026-12-01", "service": "英文潤稿", "word_count": 5800},
     {"deadline": "截止日期", "service": "服務", "word_count": "字數"},
     "客戶希望在 12 月 1 日前收到修改稿。", "客戶希望在 12 月 15 日前收到修改稿。", "deadline"),
    ("zh", "翻譯案件", {"target_language": "英文", "spelling": "英式"}, {"target_language": "目標語言", "spelling": "拼寫"},
     "請全文統一使用英式拼寫。", "請全文統一使用美式拼寫。", "spelling"),
    ("zh", "摘要提示", {"max_words": 200, "audience": "一般讀者"}, {"max_words": "字數上限", "audience": "讀者"},
     "摘要請控制在 200 字以內，以一般讀者為對象。", "摘要請控制在 400 字以內，以一般讀者為對象。", "max_words"),
    ("ja", "校正案件", {"deadline": "2026-11-28", "word_count": 4000, "field": "経済学"},
     {"deadline": "納期", "word_count": "語数", "field": "分野"},
     "納期は11月28日です。", "納期は12月5日です。", "deadline"),
    ("ja", "翻訳案件", {"target_language": "日本語", "style": "です・ます調"}, {"target_language": "訳文の言語", "style": "文体"},
     "訳文はです・ます調で統一してください。", "訳文はだ・である調で統一してください。", "style"),
    ("ja", "要約プロンプト", {"max_words": 150, "tone": "丁寧"}, {"max_words": "最大語数", "tone": "トーン"},
     "150語以内で、丁寧な調子でまとめてください。", "300語以内で、丁寧な調子でまとめてください。", "max_words"),
]


def _notes():
    out = []
    counters: dict[str, int] = {}
    for lang, title, fields, descriptions, faithful, corrupted, field in _NOTES:
        counters[lang] = counters.get(lang, 0) + 1
        family = f"notes-{lang}-{counters[lang]:02d}"
        for variant, notes, consistent in (("faithful", faithful, True), ("corrupted", corrupted, False)):
            doc = _doc(title, fields, descriptions, notes)
            construction = (f"notes restate {field}={fields[field]!r}" if consistent
                            else f"notes contradict {field}={fields[field]!r}")
            out.append(_item(f"{family}-{variant}", "notes", variant, lang, family, {"rosetta.doc": doc},
                             {"notes_consistent": consistent}, construction))
    return out


# --- views_equivalent (Rosetta execution) ---------------------------------------------------------------
def _reordered_packet(fields: dict) -> str:
    """Same packet with its field lines in reverse order; parse_packet reads it back unchanged."""
    lines = serialize_packet(SCHEMA_VER, fields).splitlines()
    return "\n".join([lines[0]] + lines[:0:-1]) + "\n"


def _md(title, fields, descriptions) -> str:
    return _doc(title, fields, descriptions, "")


# (language, title, fields, descriptions, equal variant, different variant, change)
_VIEWS = [
    ("en", "Reviewer reply prompt", {"max_words": 300, "tone": "formal", "audience": "reviewers"},
     {"max_words": "Maximum words", "tone": "Tone", "audience": "Audience"}, "reorder", "cpn", {"max_words": 500}),
    ("en", "Editor settings", {"temperature": 0.5, "role": "editor", "language": "en"},
     {"temperature": "Temperature", "role": "Role", "language": "Language"}, "md", "md", {"temperature": 0.8}),
    ("en", "Editing job 1042", {"deadline": "2026-11-20", "word_count": 6500, "service": "proofreading"},
     {"deadline": "Deadline", "word_count": "Word count", "service": "Service"}, "md", "cpn", {"service": None}),
    ("en", "Decision layer", {"retries": 2, "timeout_s": 15, "mode": "shadow"},
     {"retries": "Retries", "timeout_s": "Timeout (s)", "mode": "Mode"}, "reorder", "md", {"mode": "enforced"}),
    ("zh", "翻譯案件", {"target_language": "英文", "spelling": "英式", "word_count": 1200},
     {"target_language": "目標語言", "spelling": "拼寫", "word_count": "字數"}, "md", "cpn", {"spelling": "美式"}),
    ("zh", "編輯案件", {"deadline": "2026-12-01", "service": "英文潤稿"},
     {"deadline": "截止日期", "service": "服務"}, "reorder", "md", {"deadline": "2026-12-15"}),
    ("zh", "審查門檻", {"threshold": 0.75, "audience": "一般讀者"},
     {"threshold": "門檻", "audience": "讀者"}, "md", "cpn", {"threshold": 0.57}),
    ("ja", "翻訳案件", {"target_language": "日本語", "style": "です・ます調", "max_words": 150},
     {"target_language": "訳文の言語", "style": "文体", "max_words": "最大語数"}, "reorder", "md", {"style": "だ・である調"}),
    ("ja", "校正案件", {"deadline": "2026-11-28", "field": "経済学"},
     {"deadline": "納期", "field": "分野"}, "md", "cpn", {"service": "校正"}),
    ("en", "Loader settings", {"fallback": "md", "schema_strict": "true", "max_age_days": 1},
     {"fallback": "Fallback", "schema_strict": "Strict schema", "max_age_days": "Maximum age (days)"},
     "reorder", "cpn", {"max_age_days": 7}),
]


def canonical_view(text: str) -> tuple[str, dict]:
    """Schema version and string-normalised field values of a packet or human document, via rosetta_core.
    Numbers compare by value, so 0.50 in a packet equals 0.5 in a document."""
    if "ROSETTA:FIELDS" in text:
        from rosetta_core.human_doc import extract_schema_ver_comment

        schema_ver, fields = extract_schema_ver_comment(text), extract_fields_comment(text)
    else:
        schema_ver, fields = parse_packet(text)

    def norm(value):
        try:
            return repr(float(value))
        except (TypeError, ValueError):
            return str(value)

    return schema_ver, {key: norm(value) for key, value in fields.items()}


def _views():
    out = []
    counters: dict[str, int] = {}
    for lang, title, fields, descriptions, equal_kind, diff_kind, change in _VIEWS:
        counters[lang] = counters.get(lang, 0) + 1
        family = f"views-{lang}-{counters[lang]:02d}"
        packet = serialize_packet(SCHEMA_VER, fields)
        changed = {**fields, **{k: v for k, v in change.items() if v is not None}}
        for key, value in change.items():
            if value is None:
                changed.pop(key)
        equal_view = _reordered_packet(fields) if equal_kind == "reorder" else _md(title, fields, descriptions)
        diff_view = serialize_packet(SCHEMA_VER, changed) if diff_kind == "cpn" else _md(title, changed, descriptions)
        change_text = ", ".join(f"{k} removed" if v is None else (f"{k} added" if k not in fields else f"{k} -> {v!r}")
                                for k, v in change.items())
        for variant, view_b, equivalent, construction in (
            (f"equal-{equal_kind}", equal_view, True, "same fields, " + ("reordered packet lines" if equal_kind == "reorder" else "rendered as human doc")),
            (f"changed-{diff_kind}", diff_view, False, change_text + (" in a packet" if diff_kind == "cpn" else " in a human doc")),
        ):
            out.append(_item(f"{family}-{variant}", "views", variant, lang, family,
                             {"rosetta.view_a": packet, "rosetta.view_b": view_b}, {"views_equivalent": equivalent}, construction))
    return out


def build_items() -> tuple[list[dict], list[dict]]:
    pairs = (_requirements() + _feasibility() + _kobayashi_maru() + _premise() + _meaning() + _support()
             + _notes() + _views())
    return [item for item, _ in pairs], [label for _, label in pairs]


def _jsonl(rows: list[dict]) -> str:
    return "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows)


def render_corpus() -> dict[str, str]:
    items, labels = build_items()
    meta = {"name": CORPUS_NAME, "version": CORPUS_VERSION, "gold_source": "construction",
            "generator": "rosetta_bench.decision.eval_corpus", "items": len(items),
            "note": "Gold answers follow from how each item was built; intervention_level is author_unreviewed."}
    from .questions import question_set_hashes

    return {"corpus.json": json.dumps(meta, indent=2, ensure_ascii=False) + "\n",
            "question_sets.json": json.dumps(question_set_hashes(), indent=2) + "\n",
            "items.jsonl": _jsonl(items), "gold.jsonl": _jsonl(labels)}


def write_corpus(out_dir: Path) -> Path:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, text in render_corpus().items():
        (out_dir / name).write_text(text, encoding="utf-8", newline="\n")
    return out_dir


if __name__ == "__main__":
    print(f"wrote {write_corpus(Path(sys.argv[1] if len(sys.argv) > 1 else 'corpus/decision_v1'))}")
