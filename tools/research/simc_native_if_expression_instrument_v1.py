#!/usr/bin/env python3
"""Passive pinned SimC action_t::action_ready if-expression observation patch.

Patches the existing native if_expr->success() call site to use its exact
single return value, logging the result only AFTER it is evaluated.
Does not call expression again, does not probe unrelated readiness checks,
and does not alter state semantics. Native pristine-vs-patched action-sequence
differential remains mandatory before believing real emitted evidence.

No CLI args runs synthetic exact-anchor regression. No WCL involved.
"""
from __future__ import annotations
import argparse, hashlib, json, subprocess
from pathlib import Path

PINNED_COMMIT="b522cded8c26b97dac03fdf56e57a03ec7e8faa6"
ACTION_CPP_BLOB="399ecd9453b3f30bfc2ebf2b3ffd8f56cce8f8d4"
TARGET=Path("engine/action/action.cpp")
BEFORE="bool action_t::action_ready()\n{\n"
AFTER="\nbool action_t::cost_affordable()\n{"
OLD="""  if ( if_expr && !if_expr->success() )
    return false;"""
NEW="""  // zRotationHelper passive evidence: retain ONE native evaluation.
  if ( if_expr )
  {
    const bool zrot_original_if_result = if_expr->success();
    if ( sim->log && player && !player->is_pet() && !player->is_enemy() )
    {
      unsigned zrot_source_ordinal = 0;
      std::string zrot_source_list = "UNKNOWN";
      if ( action_list && signature )
      {
        const auto& zrot_list = *action_list;
        for ( std::size_t zrot_i = 0; zrot_i < zrot_list.action_list.size(); ++zrot_i )
        {
          if ( &( zrot_list.action_list[ zrot_i ] ) == signature )
          {
            zrot_source_list = zrot_list.name_str;
            zrot_source_ordinal = static_cast<unsigned>( zrot_i + 1 );
            break;
          }
        }
      }
      sim->print_log( "ZROT_NATIVE_IF_V1|{}|{}|{}|{}|{}",
        sim->current_time().total_millis(), zrot_source_list,
        zrot_source_ordinal, name_str, zrot_original_if_result ? 1 : 0 );
    }
    if ( !zrot_original_if_result )
      return false;
  }"""

class PatchError(ValueError): pass

def sha(x):return hashlib.sha256(x).hexdigest()
def git_blob(x):return hashlib.sha1(b"blob "+str(len(x)).encode()+b"\0"+x).hexdigest()

def instrument(raw:bytes,*,strict=True)->bytes:
    if strict and git_blob(raw)!=ACTION_CPP_BLOB:
        raise PatchError("PINNED_ACTION_CPP_BLOB_CHANGED")
    text=raw.decode("utf-8")
    if "ZROT_NATIVE_IF_V1" in text:raise PatchError("ALREADY_INSTRUMENTED")
    if text.count(BEFORE)!=1 or text.count(AFTER)!=1:
        raise PatchError("ACTION_READY_FUNCTION_BOUNDARY_CHANGED")
    i=text.index(BEFORE)
    j=text.index(AFTER,i)
    function=text[i:j]
    if function.count(OLD)!=1:
        raise PatchError("NATIVE_IF_EXPR_EVALUATION_SITE_MISMATCH")
    function=function.replace(OLD,NEW)
    if function.count("if_expr->success()")!=1:
        raise PatchError("IF_EXPR_EVALUATED_MORE_THAN_ONCE")
    return (text[:i]+function+text[j:]).encode("utf-8")

def run(root:Path):
    root=root.resolve(strict=True)
    rev=subprocess.run(["git","-C",str(root),"rev-parse","HEAD"],
        check=True,capture_output=True,text=True).stdout.strip()
    if rev!=PINNED_COMMIT:raise PatchError("SIMC_UPSTREAM_COMMIT_CHANGED")
    target=root/TARGET
    original=target.read_bytes()
    patched=instrument(original)
    target.write_bytes(patched)
    return {"schema":"ZrotNativeIfEvaluationPassivePatchReceiptV1",
        "official_simc_commit":rev,
        "original_action_cpp_git_blob_sha1":ACTION_CPP_BLOB,
        "original_action_cpp_sha256":sha(original),
        "instrumented_action_cpp_sha256":sha(patched),
        "single_if_expression_eval_per_callsite":True,
        "missing_or_unreached_if_expression_semantics":"UNKNOWN",
        "native_action_behaviour_validated_with_original":"NOT_YET_RUN",
        "WCL_API_calls":0,"MAIN_promotion":False}

def selftest():
    example=(BEFORE+"  if ( !ready() ) return false;\n"
             +OLD+"\n  return true;\n}\n"+AFTER+"  return true;\n}\n").encode()
    changed=instrument(example,strict=False).decode()
    assert changed.count("if_expr->success()")==1
    assert changed.count("ZROT_NATIVE_IF_V1")==1
    assert changed.count("zrot_source_ordinal")==3
    assert "if ( !zrot_original_if_result )" in changed
    assert changed.index("if_expr->success()")<changed.index("ZROT_NATIVE_IF_V1")
    for bad in (example.replace(b"if_expr->success()",b"if_expr->evaluate()"),
                example.replace(b"if_expr &&",b"if_expr ||")):
        try:instrument(bad,strict=False)
        except PatchError:pass
        else:raise AssertionError("ACCEPTED_CHANGED_NATIVE_IF_CODE")
    return {"status":"PASS_OFFLINE_SYNTHETIC","checks":7,
        "real_native_compile":"NOT_RUN","full_semantic_parity":False}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--simc-root",type=Path)
    parser.add_argument("--receipt",type=Path)
    args=parser.parse_args()
    value=run(args.simc_root) if args.simc_root else selftest()
    body=(json.dumps(value,sort_keys=True,separators=(",",":"))+"\n").encode()
    if args.receipt:
        args.receipt.parent.mkdir(parents=True,exist_ok=True)
        with args.receipt.open("xb") as f:f.write(body)
    else:print(body.decode(),end="")

if __name__=="__main__":main()
