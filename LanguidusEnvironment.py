import gymnasium as gym
import numpy as np
from LanguidusEvaluation import evaluate, loadData, getBuilding

buildingList, resourceList = loadData()

class LanguidusEnv(gym.Env):
    def __init__(self, buildings, regionContext):
        super().__init__()
        self.buildings = buildings #list of buildings
        self.regionContext = regionContext #Fertility, coastline & resources
        self.slots = [0] * 11 #The funny input vector array
        self.currentStats = None

        self.observation_space = gym.spaces.Box(
            low=np.inf, high=np.inf, shape=(27,), dtype=np.float32
        )
        self.action_space = gym.spaces.Discrete(
            11* #building slots
            27 #building IDs
        )

    def getObs(self):
            context = self.regionContext
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
        self.slots = [0]*11
        obs = self.getObs()
        return obs, {}

        
    def step(self, action):
        slotIdx = action // 27
        buildingId = action % 27
        self.slots[slotIdx] = buildingId
        
        reward, details = evaluate(self.buildRegion(), buildingList, resourceList)
        self.currentStats = details
        done = all(s != 0 for s in self.slots)
        obs = self.getObs()
        return obs, reward, done, False, {"raw_reward": (reward, details)}
    
    def buildRegion(self):
        context = self.regionContext
        
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
        mask = np.ones((11, 27), dtype = bool)
        regArray = [int(x) for x in regArray[0:21]]

        slots = regArray[0:11]
        coast = regArray[12:15]
        resources = regArray[18:21]

        slotGroups = [(0, 5, "city"), (5, 8, "town"), (8, 11, "town")]

        for sIdx, (start, end, sType) in enumerate(slotGroups):
            #Grab all preexisting buildings from settlement
            placedBuildings = [
                getBuilding(buildingList,resourceList, slots[i], resources[sIdx], coast[sIdx]).get("name")
                for i in range(start, end) if slots[i] != 0
            ]
            #Collect all buildings that are mutually exclusive with preexisting buildings
            excluded = set()
            for building in placedBuildings:
                b = next((b for b in buildingList if b["name"] == building), None)
                if b:
                    excluded.update(b.get("mutually_exclusive", []))
            for slot in range(start, end):
                #Mask occupied slot
                if slots[slot] != 0:
                    mask[slot, :] = False
                    continue
                for b in buildingList:
                    bid = b["id"]
                    reqs = b.get("requires", [])
                    #Is this type of building allowed in?
                    if sType not in b["valid_in"]:
                        mask[slot, bid] = False
                        continue
                    #Does the settlement have a boating license?
                    if "coast" in reqs and not coast[sIdx]:
                        mask[slot, bid] = False
                        continue
                    #Does the settlement know what a resource is?
                    resourceReqs = [r for r in reqs if r != "coast"]
                    if resourceReqs and resources[sIdx] not in resourceReqs:
                        mask[slot, bid] = False
                    if b["name"] in excluded:
                        mask[slot, bid] = False
        return mask.flatten()
                        