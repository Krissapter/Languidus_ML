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
    #Cities
    "metropolis": {"food": -140, "happiness": 5, "sanitation": -4, "wealth": 600},
    "civitas": {"food": -30, "happiness": 2, "sanitation": -1, "wealth": 300},
    #Towns
    "town": {"food": -80, "happiness": 3, "sanitation": -2, "wealth": 300},
    "colonia": {"food": -20, "happiness": 1, "sanitation": 0, "wealth": 200}
}
#Evaluates the settlement as a sum of the building effects + innate effects
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

print("Wealth? ",  evaluateSettlement("metropolis", [2, 9, 11, 15, 20], 3))

def evaluate(region):

    fertility = region.get("fertility", 0)

    regionStats = [
        evaluateSettlement(s["type"], s["buildings"], fertility)
        for s in region["settlements"]
    ]

    wealth = {"co": 0, "in": 0, "ag": 0, "ah": 0, "cu": 0, "other": 0}
    regional_sanitation = 0
    modifiers = {"co_w": 0, "in_w": 0, "ag_w": 0, "ah_w": 0, "cu_w": 0}

region = {
    "fertility": 2,
    "settlements": [
        {"type": "metropolis", "buildings": [2, 9, 11, 15, 20]},
        {"type": "town", "buildings": [33, 34, 36]},
        {"type": "town", "buildings": [35, 39, 40]}
    ]
}