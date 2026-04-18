import json
import math

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

#Defines the base values of each settlement
BASE_STATS = {
    "city": {"food": -140, "happiness": 5, "sanitation": -4, "wealth": 600},
    "town": {"food": -80, "happiness": 3, "sanitation": -2, "wealth": 300},
}

#Compiles the settlement as a sum of the building effects + innate effects
def evaluateSettlement(settlementType, buildingIds, fertility):
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
        effects = getBuildingEffects(buildingList[bid], fertility)
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
        violations.append("Regional food deficit")
    if regionData["happiness"] < 13:
        violations.append("Regional happiness too low")
    for i in sanitation:
        j += 1
        if i < 0:
            #1 = city, 2 & 3 = towns
            violations.append(f"Settlement {j} sanitation deficit")
    return violations

def scoreRegion(data, violations):

    food = data["food"]
    happy = data["happiness"]
    wealth = int(data["wealth"])

    fScore = int(200*math.sqrt(max(0, food)))

    if happy > 13 and happy <= 18:
        hScore = happy*50
    elif happy > 18:
        hScore = 18*50 - (happy-18)*50
    else:
        hScore = 0
    
    for mod, val in data["modifiers"].items():
        match mod:
            case "co_w":
                data["base_wealth"]["co"] = data["base_wealth"].get("co", 0)*val
            case "in_w":
                data["base_wealth"]["in"] = data["base_wealth"].get("in", 0)*val
            case "ag_w":
                data["base_wealth"]["ag"] = data["base_wealth"].get("ag", 0)*val
            case "ah_w":
                data["base_wealth"]["ah"] = data["base_wealth"].get("ah", 0)*val
            case "cu_w":
                data["base_wealth"]["cu"] = data["base_wealth"].get("cu", 0)*val
    penalty = len(violations)*10000

    print(fScore, hScore, wealth, "\n")
    score = wealth + fScore + hScore - penalty
    return score

def evaluate(region):

    fertility = region.get("fertility", 0)

    regionStats = [
        evaluateSettlement(s["type"], s["buildings"], fertility)
        for s in region["settlements"]
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
        baseWealth = regWealth

    #Apply wealth modifiers if applicable
    for mod, val in regModifiers.items():
        match mod:
            case "co_w":
                regWealth["co"] = regWealth.get("co", 0)*(1 + val)
            case "in_w":
                regWealth["in"] = regWealth.get("in", 0)*(1 + val)
            case "ag_w":
                regWealth["ag"] = regWealth.get("ag", 0)*(1 + val)
            case "ah_w":
                regWealth["ah"] = regWealth.get("ah", 0)*(1 + val)
            case "cu_w":
                regWealth["cu"] = regWealth.get("cu", 0)*(1 + val)
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
        "modifiers": regModifiers
    }
    print(scoreRegion(regionData, violations))
    
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
    "fertility": 2,
    "settlements": [
        {"type": "city", "buildings": [2, 9, 11, 15, 20]},
        {"type": "town", "buildings": [33, 34, 36]},
        {"type": "town", "buildings": [35, 39, 40]}
    ]
}

print(evaluate(region))