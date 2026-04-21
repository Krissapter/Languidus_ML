import json
import math

#Defines the base values of each settlement
BASE_STATS = {
    "city": {"food": -140, "happiness": 5, "sanitation": -4, "wealth": 600},
    "town": {"food": -80, "happiness": 3, "sanitation": -2, "wealth": 300},
}

def loadData():
    with open("Buildings_ERE.JSON") as f:
        data = json.load(f)
    with open("Resources_ERE.JSON") as d:
        rsrc = json.load(d)
    return data["buildings"], rsrc["resources"]

buildingList, resourceList = loadData()
#Check the effects of a given building
def getBuildingEffects(building, fertility):
    effects = building.get("effects", {})

    wealthEfx = effects.get("wealth", {})

    #Clean the fertility input for wealth or add a flat wealth
    if isinstance(wealthEfx, dict):
        wealth = {cat: evalExpression(val, fertility) for cat, val in wealthEfx.items()}
    else:
        wealth = {"flat": wealthEfx}

    resourceQTY = effects.get("resource_qty", 0)
    resourceVAL = effects.get("resource_val", 0)

    tradeValue = resourceQTY*resourceVAL
    return {
        "food": evalExpression(effects.get("food", 0), fertility),
        "happiness": effects.get("happiness", 0),
        "sanitation": effects.get("sanitation", 0),
        "sanitation_regional": effects.get("sanitation_regional", 0),
        "wealth": wealth,
        "modifiers": building.get("modifiers", {}),
        "trade_value": tradeValue
    }

#Check for and replace the fertility value
def evalExpression(expr, fertility):
    if isinstance(expr, (int, float)):
        return expr
    return eval(expr, {"fertility": fertility})

def getBuilding(buildList, rscrList, bid, resourceId=0, coast=False):
    for b in buildList:
        if b["id"] == bid:
            reqs= b.get("requires", [])
            if not reqs or (rscrList[resourceId]["resource"] in reqs) or ("coast" in reqs and coast):
                return b
    return buildList[0]
    

#Compiles the settlement as a sum of the building effects + innate effects
def evaluateSettlement(buildList, rscrList, settlementType, buildingIds, fertility, resource, coast):

    base = BASE_STATS[settlementType]

    totals = {
        "food": base["food"],
        "happiness": base["happiness"],
        "sanitation": base["sanitation"],
        "sanitation_regional": 0,
        "wealth": {},
        "modifiers": {},
        "trade_value": 0,  
    }
    #Add stuff together and put it in the dict
    for bid in buildingIds:
        effects = getBuildingEffects(getBuilding(buildList, rscrList, bid, resource, coast), fertility)
        for key in totals:
            if key == "wealth" or key == "modifiers":
                for cat, val in effects[key].items():
                    totals[key][cat] = totals[key].get(cat, 0) + val
            else:
                totals[key] += effects.get(key, 0)
    return totals

#Check if region is within soft constraints 
def checkConstraint(regionData):
    violations = []
    sanitation = regionData["sanitation"]
    j = 0
    if regionData["food"] < 0:
        violations.append(regionData["food"]*-1)
    if regionData["happiness"] < 13:
        violations.append(13-regionData["happiness"])
    for i in sanitation:
        j += 1
        if i < 0:
            violations.append(-i*10)
    return violations

#Scores the region based on the data collected
def scoreRegion(data, violations):
    #Hyperparameters
    foodParam = 200
    happyParam = 50
    religionParam = 100
    relAdjParam = 50
    synParam = 2
    TKPenalityParam = 1000

    food = data["food"]
    happy = data["happiness"]
    wScore = data["wealth"]
    tScore = data["trade_value"]
    synergy = 0

    fScore = round(foodParam*math.sqrt(max(0, food)))

    if happy > 13 and happy <= 18:
        hScore = happy*happyParam
    elif happy > 18:
        hScore = 18*happyParam - (happy-18)*happyParam
    else:
        hScore = 0
    
    rScore = data["modifiers"].get("religion", 0)*religionParam + data["modifiers"].get("religion_adjacent", 0)*relAdjParam
    
    WEALTH_MODIFIERS = {"co_w": "co", "in_w": "in", "ag_w": "ag", "ah_w": "ah", "cu_w": "cu"}
    #Test with and without synergy encouragement
    for mod, val in data["modifiers"].items():
        if mod in WEALTH_MODIFIERS:
            cat = WEALTH_MODIFIERS[mod]
            base = data["base_wealth"].get(cat, 0)
            synergy += round(base*val if val >= 0.3 else (base*val)/synParam)

    penalty = sum(violations)*TKPenalityParam
    
    score = wScore + fScore + hScore + synergy + rScore + tScore- penalty
    return score

def evaluate(region, buildList, rscrList):
    settlementsArr = [region[:5], region[5:8],region[8:11]]
    fertility = region[11]
    coastArr = region[12:15]
    typeArr = ["city", "town", "town"]
    resourceArr = region[18:21]

    regionStats = [
        evaluateSettlement(buildList, rscrList, typeArr[i], settlementsArr[i], fertility, resourceArr[i], coastArr[i])
        for i in range(3)
    ]
    #local sanitation
    locSan = []
    regionalSan = sum(s["sanitation_regional"] for s in regionStats)
    for s in regionStats:
        locSan.append(s["sanitation"] + regionalSan) 

    regFood = 0
    regHappy = 0
    regReligion = 0
    regWealth = {}
    regModifiers = {}
    totalTradeWealth = sum(s["trade_value"] for s in regionStats)
    #Get wealth and modifiers
    for s in regionStats:
        for cat, val in s["wealth"].items():
            regWealth[cat] = regWealth.get(cat, 0) + val
        for mod, val in s["modifiers"].items():
            regModifiers[mod] = regModifiers.get(mod, 0) + val
        #Get other relevant data
        regFood += s["food"]
        regHappy += s["happiness"]
        regReligion = regModifiers.get("religion", 0)
    
    baseWealth = regWealth.copy()
    #Apply wealth modifiers if applicable
    for mod, val in regModifiers.items():
        match mod:
            case "co_w":
                regWealth["co"] = round(regWealth.get("co", 0)*(1 + val))
            case "in_w":
                regWealth["in"] = round(regWealth.get("in", 0)*(1 + val))
            case "ag_w":
                regWealth["ag"] = round(regWealth.get("ag", 0)*(1 + val))
            case "ah_w":
                regWealth["ah"] = round(regWealth.get("ah", 0)*(1 + val))
            case "cu_w":
                regWealth["cu"] = round(regWealth.get("cu", 0)*(1 + val))
    totalWealth = sum(regWealth.get(cat, 0) for cat in ["co", "in", "ag", "ah", "cu", "flat"])

    constraintData = {
        "food": regFood,
        "happiness": regHappy,
        "sanitation": locSan
    }
    violations = checkConstraint(constraintData)
    regionData = {
        "food": regFood,
        "happiness": regHappy,
        "wealth": totalWealth,
        "base_wealth": baseWealth,
        "modifiers": regModifiers,
        "trade_value": totalTradeWealth,
        "religion": regReligion
    }

    return scoreRegion(regionData, violations), {
        "settlement_sanitation": locSan,
        "region": {
            "food": regFood,
            "happiness": regHappy,
            "wealth": totalWealth,
            "modifiers": regModifiers,
            "trade_value": totalTradeWealth,
            "religion": regReligion
        }
    }
#[0-4] City buildings, [5-7] Town 1 buildings, [8-10] Town 2 buildings, [11] Fertility, [12-14] Coastal Bools, [15-17] Has Resource Bool, [18-20] Resource IDs
# Example regArray = [12, 3, 9, 5, 6, 19, 20, 21, 22, 24, 19, 3, 0, 0, 0, 0, 0, 0, 0, 0, 0]
#regArray = [1, 3, 12, 6, 17, 19, 23, 24, 20, 21, 22, 3, 0, 0, 0, 1, 0, 0, 3, 0, 0]
#regArray_adj = [2, 3, 12, 6, 17, 19, 23, 24, 20, 21, 22, 3, 0, 0, 0, 1, 0, 0, 3, 0, 0]
#regArray_penalty = [13, 14, 5, 7, 0, 25, 26, 19, 25, 26, 20, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0]
#evaluate(regArray_penalty, buildingList, resourceList)