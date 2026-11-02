#!/usr/bin/env python3
"""Generic source-faithful SimC APL ordered IF/ELSE research IR.

An APL row is an ordered hypothesis, not verified player advice. The evaluator
uses three-valued guards and separate READY/NOT_READY/UNKNOWN readiness, with
strict PRE source timestamps for imported WCL facts. It cannot select a
recommended spell when readiness of any higher-priority eligible action is
unproven. Safe default: offline synthetic self-test, no API or secrets.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re

POLICY="ZROT_GENERAL_ROTATION_OPENER_DUMMY_TRAINER_20261102_V1"
PROFILE_BLOB_SHA1="3225992ed5b754ad5d61e8b785d9d859f1eed1be"
TOKENS=re.compile(r"<=|>=|!=|==|[&|!()<>]=?|[A-Za-z_][A-Za-z0-9_.]*|\d+(?:\.\d+)?")
ROW_RE=re.compile(r"^actions(?:\.([a-z_]+))?(\+?=)(?:/)?(.+)$")
ALLOWED_OPS={"&","|","!","(",")","=","==","!=",">","<",">=","<="}

class APLError(ValueError):pass

def canonical(x):
    return (json.dumps(x,sort_keys=True,separators=(",",":"),allow_nan=False)+"\n").encode()

def sha(data):
    return hashlib.sha256(data).hexdigest()

def lex(s):
    if not isinstance(s,str) or len(s)>500:raise APLError("APL_EXPRESSION_SIZE")
    out=[];pos=0
    for m in TOKENS.finditer(s):
        if m.start()!=pos:raise APLError("UNSUPPORTED_APL_TOKEN_AT_"+str(pos))
        out.append(m.group());pos=m.end()
    if pos!=len(s) or not out:raise APLError("INCOMPLETE_APL_EXPRESSION")
    return out

class Parser:
    def __init__(self,s):
        self.tokens=lex(s);self.pos=0
    def eat(self,v=None):
        if self.pos>=len(self.tokens):raise APLError("TRUNCATED_APL_EXPRESSION")
        t=self.tokens[self.pos]
        if v is not None and v!=t:raise APLError("UNEXPECTED_TOKEN")
        self.pos+=1
        return t
    def peek(self):
        return self.tokens[self.pos] if self.pos<len(self.tokens) else None
    def parse(self):
        e=self.or_expr()
        if self.peek() is not None:raise APLError("TRAILING_APL_TOKENS")
        return e
    def or_expr(self):
        x=self.and_expr()
        while self.peek()=="|":
            self.eat("|");x=["OR",x,self.and_expr()]
        return x
    def and_expr(self):
        x=self.not_expr()
        while self.peek()=="&":
            self.eat("&");x=["AND",x,self.not_expr()]
        return x
    def not_expr(self):
        if self.peek()=="!":
            self.eat("!");return ["NOT",self.not_expr()]
        return self.compare()
    def compare(self):
        x=self.atom()
        if self.peek() in ("=","==","!=",">","<",">=","<="):
            op=self.eat()
            x=["CMP",op,x,self.atom()]
        return x
    def atom(self):
        if self.peek()=="(":
            self.eat("(");x=self.or_expr();self.eat(")");return x
        t=self.eat()
        if t in ALLOWED_OPS:raise APLError("EXPECTED_OPERAND")
        if re.fullmatch(r"\d+(?:\.\d+)?",t):
            return ["NUM",float(t) if "." in t else int(t)]
        return ["KEY",t]

def parse_condition(x):
    if x is None:return ["BOOL",True]
    return Parser(x).parse()

def symbols(ast):
    kind=ast[0]
    if kind=="KEY":return {ast[1]}
    if kind in ("NUM","BOOL"):return set()
    if kind=="NOT":return symbols(ast[1])
    if kind in ("AND","OR"):return symbols(ast[1])|symbols(ast[2])
    if kind=="CMP":return symbols(ast[2])|symbols(ast[3])
    raise APLError("UNKNOWN_AST_NODE")

def _tri_boolean(value):
    return value if type(value) is bool else None

def eval_ast(ast,facts,action_ts):
    """Return bool/number/UNKNOWN; every observed fact must be strictly PRE."""
    k=ast[0]
    if k in ("NUM","BOOL"):return ast[1]
    if k=="KEY":
        row=facts.get(ast[1])
        if not isinstance(row,dict):return None
        if row.get("provenance") not in ("OFFICIAL_SOURCE_DEFINITION","STRICT_PRE_OBSERVATION"):
            return None
        if row["provenance"]=="STRICT_PRE_OBSERVATION":
            ts=row.get("timestamp")
            if type(ts) not in (int,float) or type(action_ts) not in (int,float) or ts>=action_ts:
                return None
        val=row.get("value")
        return val if type(val) in (int,float,bool) else None
    if k=="NOT":
        x=_tri_boolean(eval_ast(ast[1],facts,action_ts))
        return None if x is None else not x
    if k=="AND":
        left=_tri_boolean(eval_ast(ast[1],facts,action_ts))
        if left is False:return False
        right=_tri_boolean(eval_ast(ast[2],facts,action_ts))
        return False if right is False else (True if left is True and right is True else None)
    if k=="OR":
        left=_tri_boolean(eval_ast(ast[1],facts,action_ts))
        if left is True:return True
        right=_tri_boolean(eval_ast(ast[2],facts,action_ts))
        return True if right is True else (False if left is False and right is False else None)
    if k=="CMP":
        left=eval_ast(ast[2],facts,action_ts)
        right=eval_ast(ast[3],facts,action_ts)
        if left is None or right is None:return None
        op=ast[1]
        return {"=":lambda a,b:a==b, "==":lambda a,b:a==b,
                "!=":lambda a,b:a!=b, ">":lambda a,b:a>b,
                "<":lambda a,b:a<b, ">=":lambda a,b:a>=b,
                "<=":lambda a,b:a<=b}[op](left,right)
    raise APLError("UNKNOWN_AST_NODE")

def _parse_action(text):
    # Commas following an action can carry many APL attributes, some of which
    # are NOT guard clauses; preserve rather than silently dropping them.
    tokens=text.split(",")
    command=tokens[0]
    if not re.fullmatch("[a-z_][a-z_0-9]*",command):
        raise APLError("BAD_ACTION_TOKEN")
    fields=[]
    condition=None
    for token in tokens[1:]:
        if "=" not in token:raise APLError("UNSUPPORTED_ACTION_FIELD")
        k,v=token.split("=",1)
        if k=="if":
            if condition is not None:raise APLError("REPEATED_IF")
            condition=v
        fields.append({"key":k,"value":v})
    return command,fields,condition

def profile_to_ir(raw):
    blob=hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()
    if blob!=PROFILE_BLOB_SHA1:raise APLError("PROFILE_SOURCE_BLOB_MISMATCH")
    lists={}
    for lineno,line in enumerate(raw.decode().splitlines(),start=1):
        match=ROW_RE.fullmatch(line)
        if not match:continue
        list_name=match[1] or "default"
        operator=match[2]
        if operator=="=":
            if list_name in lists:raise APLError("DUPLICATE_ACTION_LIST_REINITIALIZATION")
            lists[list_name]=[]
        elif list_name not in lists:
            raise APLError("APPEND_TO_UNDECLARED_APL")
        action,attrs,condition=_parse_action(match[3])
        guard=parse_condition(condition)
        lists[list_name].append({
            "index":len(lists[list_name]),
            "source_line":lineno,
            "source_sha256":sha(line.encode()),
            "action":action,
            "attributes":attrs,
            "if_source":condition,
            "if_ast":guard,
            "symbolic_dependencies":sorted(symbols(guard)),
            "readiness":"NOT_INFERRED_FROM_APL",
            "mandatory_priority_claim":False,
            "gameplay_optimality_proven":False})
    for needed in ("default","slayer","slayer_aoe"):
        if not lists.get(needed):raise APLError("REQUIRED_APL_MISSING")
    return {"schema":"ZrotSimcSourceOrderedConditionalIRV1",
      "scope_policy_id":POLICY,
      "source_profile_blob_sha1":blob,
      "status":"SOURCE_APL_HYPOTHESES_NOT_WCL_VERIFIED",
      "ordered_lists":lists,
      "source_rows_total":sum(len(v) for v in lists.values()),
      "ready_to_train":False}

def decide(rows,facts,action_ts,readiness):
    """Branch-safe decision; never bypass an unknown higher-priority action."""
    blocked=[]
    for row in rows:
        name=row["action"]
        state=eval_ast(row["if_ast"],facts,action_ts)
        rd=readiness.get(str(row["index"]), "UNKNOWN")
        if rd not in ("READY","NOT_READY","UNKNOWN"):
            raise APLError("INVALID_ACTION_READINESS")
        if state is False or rd=="NOT_READY":
            continue
        if state is None or rd=="UNKNOWN":
            blocked.append({"index":row["index"],"action":name,
                "guard":"UNKNOWN" if state is None else "TRUE",
                "readiness":rd})
            # Cannot skip this potentially higher priority usable action.
            return {"verdict":"UNKNOWN","expected_action":None,
                    "blocked_by":blocked,"other_actions_eligible":"UNKNOWN"}
        return {"verdict":"HYPOTHETICAL_FIRST_ELIGIBLE_APL_ROW",
                "expected_action":name,"source_priority_index":row["index"],
                "readiness_source":"EXTERNALLY_SUPPLIED",
                "validated_against_WCL":False,
                "wrong_cast_claim":False}
    return {"verdict":"UNKNOWN","expected_action":None,
            "blocked_by":blocked,"reason":"NO_ELIGIBLE_APL_ROW_PROVEN"}

def source_wcl_hero_branch(ir,hero):
    """Only transfer explicit hero-guard truth, never active_enemies or readiness."""
    rows=hero.get("branch_statuses",[])
    result={}
    for r in rows:
        name=r.get("action_list")
        if name not in ("slayer","slayer_aoe","thane","thane_aoe"):continue
        value=r.get("wcl_pre_hero_talent_guard")
        if value not in ("TRUE","FALSE","UNKNOWN"):raise APLError("HERO_SOURCE_CONTRACT_UNRECOGNIZED")
        if value=="TRUE":
            result[name]={"verdict":"TALENT_GUARD_TRUE_TARGET_COUNT_UNKNOWN",
                          "source_apl_row_present":any(t["action"]=="run_action_list" and
                            {"key":"name","value":name} in t["attributes"]
                            for t in ir["ordered_lists"]["default"])}
        elif value=="FALSE":
            result[name]={"verdict":"TALENT_GUARD_FALSE_BRANCH_EXCLUDED",
                          "source_apl_row_present":True}
        else:
            result[name]={"verdict":"UNKNOWN_TALENT_GUARD",
                          "source_apl_row_present":True}
    return result

def real_receipt(profile_path,hero_path):
    from wcl_simc_postlock_real_audit_v1 import _sha as source_sha
    with profile_path.open("rb") as f:ir=profile_to_ir(f.read())
    blob=hero_path.read_bytes()
    if source_sha(blob)!="8f3d5f83c3d66474f5dfd2f5007924ea279a3872f331d2fd6248b30718cdc847":
        raise APLError("HERO_GUARD_SOURCE_RECEIPT_CHANGED")
    hero=json.loads(blob)
    if hero.get("schema")!="ZrotPostlockSimcTalentBranchApplicabilityV1" or hero.get("scope_policy_id")!=POLICY:
        raise APLError("HERO_GUARD_SOURCE_CONTRACT_INVALID")
    cases={}
    for role in ("discovery","holdout"):
        truth=source_wcl_hero_branch(ir,hero[role])
        if len(truth)!=4:raise APLError("REQUIRED_SOURCE_GUARD_UNOBSERVED")
        if any(t["verdict"]!="TALENT_GUARD_TRUE_TARGET_COUNT_UNKNOWN" for
               n,t in truth.items() if n.startswith("slayer")):
            raise APLError("SLAYER_TRUE_PREPROOF_MISSING")
        cases[role]=truth
    return {"schema":"ZrotSimcSlayerConditionalPriorityResearchIRV1",
       "scope_policy_id":POLICY,
       "status":"APL_CONDITIONS_EXTRACTED_WCL_TARGET_AND_READINESS_UNKNOWN",
       "simc_profile_blob_sha1":ir["source_profile_blob_sha1"],
       "hero_source_sha256":source_sha(blob),
       "source_ordered_action_counts":{k:len(v) for k,v in ir["ordered_lists"].items()},
       "source_list_rows":{
         k:[{"index":r["index"],"action":r["action"],"if_source":r["if_source"],
             "if_ast":r["if_ast"],"symbolic_dependencies":r["symbolic_dependencies"],
             "source_sha256":r["source_sha256"]}
            for r in ir["ordered_lists"][k]]
         for k in ("slayer","slayer_aoe")},
       "hero_gates_at_wcl":cases,
       "same_profile_and_wcl_hero_tree":"SLAYER_VERIFIED",
       "active_enemies_at_WCL_cast":"UNKNOWN",
       "WCL_Rage_scaled_units":"UNVERIFIED",
       "gcd_cooldown_charges_and_cost_readiness":"UNKNOWN",
       "native_SimC_APL_replay_at_WCL_timestamp":"NOT_RUN",
       "recommendation_eligible":False,"dummy_mistake_verdict":"UNKNOWN",
       "MAIN_promotion":False}

def selftest():
    ast=parse_condition("buff.enrage.up&rage>=100|!cooldown.bladestorm.ready")
    assert symbols(ast)=={"buff.enrage.up","rage","cooldown.bladestorm.ready"}
    state={"buff.enrage.up":{"value":True,"provenance":"STRICT_PRE_OBSERVATION","timestamp":80},
           "rage":{"value":110,"provenance":"STRICT_PRE_OBSERVATION","timestamp":90},
           "cooldown.bladestorm.ready":{"value":True,"provenance":"STRICT_PRE_OBSERVATION","timestamp":95}}
    assert eval_ast(ast,state,100) is True
    assert eval_ast(ast,state,90) is None
    assert eval_ast(parse_condition("!buff.enrage.up"),state,100) is False
    assert eval_ast(parse_condition("rage>110"),state,100) is False
    assert eval_ast(parse_condition("unknown&rage>110"),state,100) is False
    assert eval_ast(parse_condition("unknown|rage>110"),state,100) is None
    assert eval_ast(parse_condition("unknown|rage>=100"),state,100) is True
    for illegal in ("x;evil","(rage>100","rage>=100 garbage","foo+bar"):
        try:parse_condition(illegal)
        except APLError:pass
        else:raise AssertionError("UNSUPPORTED_EXPRESSION_ACCEPTED")
    rows=[
      {"index":0,"action":"recklessness","if_ast":parse_condition(None)},
      {"index":1,"action":"rampage","if_ast":parse_condition("rage>=100")},
      {"index":2,"action":"bloodthirst","if_ast":parse_condition(None)}
    ]
    a=decide(rows,state,100,{})
    assert a["verdict"]=="UNKNOWN" and a["blocked_by"][0]["action"]=="recklessness"
    a=decide(rows,state,100,{"0":"NOT_READY","1":"READY"})
    assert a["expected_action"]=="rampage" and a["wrong_cast_claim"] is False
    a=decide(rows,{},100,{"0":"NOT_READY","1":"READY","2":"READY"})
    assert a["verdict"]=="UNKNOWN" and a["blocked_by"][0]["action"]=="rampage"
    assert parse_condition("buff.enrage.remains<gcd")[0]=="CMP"
    return {"status":"PASS_OFFLINE_SYNTHETIC",
            "checks":15,"actual_WCL_or_SimC_loaded":False,
            "auto_trainer_wrong_cast_flags":0}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--profile",type=Path)
    p.add_argument("--hero-guard-receipt",type=Path)
    p.add_argument("--out",type=Path)
    a=p.parse_args()
    if a.profile is None and a.hero_guard_receipt is None:
        value=selftest()
    elif a.profile and a.hero_guard_receipt:
        value=real_receipt(a.profile,a.hero_guard_receipt)
    else:p.error("--profile and --hero-guard-receipt required together")
    blob=canonical(value)
    if a.out:
        a.out.parent.mkdir(parents=True,exist_ok=True)
        with a.out.open("xb") as f:f.write(blob)
        print("SIMC_GENERAL_PRIORITY_IR_RECEIPT_SHA256="+sha(blob))
    else:print(blob.decode(),end="")

if __name__=="__main__":main()
