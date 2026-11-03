#!/usr/bin/env python3
"""Read-only pinned SimulationCraft native select_action() branch instrumentation.

This *reporter-only* instrument is for native source verification, not a
replacement SimC algorithm. It records each actual foreground CALL recursion
and action_ready result with source signature-pointer APL ownership. A
run_action_list action is reported as an ordinary selected action, and only
its own execute() changes the active action list later.

Only the exact official upstream source identity is accepted. No WCL input.
PyCharm/default entry point runs synthetic patch contract tests.
"""
from __future__ import annotations
import argparse,hashlib,json,re,subprocess
from pathlib import Path

SIMC_COMMIT="b522cded8c26b97dac03fdf56e57a03ec7e8faa6"
PLAYER_CPP_BLOB="88e03a01ca87ff66fd3902c9d6e047fe1a03ecb8"
RELATIVE=Path("engine/player/player.cpp")
START="action_t* player_t::select_action( const action_priority_list_t& list,"
END="\nplayer_t* player_t::actor_by_name_str"
MARK="ZROT_NATIVE_SELECT_V1|"
HEADER="""  // zRotationHelper source-only selection provenance.
  // No RNG changes or manual readiness lookups; each action_ready() is called
  // exactly once, as in the official original.
  if ( sim->log && !is_pet() && !is_enemy() )
    sim->print_log( "ZROT_NATIVE_SELECT_V1|ENTER|{}|{}|{}",
      sim->current_time().total_millis(), list.name_str,
      et == execute_type::FOREGROUND ? "FOREGROUND" :
      et == execute_type::OFF_GCD ? "OFF_GCD" : "CAST_WHILE_CASTING" );

"""
CHECK="""    // Capture the return of the SAME native readiness call; never call twice.
    bool zrot_native_ready = a->action_ready();
    if ( sim->log && !is_pet() && !is_enemy() )
    {
      unsigned zrot_apl_ordinal = 0;
      std::string zrot_apl_owner = "UNKNOWN";
      if ( a->action_list && a->signature )
      {
        const auto& zrot_owner_list = *a->action_list;
        for ( std::size_t zrot_idx = 0; zrot_idx < zrot_owner_list.action_list.size(); ++zrot_idx )
        {
          if ( &( zrot_owner_list.action_list[ zrot_idx ] ) == a->signature )
          {
            zrot_apl_owner = zrot_owner_list.name_str;
            zrot_apl_ordinal = static_cast<unsigned>( zrot_idx + 1 );
            break;
          }
        }
      }
      sim->print_log( "ZROT_NATIVE_SELECT_V1|ATTEMPT|{}|{}|{}|{}|{}|{}",
        sim->current_time().total_millis(), list.name_str, zrot_apl_owner,
        zrot_apl_ordinal, a->name_str, zrot_native_ready ? 1 : 0 );
    }
    if ( zrot_native_ready )"""
CALL_RETURN="""          if ( sim->log && !is_pet() && !is_enemy() )
            sim->print_log( "ZROT_NATIVE_SELECT_V1|RETURN|{}|{}|{}|CALL_RECURSION",
              sim->current_time().total_millis(), list.name_str, real_a->name_str );
          return real_a;"""
DIRECT_RETURN="""        if ( sim->log && !is_pet() && !is_enemy() )
          sim->print_log( "ZROT_NATIVE_SELECT_V1|RETURN|{}|{}|{}|DIRECT",
            sim->current_time().total_millis(), list.name_str, a->name_str );
        return a;"""
NULL_EXIT="""  if ( sim->log && !is_pet() && !is_enemy() )
    sim->print_log( "ZROT_NATIVE_SELECT_V1|NO_ACTION|{}|{}",
      sim->current_time().total_millis(), list.name_str );
  return nullptr;"""

class PinError(ValueError):pass

def git_blob(raw):
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

def sha(raw):return hashlib.sha256(raw).hexdigest()

def replace_exact(x,needle,repl,expected=1):
    n=x.count(needle)
    if n!=expected:raise PinError("NATIVE_SELECT_ANCHOR_MISMATCH:"+str(n))
    return x.replace(needle,repl)

def instrument(original:bytes,*,enforce_pin=True)->bytes:
    if enforce_pin and git_blob(original)!=PLAYER_CPP_BLOB:
        raise PinError("PINNED_NATIVE_PLAYER_CPP_CHANGED")
    source=original.decode("utf-8")
    if MARK in source:raise PinError("ALREADY_INSTRUMENTED")
    if source.count(START)!=1 or source.count(END)!=1:
        raise PinError("NATIVE_SELECT_FUNCTION_BOUNDARIES_CHANGED")
    begin=source.index(START);end=source.index(END,begin)
    body=source[begin:end]
    # The C++ compiler and exact source anchor contract decide semantics,
    # not a regular expression guessed from log messages or action names.
    prefix="""  // Mark this action list as visited with the APL internal id"""
    body=replace_exact(body,prefix,HEADER+prefix)
    body=replace_exact(body,"    if ( a->action_ready() )",CHECK)
    body=replace_exact(body,"          return real_a;",CALL_RETURN)
    body=replace_exact(body,"        return a;",DIRECT_RETURN)
    body=replace_exact(body,"  return nullptr;\n}",NULL_EXIT+"\n}")
    modified=source[:begin]+body+source[end:]
    if modified.count(MARK)!=5:
        raise PinError("READ_ONLY_NATIVE_MARK_COUNT_CHANGED")
    if modified.count("zrot_native_ready = a->action_ready();")!=1:
        raise PinError("NATIVE_READINESS_WAS_REEVALUATED")
    return modified.encode("utf-8")

def instrument_tree(root:Path):
    root=root.resolve(strict=True)
    git=subprocess.run(["git","-C",str(root),"rev-parse","HEAD"],
        check=True,capture_output=True,text=True).stdout.strip()
    if git!=SIMC_COMMIT:raise PinError("PINNED_SIMC_COMMIT_CHANGED")
    target=root/RELATIVE
    if not target.is_file():raise PinError("NATIVE_PLAYER_CPP_NOT_FOUND")
    original=target.read_bytes()
    revised=instrument(original)
    target.write_bytes(revised)
    return {"schema":"ZrotNativeSelectReporterPatchReceiptV1",
            "simc_commit":SIMC_COMMIT,"original_player_cpp_blob":PLAYER_CPP_BLOB,
            "original_player_cpp_sha256":sha(original),
            "instrumented_player_cpp_sha256":sha(revised),
            "source_marker":MARK,
            "source_action_ready_evaluations_per_visited_row":1,
            "native_action_behavior_modified":False,
            "actual_compiled_and_executed":False}

def selftest():
    example=(START+"\n{\n"
      "  // Mark this action list as visited with the APL internal id\n"
      "  if ( a->action_ready() )\n"
      "          return real_a;\n"
      "        return a;\n"
      "  return nullptr;\n}\n"+END+"\n{}\n").encode()
    patched=instrument(example,enforce_pin=False).decode()
    assert patched.count(MARK)==5
    assert "if ( zrot_native_ready )" in patched
    assert patched.count("= a->action_ready();")==1
    assert "if ( a->action_ready() )" not in patched
    assert patched.index("CALL_RECURSION")<patched.index("DIRECT")
    assert "a->signature" in patched
    for invalid in (example.replace(b"return real_a;",b"return nullptr;"),
                    example.replace(b"if ( a->action_ready() )",b"if ( a->ready() )")):
        try:instrument(invalid,enforce_pin=False)
        except PinError:pass
        else:raise AssertionError("INCOMPATIBLE_NATIVE_SOURCE_WAS_ACCEPTED")
    return {"status":"PASS_OFFLINE_SYNTHETIC","checks":8,
            "native_execution":"NOT_RUN","WCL_API_calls":0,
            "false_priority_claims":0}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--simc-root",type=Path)
    p.add_argument("--receipt",type=Path)
    a=p.parse_args()
    if a.simc_root is None:result=selftest()
    else:result=instrument_tree(a.simc_root)
    blob=(json.dumps(result,sort_keys=True,separators=(",",":"))+"\n").encode()
    if a.receipt:
        a.receipt.parent.mkdir(parents=True,exist_ok=True)
        with a.receipt.open("xb") as f:f.write(blob)
    else:print(blob.decode(),end="")

if __name__=="__main__":main()
