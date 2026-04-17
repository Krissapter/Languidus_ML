import json

def loadBuildings():
    with open("Buildings_ERE.JSON") as f:
        data = json.load(f)
    return data["buildings"]

buildingList = loadBuildings()

#Check the effects of a given building
def getBuildingEffects(building, fertility):
    effects = building.get("effects", {})

    wealthEfx = effects.get("wealth", {})

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
    for bid in buildingIds:
        effects = getBuildingEffects(buildingList[bid], fertility)
        for key in totals:
            if key == "wealth" or key == "modifiers":
                for cat, val in effects[key].items():
                    totals[key][cat] = totals[key].get(cat, 0) + val
            else:
                totals[key] += effects.get(key, 0)
    return totals

#print("Wealth? ",  evaluateSettlement("metropolis", [2, 9, 11, 15, 20], 3))

def evaluate(region):

    fertility = region.get("fertility", 0)

    regionStats = [
        evaluateSettlement(s["type"], s["buildings"], fertility)
        for s in region["settlements"]
    ]
    
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

    totalTradeWealth = totalTradeWealth * (1 + regModifiers.get("tariff_wealth", 0))
        
    for s in regionStats:
        for cat, val in s["wealth"].items():
            regWealth[cat] = regWealth.get(cat, 0) + val
        for mod, val in s["modifiers"].items():
            regModifiers[mod] = regModifiers.get(mod, 0) + val
        regFood += s["food"]
        regHappy += s["happiness"]
        regReligion = regModifiers.get("religion", 0)

    for mod, val in regModifiers.items():
        match mod:
            case "co_w":
                regWealth["co"] = regWealth.get("co", 0) * (1 + val)
            case "in_w":
                regWealth["co"] = regWealth.get("co", 0) * (1 + val)
            case "ag_w":
                regWealth["co"] = regWealth.get("co", 0) * (1 + val)
            case "ah_w":
                regWealth["co"] = regWealth.get("co", 0) * (1 + val)
            case "cu_w":
                regWealth["co"] = regWealth.get("co", 0) * (1 + val)
    totalWealth = sum(regWealth.get(cat, 0) for cat in ["co", "in", "ag", "ah", "cu", "flat"])

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