import gymnasium as gym
import numpy as np
from LanguidusEvaluation import evaluate, getBuilding
from Toolbox import NUM_SLOTS, NUM_BUILDING_ID,CONTEXT_START, CONTEXT_END, SLOT_GROUPS, buildLoader, rsrcLoader, parseContext, regionLoader



class LanguidusEnv(gym.Env):
    def __init__(self, buildings, resources, regionContexts):
        super().__init__()
        self.buildings = buildings #list of buildings
        self.resources = resources
        self.regionContexts = regionContexts
        self.regionContext = None #Fertility, coastline & resources
        self.slots = [0] * NUM_SLOTS #The funny input vector array
        self.currentStats = None
        self.stage = 0

        self.observation_space = gym.spaces.Box(
            low=-np.inf, high=np.inf, shape=(27,), dtype=np.float32
        )
        self.action_space = gym.spaces.Discrete(
            NUM_SLOTS* #building slots
            NUM_BUILDING_ID #building IDs
        )

    def getObs(self):
            context = parseContext(self.regionContext)
            base = self.slots + [context["fertility"]] + context["coast"] + context["hasResource"] + context["resources"]

            if self.currentStats is None:
                stats = [0,0,0,0,0,0] #Food, happiness, san x3, wealth
            else:
                r = self.currentStats["region"]
                stats = [
                    r["food"],
                    r["happiness"],
                    self.currentStats["settlement_sanitation"][0],
                    self.currentStats["settlement_sanitation"][1],
                    self.currentStats["settlement_sanitation"][2],
                    r["wealth"]
                ]
            return np.array(base+stats, dtype=np.float32)
        
    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        idx = self.np_random.integers(len(self.regionContexts))
        self.regionContext = self.regionContexts[idx]
        self.slots = [0]*NUM_SLOTS
        self.currentStats = None
        obs = self.getObs()
        return obs, {}

        
    def step(self, action):
        slotIdx = action // NUM_BUILDING_ID
        buildingId = action % NUM_BUILDING_ID
        self.slots[slotIdx] = buildingId
        reward, details = evaluate(self.buildRegion(), self.buildings, self.resources, self.stage)
        self.currentStats = details
        done = all(s != 0 for s in self.slots)
        obs = self.getObs()
        return obs, reward, done, False, {"raw_reward": (reward, details)}
    
    def buildRegion(self):
        context = parseContext(self.regionContext)
        
        return np.array(
            self.slots + #:5 city, 5:8 town, 8:11 town
            [context["fertility"]] + # int between 0 and 5
            context["coast"] + # array with len 3 indicating if settlements are on the coast
            context["hasResource"] +
            context["resources"], #array with len 3 populated with resource ids indicating if settlements have access to resources
            dtype=np.int32
        )
    
    def getActionMask(self):
        regArray = self.getObs()
        mask = np.ones((NUM_SLOTS, NUM_BUILDING_ID), dtype = bool)
        regArray = [int(x) for x in regArray[0:CONTEXT_END]]

        slots = regArray[0:CONTEXT_START]
        coast = regArray[12:15]
        hasResource = regArray[15:18]
        resources = regArray[18:CONTEXT_END]

        Y_TIER_RESOURCES = ["gold", "iron", "grapes", "marble"]

        self.buildingsByName = {b["name"]: b for b in self.buildings}
        self.buildingsById = {}
        for b in self.buildings:
            self.buildingsById.setdefault(b["id"], []).append(b)

        for sIdx, (start, end, sType) in enumerate(SLOT_GROUPS):
            #Grab all preexisting buildings from settlement
            placedBuildings = [
                getBuilding(self.buildings, self.resources, slots[i], resources[sIdx], coast[sIdx]).get("name")
                for i in range(start, end) if slots[i] != 0
            ]
            #Collect all buildings that are mutually exclusive with preexisting buildings
            excluded = set()
            excluded.update(placedBuildings)
            for name in placedBuildings:
                b = self.buildingsByName.get(name)
                if b:
                    excluded.update(b.get("mutually_exclusive", []))
            
            #Check if settlement has coastline or resources
            noCoast = not coast[sIdx]
            noResource = not hasResource[sIdx]

            for slot in range(start, end):
                #Mask occupied slot
                if slots[slot] != 0:
                    mask[slot, :] = False
                    continue

                mask[slot, 0] = False

                #Does the settlement have a boating license?
                if noCoast:
                    mask[slot, 15] = False
                    mask[slot, 16] = False
                
                #Does the settlement know what a resource is?
                if noResource:
                    mask[slot, 17] = False
                    mask[slot, 18] = False
                else:
                    resourceName = self.resources[resources[sIdx]]["resource"]
                    if resourceName not in Y_TIER_RESOURCES:
                        mask[slot, 18] = False

                for b in self.buildings:
                    bid = b["id"]
                    #Is this type of building allowed in?
                    if sType not in b["valid_in"]:
                        mask[slot, bid] = False
                        continue
                    #Is the building already there?
                    if b["name"] in excluded:
                        mask[slot, bid] = False
        return mask.flatten()
if __name__ == "__main__":
    buildingList = buildLoader()
    resourceList = rsrcLoader()
    regionContexts = regionLoader()
    testEnv = LanguidusEnv(buildingList, resourceList, [[3, 1, 0, 0, 1, 0, 0, 3, 0, 0]])
    testEnv.regionContext = [3, 1, 0, 0, 1, 0, 0, 1, 0, 0]
    testEnv.slots = [0] * NUM_SLOTS
    testEnv.currentStats = None
    testEnv.getActionMask()