#!/usr/bin/env python3
"""Reusable, specialization-neutral original SimC PRE field transport.

Generic code only: typed field requests -> source-PRE C++ field readers,
paired source-identity marker parsing, and fail-closed transport validation.
Source-backed specialization constraints and real log/condition auditing
belong to adapter fixtures, NOT to this producer. Explicit provenance
still required before positive/negative readiness in a GateContract.

This version specializes only two *reader families*: equipped weapon slot
and named actor buff stack. The field names and buff names are parameters;
no action/class/hero tree or raid/encounter logic exists here.
"""
from __future__ import annotations

from dataclasses import dataclass
import re
from simc_native_select_trace_instrument_v1 import instrument as patch_native_source

MARK="ZROT_GR_FIELD_CAPTURE_PRE_V1|"
ATTEMPT="ZROT_NATIVE_SELECT_V1|ATTEMPT|"
ORIGINAL_CALL="    bool zrot_native_ready = a->action_ready();"
FIELD_KEY=re.compile(r"^[a-z][a-z0-9_.]{1,127}$")
BUFF_NAME=re.compile(r"^[a-z][a-z0-9_]{0,63}$")
READERS=frozenset(("actor_weapon_slot_equipped","actor_named_buff_active"))
SLOTS=frozenset(("main_hand","off_hand"))

class FieldCaptureError(ValueError):
    pass


def require(value:bool,code:str)->None:
    if not value:raise FieldCaptureError(code)


@dataclass(frozen=True)
class FieldRequest:
    key:str
    reader:str
    argument:str

    def __post_init__(self):
        require(FIELD_KEY.fullmatch(self.key) is not None and
                self.reader in READERS,"FIELD_REQUEST_KEY_OR_READER_INVALID")
        if self.reader=="actor_weapon_slot_equipped":
            require(self.argument in SLOTS,
                    "UNDECLARED_OR_UNSAFE_WEAPON_SLOT_ACCESSOR")
        else:
            require(BUFF_NAME.fullmatch(self.argument) is not None,
                    "UNSAFE_OR_EMPTY_BUFF_NAME")


def field_requests(fields:list[dict]|tuple[FieldRequest,...])->tuple[FieldRequest,...]:
    items=[x if isinstance(x,FieldRequest) else
           FieldRequest(**x) for x in fields]
    require(0<len(items)<=12 and
            len({x.key for x in items})==len(items),
            "EMPTY_OR_DUPLICATE_CAPTURE_FIELD_REQUESTS")
    return tuple(items)


def cpp_code(field:FieldRequest,index:int)->str:
    name="zrot_gr_raw_"+str(index)
    if field.reader=="actor_weapon_slot_equipped":
        return ("      const int "+name+" = a->player->"+
                field.argument+"_weapon.type == WEAPON_NONE ? 0 : 1;\n")
    require(field.reader=="actor_named_buff_active",
            "CXX_READER_NOT_REVIEWED")
    buff="zrot_gr_buff_"+str(index)
    # Actual buff_t::check() returns current_stack and is side-effect-free
    # in the pinned buff.hpp. Missing buffs/fallbacks emit -1 => UNKNOWN.
    return ("      const buff_t* "+buff+
            " = buff_t::find( a->player, \""+field.argument+"\" );\n"+
            "      const int "+name+" = ("+buff+" && "+buff+
            " != a->player->sim->auras.fallback) ? ("+buff+
            "->check() > 0 ? 1 : 0) : -1;\n")


def extend_pristine_player(raw:bytes,fields:tuple[FieldRequest,...])->bytes:
    patched=patch_native_source(raw,enforce_pin=False).decode("utf-8")
    require(patched.count(ORIGINAL_CALL)==1 and MARK not in patched,
            "SOURCE_SELECT_ORIGINAL_READY_BOUNDARY_NOT_UNIQUE")
    # All paths, including Mage, rely on original action signature owner;
    # no action-name switch or spec branch in this C++.
    code=[
        "    // Source-backed typed PRE fields only; one original readiness call.\n",
        "    if ( sim->log && !is_pet() && !is_enemy() )\n",
        "    {\n",
        '      std::string zrot_gr_owner = "UNKNOWN";\n',
        "      unsigned zrot_gr_ordinal = 0;\n",
        "      if ( a->action_list && a->signature )\n",
        "      {\n",
        "        const auto& zrot_gr_list = *a->action_list;\n",
        "        for ( std::size_t zrot_gr_i = 0; zrot_gr_i < zrot_gr_list.action_list.size(); ++zrot_gr_i )\n",
        "          if ( &( zrot_gr_list.action_list[ zrot_gr_i ] ) == a->signature )\n",
        "          {\n",
        "            zrot_gr_owner = zrot_gr_list.name_str;\n",
        "            zrot_gr_ordinal = static_cast<unsigned>( zrot_gr_i + 1 );\n",
        "            break;\n",
        "          }\n",
        "      }\n",
    ]
    for i,f in enumerate(fields):
        code.append(cpp_code(f,i))
    placeholders="|{}".join([""]+[""]*(3+len(fields)))
    marker=MARK+placeholders.lstrip("|")
    # 4 + N fmt arguments: time, list, ordinal, action, field values.
    fmt=MARK+"|".join(["{}"]*(4+len(fields)))
    code.extend([
        '      sim->print_log( "'+fmt+'",\n',
        "        sim->current_time().total_millis(), zrot_gr_owner,\n",
        "        zrot_gr_ordinal, a->name_str, "+
        ", ".join("zrot_gr_raw_"+str(i) for i in range(len(fields)))+
        " );\n",
        "    }\n",
    ])
    modified=patched.replace(ORIGINAL_CALL,"".join(code)+ORIGINAL_CALL,1)
    original_calls=patched.count("a->action_ready()")
    require(modified.count("a->action_ready()")==original_calls and
            modified.count("if ( zrot_native_ready )")==1 and
            modified.count(MARK)==1 and
            modified.index(MARK)<modified.index(ORIGINAL_CALL) and
            modified.count("buff_t::find(")==(
                patched.count("buff_t::find(")+sum(
                    f.reader=="actor_named_buff_active" for f in fields)),
            "CXX_ORIGINAL_READINESS_CALL_OR_MARKER_CHANGED")
    return modified.encode("utf-8")


def parse_marker(line:str, fields:tuple[FieldRequest,...]):
    at=line.find(MARK)
    if at<0:return None
    parts=line[at:].strip().split("|")
    require(len(parts)==5+len(fields),
            "SOURCE_CAPTURE_MARKER_FIELD_COUNT_DRIFT")
    try:
        t=int(parts[1]);ordinal=int(parts[3])
        values=[int(x) for x in parts[5:]]
    except ValueError as e:
        raise FieldCaptureError("SOURCE_CAPTURE_NONNUMERIC_FIELD") from e
    require(t>=0 and ordinal>=0 and parts[2] and parts[4] and
            all(x in (-1,0,1) for x in values),
            "SOURCE_CAPTURE_PRE_VALUES_INVALID")
    return {"time_ms":t,"source_list":parts[2],
            "ordinal_1based":ordinal,"native_action_name":parts[4],
            "values":values}


def parse_attempt(line:str):
    idx=line.find(ATTEMPT)
    if idx<0:return None
    p=line[idx:].strip().split("|")
    # ZROT_NATIVE_SELECT_V1|ATTEMPT|t|active_list|owner|ordinal|action|return
    # Original return remains a comparator only; not a READY gate.
    require(len(p)==8 and p[2].isdigit() and p[5].isdigit() and
            p[7] in ("0","1"),
            "SOURCE_ORIGINAL_NATIVE_ATTEMPT_FORMAT_CHANGED")
    return {"time_ms":int(p[2]),"source_list":p[4],
            "ordinal_1based":int(p[5]),"native_action_name":p[6]}


def selftest()->dict:
    from simc_native_select_trace_instrument_v1 import START,END
    mock=(START+"\n{\n"
          "  // Mark this action list as visited with the APL internal id\n"
          "    if ( a->action_ready() )\n"
          "          return real_a;\n"
          "        return a;\n"
          "  return nullptr;\n}\n"+END+"\n{}\n").encode()
    requests=field_requests([
        {"key":"equipment.slot_a.equipped",
         "reader":"actor_weapon_slot_equipped","argument":"main_hand"},
        {"key":"buff.unrelated_test.active",
         "reader":"actor_named_buff_active","argument":"unrelated_test"}])
    patched=extend_pristine_player(mock,requests).decode()
    require(patched.count("a->action_ready()")==1 and
            patched.index(MARK)<patched.index(ORIGINAL_CALL) and
            "main_hand_weapon.type == WEAPON_NONE" in patched and
            'buff_t::find( a->player, "unrelated_test" )' in patched,
            "GENERIC_CPP_TRANSPORT_OR_FIELD_READER_DRIFT")
    row=parse_marker(MARK+"20|secondary|3|opaque|1|-1",requests)
    require(row["time_ms"]==20 and row["ordinal_1based"]==3 and
            row["values"]==[1,-1],
            "GENERIC_RAW_FIELD_TRANSPORT_REJECTED_VALID_UNKNOWN")
    attempt=parse_attempt(
        "ZROT_NATIVE_SELECT_V1|ATTEMPT|20|primary|secondary|3|opaque|1")
    require(attempt["time_ms"]==20 and
            attempt["source_list"]=="secondary" and
            attempt["ordinal_1based"]==3,
            "ORIGINAL_SOURCE_SELECTION_IDENTITY_CHANGED")
    for bad in (
        {"key":"bad","reader":"actor_named_buff_active",
         "argument":"x; action_ready()"},
        {"key":"equipment.x","reader":"actor_weapon_slot_equipped",
         "argument":"left"},
        {"key":"buff.x","reader":"python_expression","argument":"1"},
    ):
        try:field_requests([bad])
        except FieldCaptureError:pass
        else:raise AssertionError("UNTRUSTED_SOURCE_READ_ACCEPTED")
    for bad in (
        MARK+"20|secondary|3|opaque|1|2",
        MARK+"20|secondary|3|opaque|1",
    ):
        try:parse_marker(bad,requests)
        except FieldCaptureError:pass
        else:raise AssertionError("UNTRUSTED_FIELD_MARKER_ACCEPTED")
    return {"schema":"ZrotGenericOriginalSimcPREFieldTransportV1",
            "status":"PASS_OFFLINE_SYNTHETIC","checks":11,
            "spec_and_ability_agnostic":True,
            "native_cpp_executed":False,"WCL_API_calls":0,
            "full_READY":0}


if __name__=="__main__":
    import json
    print(json.dumps(selftest(),sort_keys=True))
