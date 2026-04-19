import json
import math

#Defines the base values of each settlement
BASE_STATS = {
    "city": {"food": -140, "happiness": 5, "sanitation": -4, "wealth": 600},
    "town": {"food": -80, "happiness": 3, "sanitation": -2, "wealth": 300},
}

def loadBuildings():
    with open("Buildings_ERE.JSON") as f:
        data = json.load(f)
    return data["buildings"]

buildingList = loadBuildings()

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

def getBuilding(bid, resource=None):
    for b in buildingList:
        if b["id"] == bid:
            reqs= b.get("requires", [])
            if not reqs or resource in reqs:
                return b
    return buildingList[0]
    

#Compiles the settlement as a sum of the building effects + innate effects
def evaluateSettlement(buildingIds, fertility, resource):
    
    totals = {
        "food": 0,
        "happiness": 0,
        "sanitation": 0,
        "sanitation_regional": 0,
        "wealth": {},
        "modifiers": {},
        "trade_value": 0,  
    }
    #Add stuff together and put it in the dict
    for bid in buildingIds:
        effects = getBuildingEffects(getBuilding(bid, resource), fertility)
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
            violations.append(i)
    return violations

#Scores the region based on the data collected
def scoreRegion(data, violations):
    #Hyperparameters
    foodParam = 200
    happyParam = 50
    religionParam = 100
    relAdjParam = 50
    synParam = 2
    TKPenalityParam = 10000

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
    print(data["modifiers"], "\n", f"Wealth: {wScore}\n Food: {fScore}\n Happiness: {hScore}\n Synergy: {synergy}\n Religion: {rScore}\n Trade: {tScore}\n Penalty: {penalty}")

    score = wScore + fScore + hScore + synergy + rScore + tScore- penalty
    return score

def evaluate(region):

    fertility = region.get("fertility", 0)  

    regionStats = [
        evaluateSettlement(s["buildings"], fertility, s.get("resource", 0))
        for s in region["settlements"]
    ]
    #local sanitation
    locSan = [BASE_STATS["city"]["sanitation"], BASE_STATS["town"]["sanitation"], BASE_STATS["town"]["sanitation"]]
    regionalSan = sum(s["sanitation_regional"] for s in regionStats)
    for i, s in enumerate(regionStats):
        locSan[i] += (s["sanitation"] + regionalSan)

    regFood = BASE_STATS["city"]["food"] + BASE_STATS["town"]["food"] + BASE_STATS["town"]["food"]
    regHappy = BASE_STATS["city"]["happiness"] + BASE_STATS["town"]["happiness"] + BASE_STATS["town"]["happiness"]
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
    print(" Final Score:",scoreRegion(regionData, violations))
    
    return {
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

region = {
    "fertility": 3,
    "settlements": [
        {"type": "city", "buildings": [12, 3, 9, 5, 6]},
        {"type": "town", "buildings": [19, 20, 21]},
        {"type": "town", "buildings": [22, 24, 19]}
    ]
}

evaluate(region)