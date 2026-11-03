-- zRotDummyProbe — isolated lightweight observability diagnostic, NOT a trainer.
-- No combat log access, no protected actions, no secret arithmetic/comparison,
-- no external I/O, no automatic rotation advice, no target identification.
-- Observe only player casts and explicitly non-secret spell API fields.
-- Begin by typing /zrdprobe start; finish with /zrdprobe stop.
--
-- SavedVariables is intentionally only a bounded receipt of *public* values.
-- The user's in-game 12.x client is the sole authority for runtime API access.

local addonName = ...
local frame = CreateFrame("Frame")
local SCHEMA = "ZrotDummySafeSpellObservabilityV1"
local MAX_ROWS = 2400
local MAX_SESSIONS = 5
local MAX_TRACKED = 16
local DEFAULT_IDS = {184367, 23881, 335096, 85288, 335097, 1719, 61304}
local session
local recorderDisabled = false

local function Message(msg)
    if DEFAULT_CHAT_FRAME then
        DEFAULT_CHAT_FRAME:AddMessage("|cff8ad3ff[zRotDummyProbe]|r " .. msg)
    end
end

local function SecretFree(value)
    -- If Blizzard's security checker is unavailable or denies the check,
    -- do NOT inspect or record the underlying value.
    if type(issecretvalue) ~= "function" then return false end
    local ok, result = pcall(issecretvalue, value)
    return ok and result == false
end

local function SafeNow()
    local provider = GetTimePreciseSec or GetTime
    if type(provider) ~= "function" then return nil end
    local ok, value = pcall(provider)
    if not ok or not SecretFree(value) or type(value) ~= "number" then return nil end
    if value < 0 or value > 1000000000 then return nil end
    return value
end

local function ReadField(info, key, expected)
    if info == nil then return "UNKNOWN_NO_INFORMATION", nil end
    local ok, value = pcall(function() return info[key] end)
    if not ok then return "UNKNOWN_ACCESS_RESTRICTED", nil end
    if not SecretFree(value) then return "UNKNOWN_SECRET_OR_UNCHECKABLE", nil end
    if type(value) ~= expected then return "UNKNOWN_FIELD_NOT_AVAILABLE", nil end
    return "OBSERVED", value
end

local function CallSpellAPI(api, id)
    if type(api) ~= "function" then return "UNKNOWN_API_UNAVAILABLE", nil end
    local ok, value = pcall(api, id)
    if not ok then return "UNKNOWN_API_RESTRICTED", nil end
    if not SecretFree(value) then return "UNKNOWN_RETURN_SECRET", nil end
    if value == nil then return "UNKNOWN_NO_INFORMATION", nil end
    -- The object itself is never saved or iterated. Each allowed field
    -- is read under a pcall and checked for secrecy before inspection.
    return "RETURNED", value
end

local function ReadStatus(info, key)
    local status, value = ReadField(info, key, "boolean")
    if status == "OBSERVED" then
        return value and "OBSERVED_TRUE" or "OBSERVED_FALSE"
    end
    return status
end

local function ReadChargeCount(info, key)
    local status, value = ReadField(info, key, "number")
    if status == "OBSERVED" then
        if value >= 0 and value <= 100 and value == math.floor(value) then
            return "OBSERVED", value
        end
        return "UNKNOWN_INVALID_COUNT", nil
    end
    return status, nil
end

local function ReadSpellSnapshot(id)
    local obs = {spell_id = id}
    local cdState, cdInfo = CallSpellAPI(C_Spell and C_Spell.GetSpellCooldown, id)
    if cdState ~= "RETURNED" then
        obs.cooldown_activity = cdState
        obs.cooldown_enabled = cdState
    else
        obs.cooldown_activity = ReadStatus(cdInfo, "isActive")
        obs.cooldown_enabled = ReadStatus(cdInfo, "isEnabled")
    end
    local chargeState, chargeInfo = CallSpellAPI(C_Spell and C_Spell.GetSpellCharges, id)
    if chargeState ~= "RETURNED" then
        obs.charge_activity = chargeState
        obs.current_charges_status = chargeState
        obs.max_charges_status = chargeState
    else
        obs.charge_activity = ReadStatus(chargeInfo, "isActive")
        local currentStatus, currentCount = ReadChargeCount(chargeInfo, "currentCharges")
        local maxStatus, maxCount = ReadChargeCount(chargeInfo, "maxCharges")
        obs.current_charges_status = currentStatus
        obs.max_charges_status = maxStatus
        if currentStatus == "OBSERVED" then obs.current_charges = currentCount end
        if maxStatus == "OBSERVED" then obs.max_charges = maxCount end
    end
    -- Deliberately NEVER access cooldownStartTime, cooldownDuration,
    -- startTime, duration, modRate, chargeModRate or isOnGCD.
    -- No "READY" or "NOT_READY" decision is made here.
    return obs
end

local function Append(row)
    if not session then return false end
    if #session.records >= MAX_ROWS then
        session.stopped_reason = "MAX_ROWS_REACHED"
        session.running = false
        Message("Record limit reached; stopped. No data was inferred.")
        session = nil
        return false
    end
    row.index = #session.records + 1
    session.records[#session.records + 1] = row
    return true
end

local function Snapshot(eventName)
    if not session then return end
    local when = SafeNow()
    if not when then
        Append({kind="SNAPSHOT_UNOBSERVABLE", reason="TIMESTAMP_UNKNOWN",
                trigger=eventName})
        return
    end
    local list = {}
    for _, spellID in ipairs(ZRotDummyProbeDB.tracked) do
        list[#list + 1] = ReadSpellSnapshot(spellID)
    end
    Append({kind="SPELL_OBSERVATION", timestamp=when,
            trigger=eventName, spells=list,
            sampling="EVENT_DRIVEN_NOT_CONTINUOUS",
            gameplay_ready="UNKNOWN"})
end

local function Start()
    if recorderDisabled then Message("Recorder disabled for unsafe saved-data schema."); return end
    if session then Message("Already recording."); return end
    if not ZRotDummyProbeDB or #ZRotDummyProbeDB.sessions >= MAX_SESSIONS then
        Message("Session capacity reached; existing saved data was not removed.")
        return
    end
    local when = SafeNow()
    if not when then
        Message("Timestamp is not safely observable; recording not started.")
        return
    end
    session = {schema=SCHEMA, version=1, started_at=when,
        stopped_at=nil, running=true,
        actor="player", decision_authority="NONE",
        player_error_claims=0,
        events_only="PLAYER_UNIT_CAST_AND_SPELL_UPDATE",
        records={}}
    ZRotDummyProbeDB.sessions[#ZRotDummyProbeDB.sessions + 1] = session
    Snapshot("MANUAL_START_BASELINE")
    Message("Recording player casts and non-secret spell fields only.")
end

local function Stop()
    if not session then Message("No active recording."); return end
    session.stopped_at = SafeNow()
    session.running = false
    session.stopped_reason = "MANUAL_STOP"
    local count = #session.records
    session = nil
    Message("Stopped. " .. count .. " bounded observation records saved locally.")
end

local function AddTracked(text)
    if session then
        Message("Stop before changing tracked spell IDs.")
        return
    end
    local id = tonumber(text)
    if not id or id ~= math.floor(id) or id <= 0 or id > 2000000 then
        Message("Usage: /zrdprobe track <numeric spell ID>")
        return
    end
    for _, old in ipairs(ZRotDummyProbeDB.tracked) do
        if old == id then Message("Already tracked."); return end
    end
    if #ZRotDummyProbeDB.tracked >= MAX_TRACKED then
        Message("Tracked spell limit reached.")
        return
    end
    ZRotDummyProbeDB.tracked[#ZRotDummyProbeDB.tracked + 1] = id
    Message("Added local spell ID " .. id .. ".")
end

local function Stats()
    if not ZRotDummyProbeDB then return end
    Message("Stored sessions: " .. #ZRotDummyProbeDB.sessions ..
        "; tracked IDs: " .. #ZRotDummyProbeDB.tracked ..
        "; active: " .. (session and "yes" or "no"))
end

local function OnSlash(text)
    if recorderDisabled or not ZRotDummyProbeDB then Message("Not initialized or disabled."); return end
    local command, rest = string.match(text or "", "^%s*(%S*)%s*(.-)%s*$")
    command = string.lower(command)
    if command == "start" then Start()
    elseif command == "stop" then Stop()
    elseif command == "track" then AddTracked(rest)
    elseif command == "stats" then Stats()
    else Message("Commands: start | stop | stats | track <numeric spellID>") end
end

SLASH_ZROTDUMMYPROBE1 = "/zrdprobe"
SlashCmdList["ZROTDUMMYPROBE"] = OnSlash

frame:RegisterEvent("ADDON_LOADED")
frame:RegisterEvent("UNIT_SPELLCAST_SUCCEEDED")
frame:RegisterEvent("SPELL_UPDATE_COOLDOWN")
frame:RegisterEvent("SPELL_UPDATE_CHARGES")

frame:SetScript("OnEvent", function(_, event, ...)
    if event == "ADDON_LOADED" then
        local loaded = ...
        if loaded ~= addonName then return end
        if type(ZRotDummyProbeDB) ~= "table" then
            ZRotDummyProbeDB = {schema=SCHEMA, sessions={}, tracked=DEFAULT_IDS}
        end
        if type(ZRotDummyProbeDB.sessions) ~= "table" or
           type(ZRotDummyProbeDB.tracked) ~= "table" then
            -- Refuse to overwrite old or unexpected saved data.
            recorderDisabled = true
            Message("Saved data has unknown schema; existing records preserved; recorder disabled.")
            return
        end
        if ZRotDummyProbeDB.schema ~= SCHEMA then
            recorderDisabled = true
            Message("Saved data schema differs; existing records preserved; recorder disabled.")
        end
        return
    end
    if not session then return end
    if event == "UNIT_SPELLCAST_SUCCEEDED" then
        local unit, _, spellID = ...
        if not SecretFree(unit) or unit ~= "player" then return end
        if not SecretFree(spellID) or type(spellID) ~= "number" then
            Append({kind="CAST_UNOBSERVABLE",
                    reason="SECRET_OR_UNKNOWN_SPELL_ID"})
            return
        end
        if spellID < 1 or spellID > 2000000 or spellID ~= math.floor(spellID) then
            Append({kind="CAST_UNOBSERVABLE",reason="INVALID_NUMERIC_ID"})
            return
        end
        local when = SafeNow()
        if when then
            -- Spell cooldown API is NOT guaranteed updated at this event.
            -- Do not take post-cast cooldown to claim strict PRE readiness.
            Append({kind="PLAYER_CAST_SUCCEEDED",timestamp=when,
                    spell_id=spellID,expected_spell="UNKNOWN",
                    manual_keypress="UNKNOWN",
                    source_readiness_pre="UNKNOWN",
                    verdict="UNKNOWN"})
        else
            Append({kind="CAST_UNOBSERVABLE",reason="TIMESTAMP_UNKNOWN"})
        end
    elseif event == "SPELL_UPDATE_COOLDOWN" or event == "SPELL_UPDATE_CHARGES" then
        Snapshot(event)
    end
end)
