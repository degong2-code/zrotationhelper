#!/usr/bin/env python3
"""Original SimC spell-data dependency linker (generic, source-pinned).

Bind an independently captured original Native action lifecycle to its APL
source row and class-module action factory/constructor/talent registry. The
adapter supplies ONLY paths, expected identity and parser anchors. The generic
linker reads pinned C++ source and never embeds a specialization's spell names.

A lexical/regex parser supports a *narrow* common C++ factory/constructor
pattern. Unsupported, ambiguous, or drifted source is UNKNOWN or FAIL, not
inferred spell availability. A talent loadout string is opaque unless separately
decoded from independent Native or Blizzard evidence. No args selftests.
"""
from __future__ import annotations
import argparse
from hashlib import sha256
import json
from pathlib import Path
import re
import subprocess

SCHEMA="ZrotOriginalNativeGenericSpellDataDependencyLinkV1"
ADAPTER_SCHEMA="ZrotOriginalNativeSpellDependencyAdapterV1"
UPSTREAM="b522cded8c26b97dac03fdf56e57a03ec7e8faa6"
POLICY="ZROT_GENERAL_ROTATION_OPENER_DUMMY_TRAINER_20261102_V1"
LIFECYCLE_SCHEMA="ZrotOriginalSimCActionLifecycleSourceBoundReplayV1"
PINNED_CTOR_GUARD=r"if ( s_data == spell_data_t::not_found() )"
IDENT=r"[A-Za-z_][A-Za-z_0-9]*"
FACTORY=re.compile(
    r'\bif\s*\(\s*name\s*==\s*"(?P<name>[a-z0-9_]+)"\s*\)'
    r'\s*return\s+new\s+(?P<cls>[A-Za-z_][A-Za-z_0-9]*)'
    r'\s*\(\s*this\s*,\s*options_str\s*\)\s*;',re.S)
CLASS=re.compile(
    r'\bstruct\s+(?P<cls>[A-Za-z_]\w*)\s*:\s*public\s+'
    r'(?P<base>[A-Za-z_]\w*)\s*\{',re.S)
TALENT=re.compile(
    r'\{\s*talent\.(?P<field>[A-Za-z_]\w*)\s*,\s*"(?P<label>[^"]+)"\s*\}')
CTOR_TEMPLATE=r'\b{cls}\s*\(\s*[^(){{}}]{{1,300}}\)\s*:\s*{base}\s*'
CTOR_ARGS=re.compile(
    r'\(\s*"(?P<token>[a-z0-9_]+)"\s*,\s*'
    r'(?P<actor>[A-Za-z_]\w*)\s*,\s*'
    r'(?P<dependency>[A-Za-z_]\w*(?:->\w+|\.\w+)+)\s*\)',re.S)

class LinkError(ValueError):pass
def need(ok,msg):
    if not ok:raise LinkError(msg)

def gitblob(data:bytes):
    import hashlib
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()

def valid_adapter(plan:dict):
    need(plan.get("schema")==ADAPTER_SCHEMA and
         plan.get("policy_id")==POLICY and
         plan.get("source_revision")==UPSTREAM and
         re.fullmatch(r"[a-z_]+",plan.get("spec_key","")) is not None and
         re.fullmatch(r"[0-9a-f]{40}",plan.get("profile_git_blob","")) is not None and
         isinstance(plan.get("cases"),list) and len(plan["cases"])<=16 and
         len(plan["cases"])>=1,"ADAPTER_SCHEMA_REVISION_OR_PROFILE_PIN_INVALID")
    for case in plan["cases"]:
        need(isinstance(case.get("targets"),int) and 1<=case["targets"]<=40 and
             isinstance(case.get("source_rank"),int) and case["source_rank"]>=1 and
             re.fullmatch(r"[a-z0-9_]+",case.get("source_list","")) and
             re.fullmatch(r"[a-z0-9_]+",case.get("source_action","")) and
             re.fullmatch(r"[a-z_0-9]+",case.get("expected_talent_field","")) and
             re.fullmatch(r"[A-Za-z_]\w*",case.get("factory_class","")) and
             re.fullmatch(r"[A-Za-z_]\w*",case.get("factory_parent_base","")) and
             bool(case.get("expected_talent_label")),
             "INVALID_SPEC_ADAPTER_SOURCE_CASE")
    return True

def extract_route(cpp:str,case:dict)->dict:
    action=case["source_action"]
    factories=[m for m in FACTORY.finditer(cpp) if m["name"]==action]
    need(len(factories)==1,"FACTORY_DISPATCH_MISSING_OR_AMBIGUOUS")
    cls=factories[0]["cls"]
    need(cls==case["factory_class"],"FACTORY_CLASS_DRIFT")
    definitions=[m for m in CLASS.finditer(cpp) if m["cls"]==cls]
    need(len(definitions)==1,"ACTION_STRUCT_MISSING_OR_AMBIGUOUS")
    definition=definitions[0]
    parent=definition["base"]
    need(parent==case["factory_parent_base"],"ACTION_CONSTRUCTOR_BASE_DRIFT")
    # Bound the scan to the class's own constructor at the struct beginning;
    # do not pick another class's similar initializer later in the file.
    prefix=cpp[definition.end():definition.end()+1800]
    ctor=re.compile(CTOR_TEMPLATE.format(cls=re.escape(cls),base=re.escape(parent)),re.S)
    starts=list(ctor.finditer(prefix))
    # Factory Class(this, options_str) disambiguates overloads used for
    # triggered/background actions; do not link to a different constructor.
    compatible=[x for x in starts if
                re.search(r'\boptions_str\s*\)\s*:\s*'+re.escape(parent)+r'\s*
    need(m is not None,"CLASS_SPELL_DATA_ARGUMENT_UNSUPPORTED")
    dep=m["dependency"]
    expected=case.get("expected_spell_data_input", "player->talent."+case.get("expected_talent_field",""))
    actor=m["actor"]
    need(m["token"]==action and dep==expected and
         dep.startswith(actor+"->"),
         "CLASS_SPELL_DATA_DEPENDENCY_NOT_EXPECTED_TALENT")
    # Optional source-level talent registry. Class module layouts vary: a
    # missing flat registry must not be invented as proof of a talent label.
    expected_label=case.get("expected_talent_label")
    registry=[x["label"] for x in TALENT.finditer(cpp)
              if x["field"]==case.get("expected_talent_field")]
    if expected_label:
        need(len(registry)==1 and registry[0]==expected_label,
             "TALENT_REGISTRY_NAME_MISSING_AMBIGUOUS_OR_DRIFT")
    registry_label=registry[0] if len(registry)==1 else "UNKNOWN"
    return {
       "source_action_factory_token":action,
       "source_action_factory_constructed_class":cls,
       "source_action_factory_link":"EXACT_UNIQUE_FACTORY_RETURN",
       "source_class_ancestor":parent,
       "source_constructor_first_spell_data_input":dep,
       "source_constructor_spell_input_link":"EXACT_UNIQUE_CPP_INITIALIZER",
       "source_talent_registry_symbol":case.get("expected_talent_field","UNKNOWN"),
       "source_talent_registry_label":registry_label,
       "source_class_file_sha256":sha256(cpp.encode()).hexdigest(),
       "source_input_is_runtime_selected_talent":"UNKNOWN",
       "source_ancestral_cpp_delegation_chain_complete":False,
       "why_player_talent_pointer_is_not_found":"UNKNOWN",
    }

def link(cpp:str,actioncpp:str,profile:bytes,life:dict,plan:dict)->dict:
    valid_adapter(plan)
    guard_at=actioncpp.find(PINNED_CTOR_GUARD)
    need(guard_at>=0 and actioncpp.count(PINNED_CTOR_GUARD)==1 and
         re.search(r'background\s*=\s*true\s*;',
                   actioncpp[guard_at:guard_at+550],re.S),
         "PINNED_ACTION_NOT_FOUND_CONSTRUCTOR_GUARD_MISSING")
    need(gitblob(profile)==plan["profile_git_blob"]==
         life.get("source_profile_git_blob") and
         life.get("schema")==LIFECYCLE_SCHEMA and
         life.get("source_revision")==plan["source_revision"] and
         life.get("policy_id")==plan["policy_id"] and
         life.get("source_spec")==plan["spec_key"] and
         life.get("physical_skill_READY_independently_proven")==0 and
         life.get("WCL_independent_blind_postlock")=="NOT_RUN",
         "NATIVE_LIFECYCLE_NOT_SAME_PINNED_PROFILE_OR_PRODUCT")
    from simc_apl_semantic_ir_v2 import parse_profile
    src=parse_profile(profile,require_source=False)
    cases=[]
    for case in plan["cases"]:
        need(case["targets"]==life["targets"] and
             case["source_list"]==life["selected_root"]["source_list"],
             "CASE_NOT_THE_NATIVE_SELECTED_ROOT")
        source_rows=src["action_lists"].get(case["source_list"])
        need(source_rows and case["source_rank"]<=len(source_rows) and
             source_rows[case["source_rank"]-1]["action"]==case["source_action"],
             "NATIVE_DEPENDENCY_NOT_SAME_ORIGINAL_APL_ROW")
        matching=[x for x in life["source_upper_rows_with_original_lifecycle"]
                  if x["rank"]==case["source_rank"] and
                  x["source_action"]==case["source_action"] and
                  x["source_sha256"]==source_rows[case["source_rank"]-1]["source_sha256"]]
        need(len(matching)==1,"MISSING_OR_AMBIGUOUS_NATIVE_ACTION_SOURCE_ROW")
        target=matching[0]
        need(target["native_object_lifecycle"]==
             "EXACT_SOURCE_SIGNATURE_FOUR_PHASES" and
             target["instance_original_PTR_cohort_verified"] is True and
             target["native_background_origin"]==
             "SOURCE_PINNED_CONSTRUCTOR_NOT_FOUND_SPELL_GUARD_OBSERVED" and
             target["native_spell_data_not_found_at_create"] is True and
             target["runtime_membership_class"]=="ABSENT_BACKGROUND_FLAG" and
             target["original_ready_return"]=="NOT_CALLED" and
             target["native_flags_by_phase"]["POST_CREATE"]["not_found"] is True and
             target["native_flags_by_phase"]["POST_CREATE"]["background"] is True,
             "NATIVE_ORIGINAL_LIFECYCLE_CAUSAL_GUARD_UNSUPPORTED")
        route=extract_route(cpp,case)
        cases.append({
           "targets":case["targets"],
           "original_source_list":case["source_list"],
           "original_source_rank":case["source_rank"],
           "source_action":case["source_action"],
           "original_source_row_sha256":target["source_sha256"],
           "original_native_lifecycle_phase":"POST_CREATE",
           "original_native_spell_data":"NOT_FOUND",
           "original_native_background":True,
           "original_native_foreground_membership":"ABSENT",
           "observed_original_constructor_background_guard":True,
           "source_path_provenance":route,
           "profile_talent_loadout_status":"OPAQUE_NOT_DECODED",
           "original_talent_selected_status":"UNKNOWN",
           "blizzard_current_patch_talent_and_spell_parity":"UNKNOWN",
           "independent_physical_spell_READY":"UNKNOWN",
           "causal_scope":"SOURCE_CONSTRUCTOR_NOT_FOUND_BACKGROUND_ONLY_NOT_GAMEPLAY_PRIORITY"
        })
    return {
      "schema":SCHEMA,"policy_id":POLICY,"source_revision":UPSTREAM,
      "spec_key":plan["spec_key"],"profile_git_blob":gitblob(profile),
      "source_cpp_module":plan["source_class_path"],
      "verified_native_lifecycle_sha256":None,
      "source_to_factory_and_constructor_dependencies":cases,
      "observed_action_ptr_to_source_row_preserved":True,
      "native_to_source_dependency_link":"SOURCE_BOUND_BUT_OPAQUE_TALENT_SELECTION",
      "WCL_independent_blind":"NOT_TOUCHED",
      "independent_retail_mechanic_truth":"UNKNOWN",
      "opener_end":"UNKNOWN","general_rotation_rule_promoted":0,
      "dummy_wrong_cast":"UNKNOWN","MAIN_promoted":False
    }

def selftest():
    from simc_apl_semantic_ir_v2 import parse_profile
    c='''struct alpha_t : public base_t
{
 alpha_t( sim_t* player, util::string_view options_str )
 : base_t( "alpha", player, player->talent.alpha ) { }
};
if ( name == "alpha" ) return new alpha_t( this, options_str );
{ talent.alpha, "Alpha" };
'''
    case={"source_action":"alpha","factory_class":"alpha_t",
          "factory_parent_base":"base_t","expected_talent_field":"alpha",
          "expected_talent_label":"Alpha","source_rank":1,"source_list":"area","targets":3}
    route=extract_route(c,case)
    need(route["source_constructor_first_spell_data_input"]=="player->talent.alpha",
         "SYNTHETIC_TALENT_ROUTE_NOT_FOUND")
    n=0
    for bad in (
        c.replace('new alpha_t','new wrong_t'),
        c.replace('player->talent.alpha','player->talent.other'),
        c.replace('{ talent.alpha, "Alpha" }','{ talent.alpha, "Beta" }'),
        c.replace('struct alpha_t','struct beta_t'),
        c.replace('if ( name == "alpha" ) return new alpha_t( this, options_str );',''),
        c+'if ( name == "alpha" ) return new alpha_t( this, options_str );',
        c.replace('player, player->talent.alpha','player, player->spell.alpha'),
        c.replace(': base_t( "alpha"',': base_t( "wrong"'),
    ):
        try:extract_route(bad,case)
        except LinkError:n+=1
        else:raise AssertionError("ACCEPTED_FOREIGN_CXX_TALENT_SOURCE_DEPENDENCY")
    need(n==8,"NEGATIVE_LINKAGE_COHORT_INCOMPLETE")
    nested='''struct beta_t : public warrior_attack_t
{
 beta_t( warrior_t* p, util::string_view options_str )
 : warrior_attack_t( "beta", p, p->talents.fury.beta ) { }
};
if ( name == "beta" ) return new beta_t( this, options_str );
'''
    nested_case={"source_action":"beta","factory_class":"beta_t",
                 "factory_parent_base":"warrior_attack_t",
                 "expected_spell_data_input":"p->talents.fury.beta"}
    nested_route=extract_route(nested,nested_case)
    need(nested_route["source_constructor_first_spell_data_input"]==
         "p->talents.fury.beta" and
         nested_route["source_talent_registry_label"]=="UNKNOWN",
         "NESTED_TALENT_SOURCE_ONLY_GENERIC_ROUTING_FAIL")
    # Correctly select the factory-facing constructor when source declares
    # an additional internal background constructor overload.
    overloaded=nested.replace(
        'if ( name == "beta" )',
        'beta_t( util::string_view label, warrior_t* p )'
        ' : warrior_attack_t( "beta", p, p->talents.fury.other ) { }\\n'
        'if ( name == "beta" )')
    overload_route=extract_route(overloaded,nested_case)
    need(overload_route["source_constructor_first_spell_data_input"]==
         "p->talents.fury.beta",
         "FACTORY_SELECTED_WRONG_NATIVE_CONSTRUCTOR_OVERLOAD")
    return {"schema":SCHEMA,"status":"PASS_SYNTHETIC_STATIC",
            "negative_controls":n,"cpp_factory_dependency_route":"PASS",
            "opaque_loadout_does_not_prove_selected_talent":True,
            "WCL_API_calls":0,"new_native_simulations":0}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source-root",type=Path)
    p.add_argument("--adapter",type=Path)
    p.add_argument("--native-lifecycle",type=Path)
    p.add_argument("--out",type=Path)
    a=p.parse_args()
    if all(v is None for v in vars(a).values()):
        print(json.dumps(selftest(),sort_keys=True));return
    need(all(v is not None for v in vars(a).values()),
         "ALL_PINNED_ORIGINAL_SOURCE_AND_NATIVE_INPUTS_REQUIRED")
    root=a.source_root.resolve(strict=True)
    rev=subprocess.run(["git","-C",str(root),"rev-parse","HEAD"],check=True,
                       text=True,capture_output=True).stdout.strip()
    need(rev==UPSTREAM,"ORIGINAL_SIMC_SOURCE_COMMIT_NOT_PINNED")
    plan=json.loads(a.adapter.read_bytes())
    valid_adapter(plan)
    classpath=plan["source_class_path"]
    profpath=plan["source_profile_path"]
    need(classpath.startswith("engine/class_modules/sc_") and
         classpath.endswith(".cpp") and ".." not in classpath and
         profpath.startswith("profiles/") and profpath.endswith(".simc") and
         ".." not in profpath,"UNSAFE_OR_NONCLASS_SPEC_ADAPTER_PATH")
    raw=a.native_lifecycle.read_bytes()
    need(all(case.get("expected_native_evidence_sha256")==sha256(raw).hexdigest()
             for case in plan["cases"]),
         "SOURCE_ADAPTER_NOT_THE_PINNED_NATIVE_LIFECYCLE_BYTES")
    result=link((root/classpath).read_text("utf-8"),
                (root/"engine/action/action.cpp").read_text("utf-8"),
                (root/profpath).read_bytes(),json.loads(raw),plan)
    result["verified_native_lifecycle_sha256"]=sha256(raw).hexdigest()
    result["source_action_constructor_cpp_sha256"]=sha256(
        (root/"engine/action/action.cpp").read_bytes()).hexdigest()
    result["adapter_sha256"]=sha256(a.adapter.read_bytes()).hexdigest()
    from simc_apl_semantic_ir_v2 import canonical
    a.out.parent.mkdir(parents=True,exist_ok=True)
    with a.out.open("xb") as f:f.write(canonical(result))
    print("GENERIC_SIMC_SPELL_DEPENDENCY_SHA256="+sha256(a.out.read_bytes()).hexdigest())
    print("GENERIC_SIMC_SPELL_DEPENDENCY_SUMMARY="+json.dumps(
        {"spec":result["spec_key"],"cases":[
             {"source":c["source_action"],"dependency":
              c["source_path_provenance"]["source_constructor_first_spell_data_input"],
              "talent_selected":c["original_talent_selected_status"]}
             for c in result["source_to_factory_and_constructor_dependencies"]]},
        sort_keys=True))

if __name__=="__main__":main()
,
                          x.group(0),re.S)]
    need(len(compatible)==1,"FACTORY_CONSTRUCTOR_OVERLOAD_NOT_UNAMBIGUOUS")
    m=CTOR_ARGS.match(prefix,compatible[0].end())
    need(m is not None,"CLASS_SPELL_DATA_ARGUMENT_UNSUPPORTED")
    dep=m["dependency"]
    expected=case.get("expected_spell_data_input", "player->talent."+case.get("expected_talent_field",""))
    actor=m["actor"]
    need(m["token"]==action and dep==expected and
         dep.startswith(actor+"->"),
         "CLASS_SPELL_DATA_DEPENDENCY_NOT_EXPECTED_TALENT")
    # Optional source-level talent registry. Class module layouts vary: a
    # missing flat registry must not be invented as proof of a talent label.
    expected_label=case.get("expected_talent_label")
    registry=[x["label"] for x in TALENT.finditer(cpp)
              if x["field"]==case.get("expected_talent_field")]
    if expected_label:
        need(len(registry)==1 and registry[0]==expected_label,
             "TALENT_REGISTRY_NAME_MISSING_AMBIGUOUS_OR_DRIFT")
    registry_label=registry[0] if len(registry)==1 else "UNKNOWN"
    return {
       "source_action_factory_token":action,
       "source_action_factory_constructed_class":cls,
       "source_action_factory_link":"EXACT_UNIQUE_FACTORY_RETURN",
       "source_class_ancestor":parent,
       "source_constructor_first_spell_data_input":dep,
       "source_constructor_spell_input_link":"EXACT_UNIQUE_CPP_INITIALIZER",
       "source_talent_registry_symbol":case.get("expected_talent_field","UNKNOWN"),
       "source_talent_registry_label":registry_label,
       "source_class_file_sha256":sha256(cpp.encode()).hexdigest(),
       "source_input_is_runtime_selected_talent":"UNKNOWN",
       "source_ancestral_cpp_delegation_chain_complete":False,
       "why_player_talent_pointer_is_not_found":"UNKNOWN",
    }

def link(cpp:str,actioncpp:str,profile:bytes,life:dict,plan:dict)->dict:
    valid_adapter(plan)
    guard_at=actioncpp.find(PINNED_CTOR_GUARD)
    need(guard_at>=0 and actioncpp.count(PINNED_CTOR_GUARD)==1 and
         re.search(r'background\s*=\s*true\s*;',
                   actioncpp[guard_at:guard_at+550],re.S),
         "PINNED_ACTION_NOT_FOUND_CONSTRUCTOR_GUARD_MISSING")
    need(gitblob(profile)==plan["profile_git_blob"]==
         life.get("source_profile_git_blob") and
         life.get("schema")==LIFECYCLE_SCHEMA and
         life.get("source_revision")==plan["source_revision"] and
         life.get("policy_id")==plan["policy_id"] and
         life.get("source_spec")==plan["spec_key"] and
         life.get("physical_skill_READY_independently_proven")==0 and
         life.get("WCL_independent_blind_postlock")=="NOT_RUN",
         "NATIVE_LIFECYCLE_NOT_SAME_PINNED_PROFILE_OR_PRODUCT")
    from simc_apl_semantic_ir_v2 import parse_profile
    src=parse_profile(profile,require_source=False)
    cases=[]
    for case in plan["cases"]:
        need(case["targets"]==life["targets"] and
             case["source_list"]==life["selected_root"]["source_list"],
             "CASE_NOT_THE_NATIVE_SELECTED_ROOT")
        source_rows=src["action_lists"].get(case["source_list"])
        need(source_rows and case["source_rank"]<=len(source_rows) and
             source_rows[case["source_rank"]-1]["action"]==case["source_action"],
             "NATIVE_DEPENDENCY_NOT_SAME_ORIGINAL_APL_ROW")
        matching=[x for x in life["source_upper_rows_with_original_lifecycle"]
                  if x["rank"]==case["source_rank"] and
                  x["source_action"]==case["source_action"] and
                  x["source_sha256"]==source_rows[case["source_rank"]-1]["source_sha256"]]
        need(len(matching)==1,"MISSING_OR_AMBIGUOUS_NATIVE_ACTION_SOURCE_ROW")
        target=matching[0]
        need(target["native_object_lifecycle"]==
             "EXACT_SOURCE_SIGNATURE_FOUR_PHASES" and
             target["instance_original_PTR_cohort_verified"] is True and
             target["native_background_origin"]==
             "SOURCE_PINNED_CONSTRUCTOR_NOT_FOUND_SPELL_GUARD_OBSERVED" and
             target["native_spell_data_not_found_at_create"] is True and
             target["runtime_membership_class"]=="ABSENT_BACKGROUND_FLAG" and
             target["original_ready_return"]=="NOT_CALLED" and
             target["native_flags_by_phase"]["POST_CREATE"]["not_found"] is True and
             target["native_flags_by_phase"]["POST_CREATE"]["background"] is True,
             "NATIVE_ORIGINAL_LIFECYCLE_CAUSAL_GUARD_UNSUPPORTED")
        route=extract_route(cpp,case)
        cases.append({
           "targets":case["targets"],
           "original_source_list":case["source_list"],
           "original_source_rank":case["source_rank"],
           "source_action":case["source_action"],
           "original_source_row_sha256":target["source_sha256"],
           "original_native_lifecycle_phase":"POST_CREATE",
           "original_native_spell_data":"NOT_FOUND",
           "original_native_background":True,
           "original_native_foreground_membership":"ABSENT",
           "observed_original_constructor_background_guard":True,
           "source_path_provenance":route,
           "profile_talent_loadout_status":"OPAQUE_NOT_DECODED",
           "original_talent_selected_status":"UNKNOWN",
           "blizzard_current_patch_talent_and_spell_parity":"UNKNOWN",
           "independent_physical_spell_READY":"UNKNOWN",
           "causal_scope":"SOURCE_CONSTRUCTOR_NOT_FOUND_BACKGROUND_ONLY_NOT_GAMEPLAY_PRIORITY"
        })
    return {
      "schema":SCHEMA,"policy_id":POLICY,"source_revision":UPSTREAM,
      "spec_key":plan["spec_key"],"profile_git_blob":gitblob(profile),
      "source_cpp_module":plan["source_class_path"],
      "verified_native_lifecycle_sha256":None,
      "source_to_factory_and_constructor_dependencies":cases,
      "observed_action_ptr_to_source_row_preserved":True,
      "native_to_source_dependency_link":"SOURCE_BOUND_BUT_OPAQUE_TALENT_SELECTION",
      "WCL_independent_blind":"NOT_TOUCHED",
      "independent_retail_mechanic_truth":"UNKNOWN",
      "opener_end":"UNKNOWN","general_rotation_rule_promoted":0,
      "dummy_wrong_cast":"UNKNOWN","MAIN_promoted":False
    }

def selftest():
    from simc_apl_semantic_ir_v2 import parse_profile
    c='''struct alpha_t : public base_t
{
 alpha_t( sim_t* player, util::string_view options_str )
 : base_t( "alpha", player, player->talent.alpha ) { }
};
if ( name == "alpha" ) return new alpha_t( this, options_str );
{ talent.alpha, "Alpha" };
'''
    case={"source_action":"alpha","factory_class":"alpha_t",
          "factory_parent_base":"base_t","expected_talent_field":"alpha",
          "expected_talent_label":"Alpha","source_rank":1,"source_list":"area","targets":3}
    route=extract_route(c,case)
    need(route["source_constructor_first_spell_data_input"]=="player->talent.alpha",
         "SYNTHETIC_TALENT_ROUTE_NOT_FOUND")
    n=0
    for bad in (
        c.replace('new alpha_t','new wrong_t'),
        c.replace('player->talent.alpha','player->talent.other'),
        c.replace('{ talent.alpha, "Alpha" }','{ talent.alpha, "Beta" }'),
        c.replace('struct alpha_t','struct beta_t'),
        c.replace('if ( name == "alpha" ) return new alpha_t( this, options_str );',''),
        c+'if ( name == "alpha" ) return new alpha_t( this, options_str );',
        c.replace('player, player->talent.alpha','player, player->spell.alpha'),
        c.replace(': base_t( "alpha"',': base_t( "wrong"'),
    ):
        try:extract_route(bad,case)
        except LinkError:n+=1
        else:raise AssertionError("ACCEPTED_FOREIGN_CXX_TALENT_SOURCE_DEPENDENCY")
    need(n==8,"NEGATIVE_LINKAGE_COHORT_INCOMPLETE")
    nested='''struct beta_t : public warrior_attack_t
{
 beta_t( warrior_t* p, util::string_view options_str )
 : warrior_attack_t( "beta", p, p->talents.fury.beta ) { }
};
if ( name == "beta" ) return new beta_t( this, options_str );
'''
    nested_case={"source_action":"beta","factory_class":"beta_t",
                 "factory_parent_base":"warrior_attack_t",
                 "expected_spell_data_input":"p->talents.fury.beta"}
    nested_route=extract_route(nested,nested_case)
    need(nested_route["source_constructor_first_spell_data_input"]==
         "p->talents.fury.beta" and
         nested_route["source_talent_registry_label"]=="UNKNOWN",
         "NESTED_TALENT_SOURCE_ONLY_GENERIC_ROUTING_FAIL")
    return {"schema":SCHEMA,"status":"PASS_SYNTHETIC_STATIC",
            "negative_controls":n,"cpp_factory_dependency_route":"PASS",
            "opaque_loadout_does_not_prove_selected_talent":True,
            "WCL_API_calls":0,"new_native_simulations":0}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source-root",type=Path)
    p.add_argument("--adapter",type=Path)
    p.add_argument("--native-lifecycle",type=Path)
    p.add_argument("--out",type=Path)
    a=p.parse_args()
    if all(v is None for v in vars(a).values()):
        print(json.dumps(selftest(),sort_keys=True));return
    need(all(v is not None for v in vars(a).values()),
         "ALL_PINNED_ORIGINAL_SOURCE_AND_NATIVE_INPUTS_REQUIRED")
    root=a.source_root.resolve(strict=True)
    rev=subprocess.run(["git","-C",str(root),"rev-parse","HEAD"],check=True,
                       text=True,capture_output=True).stdout.strip()
    need(rev==UPSTREAM,"ORIGINAL_SIMC_SOURCE_COMMIT_NOT_PINNED")
    plan=json.loads(a.adapter.read_bytes())
    valid_adapter(plan)
    classpath=plan["source_class_path"]
    profpath=plan["source_profile_path"]
    need(classpath.startswith("engine/class_modules/sc_") and
         classpath.endswith(".cpp") and ".." not in classpath and
         profpath.startswith("profiles/") and profpath.endswith(".simc") and
         ".." not in profpath,"UNSAFE_OR_NONCLASS_SPEC_ADAPTER_PATH")
    raw=a.native_lifecycle.read_bytes()
    need(all(case.get("expected_native_evidence_sha256")==sha256(raw).hexdigest()
             for case in plan["cases"]),
         "SOURCE_ADAPTER_NOT_THE_PINNED_NATIVE_LIFECYCLE_BYTES")
    result=link((root/classpath).read_text("utf-8"),
                (root/"engine/action/action.cpp").read_text("utf-8"),
                (root/profpath).read_bytes(),json.loads(raw),plan)
    result["verified_native_lifecycle_sha256"]=sha256(raw).hexdigest()
    result["source_action_constructor_cpp_sha256"]=sha256(
        (root/"engine/action/action.cpp").read_bytes()).hexdigest()
    result["adapter_sha256"]=sha256(a.adapter.read_bytes()).hexdigest()
    from simc_apl_semantic_ir_v2 import canonical
    a.out.parent.mkdir(parents=True,exist_ok=True)
    with a.out.open("xb") as f:f.write(canonical(result))
    print("GENERIC_SIMC_SPELL_DEPENDENCY_SHA256="+sha256(a.out.read_bytes()).hexdigest())
    print("GENERIC_SIMC_SPELL_DEPENDENCY_SUMMARY="+json.dumps(
        {"spec":result["spec_key"],"cases":[
             {"source":c["source_action"],"dependency":
              c["source_path_provenance"]["source_constructor_first_spell_data_input"],
              "talent_selected":c["original_talent_selected_status"]}
             for c in result["source_to_factory_and_constructor_dependencies"]]},
        sort_keys=True))

if __name__=="__main__":main()
