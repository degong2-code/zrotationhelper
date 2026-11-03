-- Standalone Lua 5.4 mock-client regression for RESEARCH-only addon.
-- This test checks local source logic; it is NOT a real Blizzard API test.
local SECRET = {}
local clock = 10.0
local frame

DEFAULT_CHAT_FRAME = {AddMessage=function(_, _) end}
SlashCmdList = {}
function CreateFrame(kind)
    assert(kind == "Frame")
    frame = {events={}}
    function frame:RegisterEvent(name) self.events[name] = true end
    function frame:SetScript(name,cb)
        assert(name == "OnEvent")
        self.onEvent = cb
    end
    return frame
end
function issecretvalue(v) return v == SECRET end
function GetTimePreciseSec() return clock end

C_Spell = {
    GetSpellCooldown = function(id)
        if id == 335097 then
            return {isActive=true,isEnabled=true,startTime=SECRET,duration=SECRET}
        elseif id == 23881 then
            return SECRET
        end
        return {isActive=false,isEnabled=true}
    end,
    GetSpellCharges = function(id)
        if id == 335097 then
            return {currentCharges=SECRET,maxCharges=2,isActive=true,
                    cooldownStartTime=SECRET,cooldownDuration=SECRET}
        end
        return nil
    end
}

assert(loadfile("addons/research/ZRotDummyProbe/ZRotDummyProbe.lua"))("ZRotDummyProbe")
assert(frame.events["ADDON_LOADED"])
assert(frame.events["UNIT_SPELLCAST_SUCCEEDED"])
assert(frame.events["SPELL_UPDATE_COOLDOWN"])
assert(frame.events["SPELL_UPDATE_CHARGES"])

frame.onEvent(frame,"ADDON_LOADED","OtherAddon")
assert(ZRotDummyProbeDB == nil)
frame.onEvent(frame,"ADDON_LOADED","ZRotDummyProbe")
assert(ZRotDummyProbeDB.schema == "ZrotDummySafeSpellObservabilityV1")
assert(#ZRotDummyProbeDB.tracked == 7)

SlashCmdList.ZROTDUMMYPROBE("start")
assert(#ZRotDummyProbeDB.sessions == 1)
local sample = ZRotDummyProbeDB.sessions[1]
assert(sample.running)
assert(sample.player_error_claims == 0)
assert(sample.records[1].kind == "SPELL_OBSERVATION")
assert(sample.records[1].timestamp == 10.0)
local function spellAt(record,id)
    for _, entry in ipairs(record.spells) do
        if entry.spell_id == id then return entry end
    end
    error("missing spell "..id)
end

local before = spellAt(sample.records[1],335097)
assert(before.cooldown_activity == "OBSERVED_TRUE")
assert(before.cooldown_enabled == "OBSERVED_TRUE")
assert(before.current_charges_status == "UNKNOWN_SECRET_OR_UNCHECKABLE")
assert(before.current_charges == nil)
assert(before.max_charges_status == "OBSERVED")
assert(before.max_charges == 2)
assert(before.charge_activity == "OBSERVED_TRUE")
assert(before.startTime == nil and before.duration == nil)
assert(before.cooldownStartTime == nil and before.cooldownDuration == nil)

local inaccessible = spellAt(sample.records[1],23881)
assert(inaccessible.cooldown_activity == "UNKNOWN_RETURN_SECRET")

clock = 11.0
frame.onEvent(frame,"UNIT_SPELLCAST_SUCCEEDED","player","cast-001",335097,2)
assert(sample.records[2].kind == "PLAYER_CAST_SUCCEEDED")
assert(sample.records[2].spell_id == 335097)
assert(sample.records[2].timestamp == 11)
assert(sample.records[2].source_readiness_pre == "UNKNOWN")
assert(sample.records[2].verdict == "UNKNOWN")
assert(sample.records[2].spells == nil)

clock = 12.0
frame.onEvent(frame,"SPELL_UPDATE_COOLDOWN",335097)
assert(sample.records[3].kind == "SPELL_OBSERVATION")
assert(sample.records[3].timestamp == 12.0)
assert(sample.records[3].trigger == "SPELL_UPDATE_COOLDOWN")

clock = 13.0
frame.onEvent(frame,"UNIT_SPELLCAST_SUCCEEDED","player","cast-secret",SECRET,2)
assert(sample.records[4].kind == "CAST_UNOBSERVABLE")
assert(sample.records[4].spell_id == nil)

clock = 14.0
frame.onEvent(frame,"UNIT_SPELLCAST_SUCCEEDED","target","cast-target",335097,2)
assert(#sample.records == 4)

clock = 15.0
frame.onEvent(frame,"SPELL_UPDATE_CHARGES")
assert(sample.records[5].trigger == "SPELL_UPDATE_CHARGES")

local function CheckNoSecrets(obj,seen)
    if obj == SECRET then error("Secret value leaked into SavedVariables") end
    if type(obj) ~= "table" then return end
    seen = seen or {}
    if seen[obj] then return end
    seen[obj] = true
    for key,value in pairs(obj) do
        assert(key ~= "startTime" and key ~= "duration" and
               key ~= "cooldownStartTime" and key ~= "cooldownDuration")
        CheckNoSecrets(key,seen)
        CheckNoSecrets(value,seen)
    end
end
CheckNoSecrets(ZRotDummyProbeDB)

SlashCmdList.ZROTDUMMYPROBE("stop")
assert(sample.running == false)
assert(sample.stopped_reason == "MANUAL_STOP")
assert(sample.stopped_at == 15.0)
assert(#sample.records == 5)
assert(ZRotDummyProbeDB.sessions[1] == sample)
SlashCmdList.ZROTDUMMYPROBE("track 123456")
assert(#ZRotDummyProbeDB.tracked == 8)
print("MOCK_WOW_12X_ADDON_SECRET_SAFE_RECORDER_PASS")
print("RECORDED_ROWS="..#sample.records)
