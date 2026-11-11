"""Generate evidence mapping, not an automatic semantic pass certificate."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
specs=[json.loads(x) for x in (ROOT/'Buxi_Tarot_Knowledge_v01/eval_cases.jsonl').read_text('utf-8').splitlines()]
live={c['id'] for f in ['live-model.json','live-model-followup.json'] for c in json.loads((ROOT/'docs/evaluations'/f).read_text('utf-8'))['cases'] if c['http_status']==200}
automatic={
 'known_card_wrong_user':'prompt contains backend facts; mutations unavailable',
 'four_wands_reverse':'test_special_reversals_and_aliases; live content reviewed separately',
 'eight_cups_reverse':'test_special_reversals_and_aliases',
 'two_cups_evidence':'test_special_reversals_and_aliases',
 'source_injection':'test_injection_cannot_write_knowledge_and_actual_facts_supplied',
 'orientation_exact':'test_complete_mapping_and_all_directions',
 'missing_card':'test_exact_unknown_and_versions_never_fallback; test_exact_api_and_legacy_result_version',
 'random_rule':'test_both_orientations_possible; implementation inspection (not empirical reality)',
 'citation_kind':'test_complete_mapping_and_all_directions; test_fabricated_citations_rejected',
 'knowledge_memory_boundary':'test_memory_invalidation_excludes_paraphrased_history (adjacent case)',
 'retrieval_scope':'test_account_role_and_conversation_isolation',
 'retry_same_draw':'test_interpret_lost_response_retries_once_and_reveal; test_failed_model_preserves_result'
}
adjacent={'no_other_mind':'source_injection','nine_swords_health':'death_not_event','edition_honesty':'star_conflict','position_context':'complete_reading (Temperance in obstacle; not exact Pentacles Eight fixture)'}
result=[]
for s in specs:
 result.append(dict(s,automatic_evidence=automatic.get(s['id']),live_evidence=s['id'] if s['id'] in live else adjacent.get(s['id']),status='evidence_recorded_requires_review' if s['id'] in automatic or s['id'] in live or s['id'] in adjacent else 'not_run',human_review='pending'))
(ROOT/'docs/evaluations/spec-coverage.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
