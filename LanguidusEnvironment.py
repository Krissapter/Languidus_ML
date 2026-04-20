import gymnasium as gym
import numpy as np
from LanguidusEvaluate.py import evaluate

class LanguidusEnv(gym.Env):
    def __init__(self, buildings, regionContext):
        super().__init__()
        self.buildings = buildings #list of buildings
        self.regionContext = regionContext #Fertility, coastline & resources
        self.slots = [0] * 11 #The funny input vector array

        self.observation_space = gym.spaces.MultiDiscrete([
            27, 27, 27, 27, 27, 27, 27, 27, 27, 27, 27, #11 building slots with 27 possible buildings
            6, #fertility
            2, 2, 2, #Coastal boolean for each settlement
            2, 2, 2, #hasResource boolean
            14, 14, 14, #resourceIDs for each settlement
        ])
        self.action_space = gym.spaces.MultiDiscrete([
            11, #building slots
            27, #building IDs
        ])

    def getObs(self):
            context = self.regionContext
            return np.array(
                self.slot + 
                [context["fertility"]] +
                context["coast"] +
                context["hasResource"] +
                context["resources"],
                dtype=np.int32
            )
        
    def reset(self, seed=None):
        super().reset(seed=seed)
        self.slots = [0]*11
        obs = self.getObs()
        return obs, {}

        
    def step(self, action):
        slotIdx, buildingId = action
        self.slots[slotIdx] = buildingId

        result = evaluate(self.buildRegion())

        done = all(s != 0 for s in self.slots)
        obs = self.getObs()
        return obs, result, done, False, {}
    
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
    def getActionMask(regArray):
         mask = np.ones((11, 27), dtype = bool)

         slots = regArray[0:11]
         coast = regArray[12:15]
         resources = regArray[18:21]