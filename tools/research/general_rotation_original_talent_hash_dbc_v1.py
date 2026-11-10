#!/usr/bin/env python3
"""Source-neutral, source-pinned SimC trait hash + generated DBC decoder.

Reimplement ONLY the input codec used by original player_t::parse_traits_hash
and trait_data_t::data(), not the SimC action scheduler or live WoW mechanics.
The original spell/talent metadata and profile must be taken from the same
exact pinned SimC git commit, asserted by an external SpecAdapter. Decode all
nodes, enforce node order/choice/rank/spec checks, and return evidence for
adapter-identified trait node entries. The original source's free-grant
id_spec_starter rule is evaluated separately. An additional source/native
dependency receipt is optional and does NOT affect decoded selections.

No-arg: static synthetic tests with negative controls. No WCL/Blizzard API,
no original SimC action_ready invocation, no spec names in generic module.
"""
from __future__ import annotations
import argparse
from collections import defaultdict
from hashlib import sha1, sha256
import json
from pathlib import Path
import re
import subprocess

SCHEMA="ZrotGenericPinnedSimCTalentHashDbcDecodeV1"
ADAPTER_SCHEMA="ZrotGenericPinnedSimCTalentHashAdapterV1"
LINK_SCHEMA="ZrotOriginalNativeGenericSpellDataDependencyLinkV1"
POLICY="ZROT_GENERAL_ROTATION_OPENER_DUMMY_TRAINER_20261102_V1"
ALPHABET="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"
ROW=re.compile(
    r'^\s*\{\s*'+r'\s*,\s*'.join([r'(-?\d+)']*13)+
    r'\s*,\s*"((?:[^"\\]|\\.)*)"\s*,\s*'
    r'\{\s*([^{}]+)\s*\}\s*,\s*\{\s*([^{}]+)\s*\}\s*,\s*'
    r'(-?\d+)\s*,\s*(-?\d+)\s*\},?\s*$'
)
TABLE_HEADER=re.compile(r'\bstd::array<trait_data_t,\s*(\d+)>\s+__trait_data_data\b')
REV=re.compile(r'^[0-9a-f]{40}$')
LABEL=re.compile(r'^[A-Za-z0-9_\- ]{1,160}$')

class TalentDecodeError(ValueError):pass
def need(ok,why):
    if not ok:raise TalentDecodeError(why)

def gitblob(data:bytes)->str:
    return sha1(b"blob "+str(len(data)).encode("ascii")+b"\0"+data).hexdigest()

def read_config(raw:bytes)->dict:
    x=json.loads(raw)
    need(x.get("schema")==ADAPTER_SCHEMA and x.get("policy_id")==POLICY and
         REV.fullmatch(x.get("source_revision","")) is not None and
         REV.fullmatch(x.get("profile_git_blob","")) is not None and
         LABEL.fullmatch(x.get("spec_key","")) is not None and
         isinstance(x.get("class_id"),int) and 1<=x["class_id"]<=20 and
         isinstance(x.get("spec_id"),int) and 1<=x["spec_id"]<=65535 and
         isinstance(x.get("cases"),list) and 1<=len(x["cases"])<=16,
         "UNBOUND_SIMC_TRAIT_ADAPTER_REVISION_OR_SCHEMA")
    for c in x["cases"]:
        need(all(isinstance(c.get(k),int) and c[k]>0
                 for k in ("trait_node","trait_entry","trait_spell")) and
             LABEL.fullmatch(c.get("trait_name","")) is not None and
             isinstance(c.get("trait_tree"),int) and 0<=c["trait_tree"]<=8,
             "SOURCE_CASE_ENTRY_NODE_SPELL_OR_NAME_UNPINNED")
    need(x.get("source_profile_path","").startswith("profiles/") and
         x["source_profile_path"].endswith(".simc") and
         ".." not in x["source_profile_path"] and
         x.get("source_trait_data_path")==
         "engine/dbc/generated/trait_data.inc",
         "UNSAFE_OR_UNSUPPORTED_SIMC_SOURCE_PATH")
    return x

def check_source_codec(player_cpp:str,trait_cpp:str):
    # Verify the original parser and DBC source contract, not a guessed
    # contemporary WoW import format. Change codec after source review if
    # serialization changes, never silently interpret a new format.
    for marker in (
        "static void parse_traits_hash(", "static bool generate_tree_nodes(",
        "std::map<unsigned, std::vector<std::pair<const trait_data_t*, unsigned>>> tree_nodes;",
        "get_bit( version_bits )","get_bit( spec_bits )",
        "get_bit( tree_bits )","get_bit( rank_bits )",
        "get_bit( choice_bits )","trait_data_t::data( class_idx, i",
    ):
        need(marker in player_cpp,"ORIGINAL_SIMC_HASH_DECODER_CONTRACT_DRIFT")
    for name,value in (
        ("LOADOUT_SERIALIZATION_VERSION",2),
        ("version_bits",8),("spec_bits",16),("tree_bits",128),
        ("rank_bits",6),("choice_bits",2),("byte_size",6),
    ):
        need(re.search(r'\b'+re.escape(name)+r'\s*=\s*'+str(value)+r'\s*;',player_cpp),
             "ORIGINAL_SIMC_HASH_BIT_CODEC_CHANGED")
    need("trait_data_t::data( unsigned class_id, talent_tree tree" in trait_cpp and
         "range::equal_range" in trait_cpp and
         "return trait->id_spec_starter[ 0 ] && range::contains( trait->id_spec_starter, spec );" in trait_cpp,
         "ORIGINAL_SIMC_TRAIT_DBC_OR_FREE_GRANT_CONTRACT_DRIFT")
    need("if ( !rank )" in player_cpp and
         "return { player };  // Trait not found on player" in player_cpp,
         "ORIGINAL_SIMC_NON_SELECTED_TALENT_RETURN_CONTRACT_DRIFT")

def parse_dbc(inc:str)->list[dict]:
    header=TABLE_HEADER.search(inc)
    need(header is not None,"PINNED_TRAIT_TABLE_HEADER_MISSING")
    declared=int(header[1])
    need(1<=declared<=12000,"UNBOUNDED_OR_EMPTY_GENERATED_TRAIT_TABLE")
    out=[]
    for line in inc.splitlines():
        match=ROW.fullmatch(line)
        if not match:continue
        v=match.groups()
        fields=[int(t) for t in v[:13]]
        def array(segment):
            values=[int(t.strip()) for t in segment.split(",")]
            need(len(values)==4 and all(x>=0 for x in values),
                 "TRAIT_SPEC_LIST_SCHEMA_CHANGED")
            return values
        rec={
          "tree":fields[0],"class_id":fields[1],
          "entry":fields[2],"node":fields[3],
          "max_rank":fields[4],"trait_definition":fields[6],
          "spell":fields[7],"starter":array(v[15]),
          "name":v[13],"spec":array(v[14]),
          "subtree":int(v[16]),"type":int(v[17])
        }
        need(rec["node"]>0 and rec["entry"]>0 and rec["max_rank"]>=0 and
             0<=rec["type"]<=3 and 0<=rec["tree"]<=8,
             "TRAIT_ROW_INVALID_IDENTITIES_OR_TYPES")
        out.append(rec)
    need(len(out)==declared,"TRAIT_TABLE_RECORD_COUNT_OR_FORMAT_DRIFT")
    return out

class Reader:
    def __init__(self,encoded:str):
        need(encoded and len(encoded)<=8192 and
             all(c in ALPHABET for c in encoded),"INVALID_BASE64_TALENT_HASH")
        self.bits=[(ALPHABET.index(c)>>i)&1 for c in encoded for i in range(6)]
        self.pos=0
    def read(self,n:int)->int:
        need(0<=n<=128 and self.pos+n<=len(self.bits),
             "ORIGINAL_TALENT_HASH_TRUNCATED_OR_OVERREAD")
        ans=0
        for i in range(n):
            ans|=self.bits[self.pos+i]<<i
        self.pos+=n
        return ans
    def padding_ok(self):
        return (len(self.bits)-self.pos<6 and
                all(b==0 for b in self.bits[self.pos:]))

def _profile_values(raw:bytes):
    lines=raw.decode("utf-8").splitlines()
    result=defaultdict(list)
    for line in lines:
        line=line.strip()
        if not line or line.startswith(("#","//")) or "=" not in line:continue
        key,value=line.split("=",1)
        if key in ("talents","class_talents","spec_talents","hero_talents",
                   "enable_all_talents","load_default_talents","spec","source"):
            result[key].append(value)
    need(len(result["talents"])==1 and len(result["spec"])==1,
         "MISSING_OR_AMBIGUOUS_PROFILE_TALENTS_SPEC")
    # Do not misclassify a selected/unselected entry if additional explicit
    # player_traits mutations can override the encoded import state.
    for k in ("class_talents","spec_talents","hero_talents"):
        need(not any(v.strip() for v in result[k]),
             "SUPPLEMENTAL_TALENT_PROFILE_OVERRIDES_UNRESOLVED")
    for k in ("enable_all_talents","load_default_talents"):
        need(not any(v.strip().lower() in ("1","true","yes") for v in result[k]),
             "GLOBAL_TALENT_OVERRIDE_UNRESOLVED")
    return result

def decode(encoded:str,trait_rows:list[dict],class_id:int,spec_id:int)->dict:
    reader=Reader(encoded)
    version=reader.read(8);observed_spec=reader.read(16)
    need(version==2,"UNSUPPORTED_TALENT_SERIALIZATION_VERSION")
    need(observed_spec==spec_id,"ORIGINAL_TALENT_HASH_SPEC_MISMATCH")
    treehash=reader.read(128)
    # SimC generate_tree_nodes iterates all tree_index enums, group by node id
    # in std::map, preserving generated DBC per-node entry ordering.
    nodes=defaultdict(list)
    filtered=[t for t in trait_rows if t["class_id"]==class_id]
    need(bool(filtered),"NO_DBC_TRAITS_FOR_CLASS")
    for tree in sorted({t["tree"] for t in filtered}):
        for t in filtered:
            if t["tree"]==tree:
                nodes[t["node"]].append(t)
    need(len(nodes)<=1500,"INVALID_CLASS_TREE_NODE_COHORT")
    selected=[];node_selection={}
    for id in sorted(nodes):
        node=nodes[id];first=node[0]
        has=reader.read(1)
        if not has:
            node_selection[id]={"selected_bit":False,"rank":0,"entry":None}
            continue
        if first["tree"]!=3 and any(first["spec"]) and spec_id not in first["spec"]:
            raise TalentDecodeError("SELECTED_DBC_TRAIT_NOT_AVAILABLE_TO_SPEC")
        max_rank=(sum(t["max_rank"] for t in node)
                  if first["type"]==1 else first["max_rank"])
        need(max_rank>0,"SELECTED_NODE_MAX_RANK_ZERO")
        rank=max_rank;chosen=first;choice_idx=0
        purchased=reader.read(1)
        if not purchased:
            rank=1
        else:
            partial=reader.read(1)
            if partial:
                need(first["type"]==1 or len(node)==1,
                     "NON_CHOICE_PARTIAL_NODE_HAS_MULTIPLE_ENTRIES")
                rank=reader.read(6)
                need(0<rank<max_rank,"INVALID_PARTIAL_NODE_RANK")
            if reader.read(1):
                need(first["type"] in (2,3),"CHOICE_BIT_ON_NON_CHOICE_NODE")
                choice_idx=reader.read(2)
                need(choice_idx<len(node),"CHOICE_INDEX_OUTSIDE_DBC_NODE")
                chosen=node[choice_idx]
        node_selection[id]={"selected_bit":True,"rank":rank,
                            "entry":chosen["entry"],"choice_index":choice_idx}
        if first["type"]==1:
            remaining=rank
            for t in node:
                allocated=min(remaining,t["max_rank"])
                if allocated:
                    selected.append({"node":id,"entry":t["entry"],"rank":allocated})
                    remaining-=allocated
                if not remaining:break
            need(remaining==0,"TIERED_NODE_UNALLOCATED_RANK")
        else:
            selected.append({"node":id,"entry":chosen["entry"],"rank":rank})
    need(reader.padding_ok(),"TALENT_HASH_TRAILING_BITS_OR_NODE_ORDER_DRIFT")
    return {
      "serialization_version":version,"spec_id":observed_spec,
      "ignored_original_tree_hash_nonzero":bool(treehash),
      "class_id":class_id,"trait_row_count":len(filtered),
      "tree_node_count":len(nodes),
      "chosen_trait_entry_count":len(selected),
      "bits_consumed":reader.pos,
      "bits_total":len(reader.bits),
      "selected":selected,"node_selection":node_selection,
      "rows":filtered
    }

def analyze(profile:bytes,inc:str,player_cpp:str,trait_cpp:str,
            cfg:dict,prior:dict|None=None,prior_sha:str|None=None)->dict:
    need(cfg.get("schema")==ADAPTER_SCHEMA and cfg.get("policy_id")==POLICY,
         "TRAIT_ADAPTER_SCHEMA_DRIFT")
    need(gitblob(profile)==cfg.get("profile_git_blob"),
         "PROFILE_NOT_ORIGINAL_PINNED_GIT_BLOB")
    check_source_codec(player_cpp,trait_cpp)
    p=_profile_values(profile)
    rows=parse_dbc(inc)
    d=decode(p["talents"][0],rows,cfg["class_id"],cfg["spec_id"])
    if prior is not None:
        need(prior.get("schema")==LINK_SCHEMA and prior.get("policy_id")==POLICY and
             prior.get("source_revision")==cfg["source_revision"] and
             prior.get("spec_key")==cfg["spec_key"] and
             prior.get("profile_git_blob")==cfg["profile_git_blob"] and
             prior_sha==cfg.get("expected_prior_native_link_sha256"),
             "ORIGINAL_NATIVE_DEPENDENCY_NOT_SAME_PINNED_PROFILE")
    results=[]
    for c in cfg["cases"]:
        match=[t for t in d["rows"] if
               t["node"]==c["trait_node"] and
               t["entry"]==c["trait_entry"] and
               t["spell"]==c["trait_spell"] and
               t["tree"]==c["trait_tree"] and t["name"]==c["trait_name"]]
        need(len(match)==1,"DBC_NODE_ENTRY_SPELL_NAME_NOT_EXACTLY_UNIQUE")
        row=match[0]
        allocated=next((x["rank"] for x in d["selected"]
                        if x["entry"]==row["entry"]),0)
        free_grant=bool(row["starter"][0] and cfg["spec_id"] in row["starter"])
        final_rank=max(allocated,1 if free_grant else 0)
        status=("PROFILE_SELECTED_RANK" if allocated else
                ("PROFILE_UNSELECTED_BUT_FREE_GRANTED" if free_grant
                 else "PROFILE_NOT_SELECTED_NOT_GRANTED"))
        direct_join="NOT_REQUESTED"
        if prior is not None:
            linked=[x for x in prior["source_to_factory_and_constructor_dependencies"]
                    if x["source_action"]==c.get("source_action") and
                    x["original_native_spell_data"]=="NOT_FOUND" and
                    x["original_native_background"] is True]
            need(len(linked)==1,"NATIVE_NOT_FOUND_EVIDENCE_NOT_SAME_ACTION")
            direct_join="SAME_PROFILE_SPELL_INPUT_AND_NATIVE_NOT_FOUND"
        results.append({
            "trait_name":row["name"],"trait_entry":row["entry"],
            "trait_node":row["node"],"trait_spell":row["spell"],
            "trait_tree":row["tree"],"trait_max_rank":row["max_rank"],
            "source_profile_hash_node_selected":d["node_selection"][row["node"]]["selected_bit"],
            "source_profile_allocated_rank":allocated,
            "source_dbc_free_grant_to_spec":free_grant,
            "source_profile_effective_rank_after_free_grant":final_rank,
            "source_profile_status":status,
            "native_dependency_join":direct_join,
            "current_Retail_user_talent_selected":"UNKNOWN",
            "current_Retail_physical_ability_READY":"UNKNOWN"
        })
    return {
       "schema":SCHEMA,"policy_id":POLICY,"source_revision":cfg["source_revision"],
       "spec_key":cfg["spec_key"],"class_id":cfg["class_id"],"spec_id":cfg["spec_id"],
       "source_profile_git_blob":cfg["profile_git_blob"],
       "source_dbc_sha256":sha256(inc.encode()).hexdigest(),
       "source_player_cpp_sha256":sha256(player_cpp.encode()).hexdigest(),
       "profile_talent_hash_codec_version":d["serialization_version"],
       "profile_talent_tree_hash_ignored_by_SimC":True,
       "source_trait_rows_for_class":d["trait_row_count"],
       "source_trait_nodes":d["tree_node_count"],
       "source_allocated_trait_entries":d["chosen_trait_entry_count"],
       "source_bits_consumed":d["bits_consumed"],
       "source_bits_total":d["bits_total"],
       "cases":results,
       "original_source_parse_and_DBC_proven":True,
       "supplemental_talents_overrides":"NONE",
       "other_source_profile_options_not_mechanically_replayed":True,
       "native_action_talent_value_read_independently":"NOT_RUN",
       "Blizzard_current_patch_mechanic_parity":"UNKNOWN",
       "WCL_independent_blind":"NOT_RUN",
       "General_Rotation_priority_promoted":0,"dummy_wrong_cast":"UNKNOWN",
       "MAIN_promoted":False
    }

def selftest()->dict:
    def line(tree,cl,entry,node,rank,name,typ=0,spec=42,starter=0,spell=None):
        return (f'  {{ {tree}, {cl}, {entry}, {node}, {rank}, 0, {entry+100}, '
                f'{spell or entry+200}, 0, 0, 1, 1, 100, "{name}", '
                f'{{ {spec}, 0, 0, 0 }}, {{ {starter}, 0, 0, 0 }}, 0, {typ} }},')
    inc='static constexpr std::array<trait_data_t, 3> __trait_data_data { {\n'+(
        line(2,9,111,100,1,"Alpha")+'\n'+
        line(2,9,222,200,1,"Beta",typ=2)+'\n'+
        line(2,9,223,200,1,"Gamma",typ=2))+'\n} };'
    db=parse_dbc(inc)
    def pack(vals):
        bits=[]
        for n,v in vals:
            for i in range(n):bits.append((v>>i)&1)
        while len(bits)%6:bits.append(0)
        return ''.join(ALPHABET[sum(bits[i+j]<<j for j in range(6))]
                       for i in range(0,len(bits),6))
    # node100 unselected; node200 selected, purchased, full rank, choice idx1
    h=pack([(8,2),(16,42),(128,0),(1,0),(1,1),(1,1),(1,0),
            (1,1),(2,1)])
    d=decode(h,db,9,42)
    need(d["chosen_trait_entry_count"]==1 and
         d["selected"]==[{"node":200,"entry":223,"rank":1}] and
         d["node_selection"][100]["selected_bit"] is False,
         "SYNTHETIC_CHOICE_OR_ABSENCE_NOT_REPRODUCIBLE")
    failures=0
    for bad,kind in (
        (h+"*","hash"),
        ("AAAA","hash"),
        (pack([(8,3),(16,42),(128,0),(1,0),(1,0)]),"hash"),
        (h,"spec"),
        (h,"class"),
        (h,"traitmissing"),
        (h,"truncated_db"),
        (pack([(8,2),(16,42),(128,0),(1,0),(1,1),(1,1),
               (1,0),(1,1),(2,3)]),"hash")
    ):
        try:
            if kind=="spec":decode(bad,db,9,43)
            elif kind=="class":decode(bad,db,10,42)
            elif kind=="traitmissing":
                need(any(r["entry"]==999 for r in db),"NO_MATCH")
            elif kind=="truncated_db":parse_dbc(inc.replace(
                 "std::array<trait_data_t, 3>","std::array<trait_data_t, 4>"))
            else:decode(bad,db,9,42)
        except TalentDecodeError:failures+=1
        else:raise AssertionError("INVALID_IMPORTED_TALENT_TRAIT_STATE_ACCEPTED")
    need(failures==8,"NEGATIVE_TALENT_HASH_CONTRACT_INCOMPLETE")
    return {"schema":SCHEMA,"status":"PASS_SYNTHETIC_STATIC",
            "negative_controls":failures,
            "mixed_choice_node_synthetic":"PASS",
            "unselected_not_promoted_to_READY":True,
            "new_original_simc_rebuilds":0,"WCL_API_calls":0}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source-root",type=Path)
    p.add_argument("--adapter",type=Path)
    p.add_argument("--prior-native-link",type=Path)
    p.add_argument("--out",type=Path)
    a=p.parse_args()
    if not any(vars(a).values()):
        print(json.dumps(selftest(),sort_keys=True));return
    need(a.source_root is not None and a.adapter is not None and a.out is not None,
         "ORIGINAL_SOURCE_DBC_AND_ADAPTER_REQUIRED")
    cfg=read_config(a.adapter.read_bytes())
    root=a.source_root.resolve(strict=True)
    revision=subprocess.run(["git","-C",str(root),"rev-parse","HEAD"],
             check=True,capture_output=True,text=True).stdout.strip()
    need(revision==cfg["source_revision"],"ORIGINAL_DBC_SOURCE_REVISION_DRIFT")
    prior=None;prior_sha=None
    if a.prior_native_link:
        data=a.prior_native_link.read_bytes()
        prior=json.loads(data)
        prior_sha=sha256(data).hexdigest()
    elif cfg.get("expected_prior_native_link_sha256"):
        raise TalentDecodeError("MISSING_EXPECTED_PINNED_NATIVE_LINK_RECEIPT")
    result=analyze((root/cfg["source_profile_path"]).read_bytes(),
                   (root/cfg["source_trait_data_path"]).read_text("utf-8"),
                   (root/"engine/player/player.cpp").read_text("utf-8"),
                   (root/"engine/dbc/trait_data.cpp").read_text("utf-8"),
                   cfg,prior,prior_sha)
    result["adapter_sha256"]=sha256(a.adapter.read_bytes()).hexdigest()
    result["prior_native_link_sha256"]=prior_sha
    a.out.parent.mkdir(parents=True,exist_ok=True)
    from simc_apl_semantic_ir_v2 import canonical
    with a.out.open("xb") as f:f.write(canonical(result))
    print("GENERIC_ORIGINAL_TALENT_DBC_HASH_SHA256="+sha256(a.out.read_bytes()).hexdigest())
    print("GENERIC_ORIGINAL_TALENT_DBC_HASH_SUMMARY="+json.dumps({
       "spec":result["spec_key"],"nodes":result["source_trait_nodes"],
       "cases":result["cases"]},sort_keys=True))
if __name__=="__main__":main()
